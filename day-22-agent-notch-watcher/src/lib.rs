use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

pub mod tailer;
pub use tailer::{parse_jsonl_line, start_universal_tailer};


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
    pub fn hud_size(&self, expanded: bool) -> (f32, f32) {
        let shoulder = if expanded { 230.0 } else { 150.0 };
        let width = (self.notch_width + shoulder * 2.0).min(self.screen_width);
        let height = if expanded {
            self.notch_height + DRAWER_HEIGHT
        } else {
            self.notch_height
        };
        (width, height)
    }

    /// Usable width on each side of the cutout. Content laid out here is never occluded.
    pub fn shoulder_width(&self, hud_width: f32) -> f32 {
        ((hud_width - self.notch_width) / 2.0).max(0.0)
    }
}

/// Height of the expanded drawer that hangs below the notch.
/// 220, not 176: the LOCAL AGENTS section (top-3 detected processes) needs another
/// ~45pt below the session/budget rows, and 176 clipped it off the bottom of the window.
pub const DRAWER_HEIGHT: f32 = 220.0;

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
    pub name: String,
    pub cpu_usage: f32,
    pub memory_mb: f64,
    pub agent_type: AgentType,
}

pub fn match_agent_type_from_name(name: &str) -> AgentType {
    let lower = name.to_lowercase();
    if lower.contains("ollama") {
        AgentType::Ollama
    } else if lower.contains("claude") || lower.contains("anthropic") {
        AgentType::Anthropic
    } else if lower.contains("gemini") || lower.contains("antigravity") {
        AgentType::Gemini
    } else if lower.contains("openai") || lower.contains("gpt") || lower.contains("chatgpt") {
        AgentType::OpenAi
    } else {
        AgentType::Custom
    }
}

pub fn scan_system_agents(sys: &mut sysinfo::System) -> Vec<DetectedProcess> {
    sys.refresh_processes();
    let mut detected = Vec::new();
    let targets = ["ollama", "claude", "cursor", "antigravity", "python", "node"];

    for (pid, process) in sys.processes() {
        let name = process.name();
        let lower = name.to_lowercase();
        if targets.iter().any(|t| lower.contains(t)) {
            detected.push(DetectedProcess {
                pid: pid.as_u32(),
                name: name.to_string(),
                cpu_usage: process.cpu_usage(),
                memory_mb: (process.memory() as f64) / (1024.0 * 1024.0),
                agent_type: match_agent_type_from_name(name),
            });
        }
    }
    detected
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

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SessionLaunchPayload {
    pub agent_command: String,
    pub working_directory: String,
    pub initial_prompt: String,
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
    pub sessions: std::collections::HashMap<String, SessionState>,
    pub active_session_id: String,
}

impl Default for AppState {
    fn default() -> Self {
        let mut sessions = std::collections::HashMap::new();
        let default_id = "claude-default".to_string();
        sessions.insert(
            default_id.clone(),
            SessionState {
                session_id: default_id.clone(),
                agent_name: "Claude Code".to_string(),
                agent_type: AgentType::Anthropic,
                status: AgentStatus::Idle,
                step_description: "Idle - Awaiting task...".to_string(),
                tokens_used: 74200,
                token_limit: 100000,
            },
        );

        Self {
            agent_type: AgentType::Anthropic,
            status: AgentStatus::Idle,
            step_description: "Idle - Awaiting task...".to_string(),
            session_limit: SessionLimit::default(),
            glow_setting: GlowSetting::Max,
            detected_processes: Vec::new(),
            pending_permissions: Vec::new(),
            sessions,
            active_session_id: default_id,
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
        let session = SessionState {
            session_id: session_id.to_string(),
            agent_name: agent_name.to_string(),
            agent_type: agent_type.clone(),
            status: AgentStatus::Idle,
            step_description: format!("Session {} started", session_id),
            tokens_used: 0,
            token_limit: 100000,
        };
        self.sessions.insert(session_id.to_string(), session);
        if self.sessions.len() == 1 || self.active_session_id.is_empty() {
            self.active_session_id = session_id.to_string();
            self.agent_type = agent_type;
        }
    }

    pub fn select_session(&mut self, session_id: &str) {
        if let Some(session) = self.sessions.get(session_id) {
            self.active_session_id = session_id.to_string();
            self.agent_type = session.agent_type.clone();
            self.status = session.status.clone();
            self.step_description = session.step_description.clone();
            self.session_limit.tokens_used = session.tokens_used;
            self.session_limit.token_limit = session.token_limit;
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
        // sysinfo iterates a HashMap, so `first()` was whichever process hashed first —
        // usually a stray `node`. Sink unidentified processes so the badge and the
        // top-3 list both lock onto real agents.
        processes.sort_by_key(|p| (p.agent_type == AgentType::Custom, p.pid));

        if let Some(first) = processes.first() {
            if self.status == AgentStatus::Idle && first.agent_type != AgentType::Custom {
                self.agent_type = first.agent_type.clone();
            }
        }
        self.detected_processes = processes;
    }

    pub fn apply_event(&mut self, event: AgentEvent) {
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
