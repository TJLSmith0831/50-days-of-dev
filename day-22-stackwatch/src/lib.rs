use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

pub mod tailer;
pub mod term;
pub use tailer::{parse_jsonl_line, read_new_events, source_of, start_universal_tailer};
pub use term::{new_terminals, TermSession, Terminals};


#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum AgentType {
    Anthropic,
    Gemini,
    OpenAi,
    Ollama,
    Custom,
}

impl Default for AgentType {
    fn default() -> Self {
        AgentType::Anthropic
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum AgentStatus {
    Idle,
    Thinking,
    ToolExecuting,
    QuotaWarning,
    /// The session never started — its process failed to spawn. Deliberately not
    /// folded into `QuotaWarning`: "running low on tokens" and "never launched"
    /// need to be distinguishable at a glance in the notch.
    Error,
}

impl Default for AgentStatus {
    fn default() -> Self {
        AgentStatus::Idle
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum GlowSetting {
    Max,
    Subtle,
    Off,
}

impl Default for GlowSetting {
    fn default() -> Self {
        GlowSetting::Max
    }
}

impl GlowSetting {
    /// Opacity of the outer aura bloom. `Off` draws a clean glass edge only.
    pub fn intensity(&self) -> f32 {
        match self {
            GlowSetting::Max => 1.0,
            GlowSetting::Subtle => 0.4,
            GlowSetting::Off => 0.0,
        }
    }

    /// Breathing multiplier applied to the accent stroke. Never reaches 0 —
    /// a HUD that blinks fully out reads as a crash, not a pulse.
    pub fn pulse_at(&self, elapsed_secs: f32) -> f32 {
        let amplitude = match self {
            GlowSetting::Max => 0.30,
            GlowSetting::Subtle => 0.12,
            GlowSetting::Off => return 1.0,
        };
        (elapsed_secs * 3.0).sin() * amplitude + (1.0 - amplitude)
    }
}

/// Physical display-notch geometry, in logical points.
///
/// ponytail: read from `NSScreen` at startup (see `notch.rs`); these constructors are the
/// calibration knob for Macs without a notch, or when AppKit reports something odd.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct NotchGeometry {
    pub screen_width: f32,
    pub notch_width: f32,
    pub notch_height: f32,
}

impl NotchGeometry {
    /// Notch-less Macs (and external displays): pretend the menu bar strip is the notch,
    /// so the HUD docks under it with the same layout instead of hiding behind it.
    pub fn fallback(screen_width: f32) -> Self {
        Self {
            screen_width,
            notch_width: 0.0,
            notch_height: 24.0,
        }
    }

    /// Top-left corner of a HUD of `hud_width`, docked flush at the top edge, centred.
    pub fn dock_position(&self, hud_width: f32) -> (f32, f32) {
        (((self.screen_width - hud_width) / 2.0).max(0.0), 0.0)
    }

    /// Outer window size. The window is sized to its content so the transparent
    /// margin never swallows clicks meant for the app underneath.
    pub fn hud_size(&self, mode: HudMode) -> (f32, f32) {
        let width = match mode {
            // Narrower than it wants to be, on purpose: the collapsed bar sits in the same
            // strip as the menu-bar extras, and every point of shoulder is a point of their
            // icons covered. 100 still clears "Running tool" on the right shoulder.
            HudMode::Collapsed => self.notch_width + 100.0 * 2.0,
            HudMode::Drawer => self.notch_width + 210.0 * 2.0,
            HudMode::Terminal => TERMINAL_WIDTH,
        };
        let height = match mode {
            HudMode::Collapsed => self.notch_height,
            HudMode::Drawer => self.notch_height + DRAWER_HEIGHT,
            HudMode::Terminal => self.notch_height + TERMINAL_HEIGHT,
        };
        (width.min(self.screen_width), height)
    }

    /// Usable width on each side of the cutout. Content laid out here is never occluded.
    pub fn shoulder_width(&self, hud_width: f32) -> f32 {
        ((hud_width - self.notch_width) / 2.0).max(0.0)
    }
}

/// How much window the HUD is currently asking for. Three states, not a bool: a live
/// agent TUI needs an order of magnitude more room than a status drawer, and squeezing one
/// into the other is what made the drawer unreadable.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HudMode {
    /// Docked in the notch strip, status only.
    Collapsed,
    /// Status drawer: sessions, context gauge, local agents, activity.
    Drawer,
    /// A session's terminal, full width.
    Terminal,
}

/// Terminal-mode panel. 900x620 is ~100 columns by ~30 rows of 11pt monospace once the
/// tab strip and status line are taken out — the point below which Claude Code's TUI
/// starts wrapping its own borders.
pub const TERMINAL_WIDTH: f32 = 900.0;
pub const TERMINAL_HEIGHT: f32 = 620.0;

/// Height of the expanded drawer that hangs below the notch.
/// 220, not 176: the LOCAL AGENTS section (top-3 detected processes) needs another
/// ~45pt below the session/budget rows, and 176 clipped it off the bottom of the window.
/// 242, not 220: the launch form grew a second row (the initial-prompt field) — without
/// the extra ~22pt, LOCAL AGENTS clips off the bottom whenever the launcher is open at
/// the same time as a detected local process.
/// 350, not 242: LOCAL AGENTS rows grew a Kill button (13pt -> 20pt tall, needs button
/// hit-height) and an ACTIVITY pane was added below it (a bounded, scrollable session
/// list — the fixed `max_height` is what keeps it from repeating the old unbounded-height
/// bug in BUGS.md). Extra headroom is cheap; clipping the bottom section is not.
pub const DRAWER_HEIGHT: f32 = 350.0;

/// `74200` -> `"74,200"`. Raw token counts read as noise at 11pt.
pub fn thousands(n: u64) -> String {
    let digits = n.to_string();
    let mut out = String::with_capacity(digits.len() + digits.len() / 3);
    for (i, c) in digits.chars().enumerate() {
        if i > 0 && (digits.len() - i) % 3 == 0 {
            out.push(',');
        }
        out.push(c);
    }
    out
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionLimit {
    pub tokens_used: u64,
    pub token_limit: u64,
    pub requests_used: u32,
    pub request_limit: u32,
    pub budget_used: f64,
    pub reset_seconds_remaining: u64,
}

impl Default for SessionLimit {
    fn default() -> Self {
        Self {
            tokens_used: 74200,
            token_limit: 100000,
            requests_used: 42,
            request_limit: 50,
            budget_used: 0.14,
            reset_seconds_remaining: 8040, // 2h 14m
        }
    }
}

impl SessionLimit {
    pub fn usage_percentage(&self) -> f64 {
        if self.token_limit == 0 {
            return 0.0;
        }
        ((self.tokens_used as f64) / (self.token_limit as f64)) * 100.0
    }

    pub fn is_warning_threshold(&self) -> bool {
        self.usage_percentage() >= 90.0
    }

    pub fn formatted_time_remaining(&self) -> String {
        let hours = self.reset_seconds_remaining / 3600;
        let mins = (self.reset_seconds_remaining % 3600) / 60;
        format!("{}h {}m", hours, mins)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DetectedProcess {
    pub pid: u32,
    /// Who spawned it. This is what separates "a second agent" from "the first agent's
    /// forked worker" — see `top_level_agents`.
    pub parent_pid: Option<u32>,
    pub name: String,
    pub cpu_usage: f32,
    pub memory_mb: f64,
    pub agent_type: AgentType,
}

/// Context window a session's token gauge is measured against. Claude Code's is 200k;
/// anything unknown gets a neutral 100k rather than a made-up number.
pub fn context_window_of(agent: &AgentType) -> u64 {
    match agent {
        AgentType::Anthropic => 200_000,
        _ => 100_000,
    }
}

/// The herd. One list, two jobs: which binaries the launcher offers (filtered by
/// `available_agent_clis` to what's actually installed), and which running processes count
/// as an agent in `LOCAL AGENTS`. Coverage tracks herdr's supported set.
pub const KNOWN_AGENT_CLIS: &[&str] = &[
    "claude", "codex", "cursor-agent", "devin", "gemini", "ollama", "aider", "amp",
    "opencode", "goose", "copilot", "crush", "qoder",
];

/// Directories to look for agent binaries in.
///
/// `PATH` alone is not enough: launched from Finder (or any `.app` bundle) the process
/// inherits the bare system PATH, not the user's shell PATH — so `claude` installed under
/// nvm is invisible, and `Command::new("claude")` fails to spawn even though it's there.
pub(crate) fn binary_search_dirs() -> Vec<std::path::PathBuf> {
    use std::path::PathBuf;
    let mut dirs: Vec<PathBuf> = std::env::var("PATH")
        .unwrap_or_default()
        .split(':')
        .filter(|s| !s.is_empty())
        .map(PathBuf::from)
        .collect();
    dirs.extend(
        ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
            .iter()
            .map(PathBuf::from),
    );
    let home = std::env::var("HOME").unwrap_or_default();
    if !home.is_empty() {
        for rel in [".local/bin", ".bun/bin", ".cargo/bin", ".volta/bin"] {
            dirs.push(PathBuf::from(&home).join(rel));
        }
        // nvm nests every install under its own version directory.
        if let Ok(entries) = std::fs::read_dir(format!("{home}/.nvm/versions/node")) {
            for entry in entries.flatten() {
                dirs.push(entry.path().join("bin"));
            }
        }
    }
    dirs
}

fn is_executable_file(path: &std::path::Path) -> bool {
    use std::os::unix::fs::PermissionsExt;
    std::fs::metadata(path)
        .map(|m| m.is_file() && m.permissions().mode() & 0o111 != 0)
        .unwrap_or(false)
}

/// Turn a bare command name into an absolute path, using the same directories the
/// launcher probes. Anything already absolute (or not found) passes through unchanged.
///
/// Without this, a HUD started from Finder can't spawn `claude` at all — the `.app`
/// inherits the bare system PATH, not the shell's.
pub fn resolve_agent_command(cmd: &str) -> String {
    if cmd.contains('/') {
        return cmd.to_string();
    }
    binary_search_dirs()
        .iter()
        .map(|d| d.join(cmd))
        .find(|p| is_executable_file(p))
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|| cmd.to_string())
}

/// Absolute paths of the known agent CLIs actually installed on this machine.
///
/// Returned as full paths, not bare names, so launching works from a `.app` bundle too.
/// Probed once at startup — offering "gemini" on a machine without it is just a launch
/// failure the user could have been spared.
pub fn available_agent_clis() -> Vec<std::path::PathBuf> {
    let dirs = binary_search_dirs();
    let mut found = Vec::new();
    for name in KNOWN_AGENT_CLIS {
        if let Some(path) = dirs.iter().map(|d| d.join(name)).find(|p| is_executable_file(p)) {
            found.push(path);
        }
    }
    found
}

pub fn match_agent_type_from_name(name: &str) -> AgentType {
    let lower = name.to_lowercase();
    if lower.contains("ollama") {
        AgentType::Ollama
    } else if lower.contains("claude") || lower.contains("anthropic") {
        AgentType::Anthropic
    } else if lower.contains("gemini") || lower.contains("antigravity") {
        AgentType::Gemini
    } else if lower.contains("openai") || lower.contains("gpt") || lower.contains("codex") {
        AgentType::OpenAi
    } else {
        AgentType::Custom
    }
}

/// Is this process name one of the agent CLIs we herd?
///
/// Exact match on the binary name, case-insensitive — **not** substring. The old scan
/// matched `python` and `node` as substrings, which is how a Python helper and
/// `CursorUIViewService` ended up in `LOCAL AGENTS` with a Kill button beside them.
/// Substring matching can't be made safe here: every agent CLI worth naming is a common
/// English word or a common runtime.
pub fn is_agent_cli(process_name: &str) -> bool {
    let lower = process_name.to_lowercase();
    KNOWN_AGENT_CLIS.contains(&lower.as_str())
}

/// Drop agent processes that are children of another agent process, keeping one row per
/// actual session.
///
/// `claude` forks workers that are themselves called `claude`. The old fix deduped by
/// name, which also collapsed two genuinely separate sessions into one row — a herd
/// manager that under-reports the herd. Parenthood is the real signal: a child of a
/// detected agent belongs to it, while two agents both parented by the shell are two
/// agents. Membership is tested against the *input* set, so a worker still drops when its
/// own parent was dropped too.
pub fn top_level_agents(procs: Vec<DetectedProcess>) -> Vec<DetectedProcess> {
    let pids: std::collections::HashSet<u32> = procs.iter().map(|p| p.pid).collect();
    let mut kept: Vec<DetectedProcess> = procs
        .into_iter()
        .filter(|p| !p.parent_pid.is_some_and(|ppid| pids.contains(&ppid)))
        .collect();
    kept.sort_by_key(|p| p.pid);
    // Siblings: same binary, same parent. Parenthood alone misses these, because the
    // shared parent is often a GUI app that isn't itself an agent — Devin's app spawns two
    // `devin` helpers that way, and both showed up as separate agents. Keeping the
    // lowest-pid one is safe because two sessions started in two terminal tabs have
    // *different* parents and so are never collapsed together.
    //
    // pid 1 is exempt: launchd parents every GUI app and adopts every orphan, so a shared
    // parent of 1 says nothing about whether two agents are related.
    let mut seen = std::collections::HashSet::new();
    kept.retain(|p| match p.parent_pid {
        Some(ppid) if ppid != 1 => seen.insert((p.name.clone(), ppid)),
        _ => true,
    });
    kept
}

pub fn scan_system_agents(sys: &mut sysinfo::System) -> Vec<DetectedProcess> {
    sys.refresh_processes();
    let detected = sys
        .processes()
        .iter()
        .filter(|(_, process)| is_agent_cli(process.name()))
        .map(|(pid, process)| DetectedProcess {
            pid: pid.as_u32(),
            parent_pid: process.parent().map(|p| p.as_u32()),
            name: process.name().to_string(),
            cpu_usage: process.cpu_usage(),
            memory_mb: (process.memory() as f64) / (1024.0 * 1024.0),
            agent_type: match_agent_type_from_name(process.name()),
        })
        .collect();
    top_level_agents(detected)
}

/// Sends `SIGTERM` to a detected local agent process, so the `LOCAL AGENTS` list is
/// something you can act on, not just watch. Shells out (same pattern as
/// `notify_permission_request`'s `osascript` call) rather than reaching for a `sysinfo`
/// handle — the `System` that produced `DetectedProcess` lives on the background scan
/// thread, not the egui thread the Kill button runs on, so there's no live handle to reuse.
/// A stale PID (the process already exited since the last scan) or a permissions error
/// both come back as `Err` rather than panicking a render frame.
pub fn kill_local_process(pid: u32) -> Result<(), String> {
    let status = std::process::Command::new("kill")
        .arg(pid.to_string())
        .status()
        .map_err(|e| e.to_string())?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("kill exited with {status}"))
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PermissionRequest {
    pub request_id: String,
    pub session_id: String,
    pub agent_name: String,
    pub action_type: String,
    pub details: String,
    pub timeout_seconds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PermissionResponse {
    pub request_id: String,
    pub allowed: bool,
    pub timestamp: u64,
}

/// ponytail: no `initial_prompt` field. The session gets a real terminal in the drawer,
/// so the first message is just the first thing you type into it — a separate one-shot
/// prompt box was a second, worse way to say the same thing. Unknown fields are ignored
/// by serde, so an older caller still posting `initial_prompt` launches fine.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SessionLaunchPayload {
    pub agent_command: String,
    pub working_directory: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SessionState {
    pub session_id: String,
    pub agent_name: String,
    pub agent_type: AgentType,
    pub status: AgentStatus,
    pub step_description: String,
    pub tokens_used: u64,
    pub token_limit: u64,
    /// Ordering marker only — which session updated most recently, for the collapsed
    /// header's focus. Deliberately a counter, not wall-clock: nothing here needs a date.
    pub last_updated: u64,
}

/// A session whose process failed to spawn, queued for the drawer's failure prompt.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FailedLaunch {
    pub session_id: String,
    pub agent_name: String,
    pub reason: String,
}

static UPDATE_TICK: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(1);

fn next_tick() -> u64 {
    UPDATE_TICK.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
}

/// What the HUD paints for one slot (collapsed header, or the drawer's detail rows).
/// `None` from `header_view`/`drawer_view` is the genuine "nothing is running" state.
#[derive(Debug, Clone, PartialEq)]
pub struct HudView {
    pub agent_type: AgentType,
    pub status: AgentStatus,
    pub step_description: String,
    pub tokens_used: u64,
    pub token_limit: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentEvent {
    pub agent_type: Option<AgentType>,
    pub status: AgentStatus,
    pub step_description: String,
    pub tokens_used: Option<u64>,
    pub glow_setting: Option<GlowSetting>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppState {
    pub agent_type: AgentType,
    pub status: AgentStatus,
    pub step_description: String,
    pub session_limit: SessionLimit,
    pub glow_setting: GlowSetting,
    pub detected_processes: Vec<DetectedProcess>,
    pub pending_permissions: Vec<PermissionRequest>,
    pub pending_launch_failures: Vec<FailedLaunch>,
    pub sessions: std::collections::HashMap<String, SessionState>,
    pub active_session_id: Option<String>,
    /// Has any agent reported activity via `POST /event`? Agents on the event protocol
    /// have no session concept, so this is the only signal the HUD is showing something
    /// real rather than defaults — it gates the empty header alongside `sessions`.
    pub activity_seen: bool,
}

impl Default for AppState {
    fn default() -> Self {
        // No seeded demo session: an empty HUD on cold start is the honest state.
        Self {
            agent_type: AgentType::Anthropic,
            status: AgentStatus::Idle,
            step_description: "Idle - Awaiting task...".to_string(),
            session_limit: SessionLimit::default(),
            glow_setting: GlowSetting::Max,
            detected_processes: Vec::new(),
            pending_permissions: Vec::new(),
            pending_launch_failures: Vec::new(),
            sessions: std::collections::HashMap::new(),
            active_session_id: None,
            activity_seen: false,
        }
    }
}

impl AppState {
    pub fn add_permission_request(&mut self, request: PermissionRequest) {
        notify_permission_request(&request.agent_name, &request.details);
        self.pending_permissions.push(request);
    }

    pub fn resolve_permission(&mut self, request_id: &str, _allowed: bool) -> bool {
        if let Some(pos) = self.pending_permissions.iter().position(|p| p.request_id == request_id) {
            self.pending_permissions.remove(pos);
            true
        } else {
            false
        }
    }

    pub fn register_session(&mut self, session_id: &str, agent_type: AgentType, agent_name: &str) {
        let token_limit = context_window_of(&agent_type);
        let session = SessionState {
            session_id: session_id.to_string(),
            agent_name: agent_name.to_string(),
            agent_type,
            status: AgentStatus::Idle,
            step_description: format!("Session {} started", session_id),
            tokens_used: 0,
            token_limit,
            last_updated: next_tick(),
        };
        self.sessions.insert(session_id.to_string(), session);
        if self.active_session_id.is_none() {
            self.active_session_id = Some(session_id.to_string());
        }
    }

    /// Route one event to its own session, creating the session on first sight.
    /// This is what keeps two concurrently-running agents from clobbering each other:
    /// the tailer calls this per log file instead of `apply_event` on shared fields.
    pub fn apply_session_event(
        &mut self,
        session_id: &str,
        agent_type: AgentType,
        agent_name: &str,
        event: AgentEvent,
    ) {
        if !self.sessions.contains_key(session_id) {
            self.register_session(session_id, agent_type, agent_name);
        }
        let Some(session) = self.sessions.get_mut(session_id) else { return };
        session.status = event.status;
        session.step_description = event.step_description;
        if let Some(tokens) = event.tokens_used {
            session.tokens_used = tokens;
            // The window isn't knowable from the transcript — a session on the 1M tier
            // blows past the 200k default. Grow to the next real tier rather than pin a
            // wrong gauge at 100% forever.
            if tokens > session.token_limit {
                session.token_limit = 1_000_000;
            }
        }
        session.last_updated = next_tick();
    }

    pub fn select_session(&mut self, session_id: &str) {
        if self.sessions.contains_key(session_id) {
            self.active_session_id = Some(session_id.to_string());
        }
    }

    pub fn mark_session_failed(&mut self, session_id: &str, reason: &str) {
        let Some(session) = self.sessions.get_mut(session_id) else { return };
        session.status = AgentStatus::Error;
        session.step_description = format!("Failed to launch: {reason}");
        session.last_updated = next_tick();
        let agent_name = session.agent_name.clone();
        self.pending_launch_failures.push(FailedLaunch {
            session_id: session_id.to_string(),
            agent_name,
            reason: reason.to_string(),
        });
    }

    /// Drop the prompt but keep the (still-failed) tab — the "Later" action.
    pub fn dismiss_launch_failure(&mut self, session_id: &str) {
        self.pending_launch_failures.retain(|f| f.session_id != session_id);
    }

    pub fn remove_session(&mut self, session_id: &str) {
        self.sessions.remove(session_id);
        self.dismiss_launch_failure(session_id);
        if self.active_session_id.as_deref() == Some(session_id) {
            self.active_session_id = self.sessions.keys().next().cloned();
        }
    }

    fn view_of(&self, session: Option<&SessionState>) -> Option<HudView> {
        match session {
            Some(s) => Some(HudView {
                agent_type: s.agent_type.clone(),
                status: s.status.clone(),
                step_description: s.step_description.clone(),
                tokens_used: s.tokens_used,
                token_limit: s.token_limit,
            }),
            // No session, but an `/event`-only agent is reporting — still real activity.
            None if self.activity_seen => Some(HudView {
                agent_type: self.agent_type.clone(),
                status: self.status.clone(),
                step_description: self.step_description.clone(),
                tokens_used: self.session_limit.tokens_used,
                token_limit: self.session_limit.token_limit,
            }),
            None => None,
        }
    }

    /// Collapsed header: follows whichever session moved most recently, regardless of
    /// which tab is selected. `None` means nothing is running — paint the empty state.
    pub fn header_view(&self) -> Option<HudView> {
        let latest = self.sessions.values().max_by_key(|s| s.last_updated);
        self.view_of(latest)
    }

    /// Expanded drawer: follows the clicked tab, independent of the header.
    pub fn drawer_view(&self) -> Option<HudView> {
        let active = self
            .active_session_id
            .as_ref()
            .and_then(|id| self.sessions.get(id));
        self.view_of(active)
    }
}

/// One implementation of "launch a session", shared by `POST /session/launch` and the
/// notch's Launch button. Returns `(session_id, Some(reason))` when the spawn failed.
///
/// The agent goes into a PTY, not a plain `Command`: that's what makes the session's
/// terminal in the drawer interactive instead of a read-only log tail.
///
/// Free function, not an `AppState` method: it must hold the mutex only long enough to
/// register, then release before spawning — the egui render loop locks the same mutex
/// every frame, so holding it across a spawn would stall the HUD.
pub async fn launch_session(
    shared_state: &SharedState,
    terminals: &Terminals,
    payload: &SessionLaunchPayload,
) -> (String, Option<String>) {
    let session_id = format!(
        "session-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis()
    );
    let resolved = resolve_agent_command(&payload.agent_command);
    let agent_type = match_agent_type_from_name(&resolved);
    // Tab label is the binary name — a full path would blow out the tab strip.
    let agent_name = std::path::Path::new(&resolved)
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| resolved.clone());

    {
        let mut app_state = shared_state.lock().unwrap();
        app_state.register_session(&session_id, agent_type, &agent_name);
    }

    match TermSession::spawn(&resolved, &payload.working_directory) {
        Ok(term) => {
            terminals
                .lock()
                .unwrap()
                .insert(session_id.clone(), term);
            {
                let mut app_state = shared_state.lock().unwrap();
                if let Some(session) = app_state.sessions.get_mut(&session_id) {
                    session.step_description = "Terminal ready".to_string();
                }
            }
            (session_id, None)
        }
        Err(reason) => {
            shared_state
                .lock()
                .unwrap()
                .mark_session_failed(&session_id, &reason);
            (session_id, Some(reason))
        }
    }
}

pub type PermissionChannels = Arc<Mutex<std::collections::HashMap<String, tokio::sync::oneshot::Sender<bool>>>>;

pub fn resolve_permission_channel(
    channels: &PermissionChannels,
    state: SharedState,
    request_id: &str,
    allowed: bool,
) -> bool {
    let mut state_guard = state.lock().unwrap();
    let removed = state_guard.resolve_permission(request_id, allowed);
    if let Ok(mut chans) = channels.lock() {
        if let Some(tx) = chans.remove(request_id) {
            let _ = tx.send(allowed);
        }
    }
    removed
}

pub fn notify_permission_request(agent_name: &str, details: &str) {

    if cfg!(test) {
        return;
    }
    let script = format!(
        "display notification \"{}\" with title \"Permission Request: {}\" sound name \"Glass\"",
        details.replace('"', "\\\""),
        agent_name.replace('"', "\\\"")
    );
    let _ = std::process::Command::new("osascript")
        .arg("-e")
        .arg(script)
        .spawn();
}



impl AppState {
    pub fn update_detected_processes(&mut self, mut processes: Vec<DetectedProcess>) {
        // sysinfo iterates a HashMap, so `first()` was whichever process hashed first and
        // the list reshuffled under the cursor every scan tick. Sort is stable and sinks
        // unbranded agents (devin, amp, goose) below branded ones, so the header badge
        // locks onto a logo it can actually paint.
        processes.sort_by_key(|p| (p.agent_type == AgentType::Custom, p.pid));
        // ponytail: no dedupe-by-name here — `top_level_agents` already dropped forked
        // workers by parenthood, and deduping again would merge two real sessions.

        if let Some(first) = processes.first() {
            if self.status == AgentStatus::Idle && first.agent_type != AgentType::Custom {
                self.agent_type = first.agent_type.clone();
            }
        }
        self.detected_processes = processes;
    }

    pub fn apply_event(&mut self, event: AgentEvent) {
        self.activity_seen = true;
        if let Some(agent) = event.agent_type {
            self.agent_type = agent;
        }
        self.status = event.status;
        self.step_description = event.step_description;

        if let Some(tokens) = event.tokens_used {
            self.session_limit.tokens_used = tokens;
        }
        if let Some(glow) = event.glow_setting {
            self.glow_setting = glow;
        }

        // Auto trigger quota warning if 90%+ used
        if self.session_limit.is_warning_threshold() && self.status != AgentStatus::Thinking {
            self.status = AgentStatus::QuotaWarning;
        }
    }

    pub fn to_json_payload(&self) -> String {
        serde_json::to_string(self).unwrap_or_else(|_| "{}".to_string())
    }
}

pub type SharedState = Arc<Mutex<AppState>>;

#[cfg(test)]
mod tests;
