mod notch;

use stackwatch::{
    available_agent_clis, kill_local_process, launch_session, new_terminals, resolve_permission_channel,
    scan_system_agents, start_universal_tailer, term, thousands, AgentEvent, AgentStatus, AgentType,
    AppState, HudMode, NotchGeometry, DRAWER_HEIGHT, PermissionChannels, PermissionRequest, PermissionResponse,
    SessionLaunchPayload, SharedState, Terminals,
};

use axum::{
    extract::State,
    http::{HeaderValue, StatusCode},
    response::{Html, IntoResponse, Json},
    routing::{get, post},
    Router,
};
use eframe::egui::{
    self, pos2, vec2, Align2, Color32, FontId, Rounding, Sense, Stroke,
};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use sysinfo::System;
use tower_http::cors::CorsLayer;

const CARD: Color32 = Color32::from_rgb(9, 11, 16);
const TEXT: Color32 = Color32::from_rgb(237, 241, 248);
const DIM: Color32 = Color32::from_rgb(129, 140, 156);
const TRACK: Color32 = Color32::from_rgb(38, 43, 54);
const WARN: Color32 = Color32::from_rgb(244, 96, 84);
// Darker than WARN's coral on purpose: "quota low, still working" and "never started"
// must not read the same at a glance.
const ERROR: Color32 = Color32::from_rgb(200, 40, 40);

const PAD: f32 = 18.0;
const BOTTOM_RADIUS: f32 = 14.0;

// ---------------------------------------------------------------- HTTP

/// A mode change asked for over HTTP, waiting for the next render frame to apply it.
///
/// Its own slot rather than a field on `AppState`, which is serialised wholesale by
/// `GET /state` — "which pane is open" is UI state, not something a polling client should
/// be reading back as if it were agent status.
type UiRequest = Arc<Mutex<Option<(HudMode, Option<String>)>>>;

#[derive(Clone)]
struct ServerRouterState {
    shared_state: SharedState,
    channels: PermissionChannels,
    terminals: Terminals,
    ui_request: UiRequest,
}

/// `POST /ui` — open a pane from outside the app.
///
/// Exists because the HUD has no scriptable surface otherwise: it is an `LSUIElement` app
/// with no menu bar and no Dock tile, so there is nothing for AppleScript or the
/// accessibility APIs to drive. That makes it impossible to verify the terminal pane, or
/// to record a repeatable demo, without a human at the trackpad. It also falls out as a
/// real feature — an agent can bring its own session to the front.
async fn handle_post_ui(
    State(srv): State<ServerRouterState>,
    Json(body): Json<serde_json::Value>,
) -> impl IntoResponse {
    let mode = match body.get("mode").and_then(|m| m.as_str()) {
        Some("collapsed") => HudMode::Collapsed,
        Some("drawer") => HudMode::Drawer,
        Some("terminal") => HudMode::Terminal,
        other => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({
                    "error": format!("unknown mode {other:?}; want collapsed|drawer|terminal"),
                })),
            )
        }
    };
    let session_id = body
        .get("session_id")
        .and_then(|s| s.as_str())
        .map(str::to_string);
    *srv.ui_request.lock().unwrap() = Some((mode, session_id));
    (StatusCode::OK, Json(serde_json::json!({ "status": "ok" })))
}

/// `POST /session/input` — type into a session's terminal from outside the app.
///
/// The same bytes a keystroke would produce, straight into the PTY. Added so the demo
/// shoot could drive the one beat that proves the pane is interactive without a human at
/// the trackpad — the recording has to be re-runnable after a UI change, and a hand-typed
/// take isn't. It is the write half of what `POST /ui` does for panes.
async fn handle_session_input(
    State(srv): State<ServerRouterState>,
    Json(body): Json<serde_json::Value>,
) -> impl IntoResponse {
    let Some(session_id) = body.get("session_id").and_then(|s| s.as_str()) else {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({ "error": "session_id required" })),
        );
    };
    let text = body.get("text").and_then(|t| t.as_str()).unwrap_or_default();
    let mut terms = srv.terminals.lock().unwrap();
    let Some(term) = terms.get_mut(session_id) else {
        return (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "error": "no terminal for that session" })),
        );
    };
    term.send(text.as_bytes());
    (StatusCode::OK, Json(serde_json::json!({ "status": "sent" })))
}

async fn handle_get_index() -> Html<&'static str> {
    Html("<h1>Agent Notch Watcher Native Server</h1>")
}

async fn handle_get_state(State(srv): State<ServerRouterState>) -> impl IntoResponse {
    let app_state = srv.shared_state.lock().unwrap().clone();
    Json(app_state)
}

async fn handle_post_event(
    State(srv): State<ServerRouterState>,
    Json(event): Json<AgentEvent>,
) -> impl IntoResponse {
    let mut app_state = srv.shared_state.lock().unwrap();
    app_state.apply_event(event);
    (StatusCode::OK, Json(app_state.clone()))
}

async fn handle_permission_request(
    State(srv): State<ServerRouterState>,
    Json(req): Json<PermissionRequest>,
) -> impl IntoResponse {
    let (tx, rx) = tokio::sync::oneshot::channel();
    {
        // Lock state before channels — matches `resolve_permission_channel`'s order.
        // Taking them in opposite order on the two call paths is a lock-order
        // inversion: a click on Approve/Deny racing an incoming request could deadlock.
        let mut app_state = srv.shared_state.lock().unwrap();
        let mut chans = srv.channels.lock().unwrap();
        chans.insert(req.request_id.clone(), tx);
        app_state.add_permission_request(req.clone());
    }

    let timeout_sec = if req.timeout_seconds == 0 { 60 } else { req.timeout_seconds };
    let allowed = match tokio::time::timeout(Duration::from_secs(timeout_sec), rx).await {
        Ok(Ok(val)) => val,
        _ => false,
    };

    let response = PermissionResponse {
        request_id: req.request_id,
        allowed,
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs(),
    };
    (StatusCode::OK, Json(response))
}

async fn handle_session_launch(
    State(srv): State<ServerRouterState>,
    Json(payload): Json<SessionLaunchPayload>,
) -> impl IntoResponse {
    let (session_id, failure) =
        launch_session(&srv.shared_state, &srv.terminals, &payload).await;

    // 200 on failure with the outcome in the body, matching every other handler here —
    // both callers (the Spawn button, simulate.rs) read the body, not the status code.
    (
        StatusCode::OK,
        Json(serde_json::json!({
            "status": if failure.is_some() { "failed" } else { "launched" },
            "session_id": session_id,
            "agent_command": payload.agent_command,
            "reason": failure,
        })),
    )
}

fn start_http_server(
    shared_state: SharedState,
    channels: PermissionChannels,
    terminals: Terminals,
    ui_request: UiRequest,
) {
    let server_router_state = ServerRouterState {
        shared_state,
        channels,
        terminals,
        ui_request,
    };

    tokio::spawn(async move {
        let app = Router::new()
            .route("/", get(handle_get_index))
            .route("/state", get(handle_get_state))
            .route("/event", post(handle_post_event))
            .route("/permission/request", post(handle_permission_request))
            .route("/session/launch", post(handle_session_launch))
            .route("/ui", post(handle_post_ui))
            .route("/session/input", post(handle_session_input))
            .layer(
                CorsLayer::new()
                    .allow_origin(HeaderValue::from_static("*"))
                    .allow_headers(tower_http::cors::Any)
                    .allow_methods(tower_http::cors::Any),
            )
            .with_state(server_router_state);

        let listener = tokio::net::TcpListener::bind("127.0.0.1:8765")
            .await
            .expect("Failed to bind port 8765");

        println!("Agent Notch Watcher HTTP Server running at http://127.0.0.1:8765");
        axum::serve(listener, app).await.unwrap();
    });
}


// ---------------------------------------------------------------- palette

fn accent_of(agent: &AgentType) -> Color32 {
    match agent {
        AgentType::Anthropic => Color32::from_rgb(217, 119, 87),
        AgentType::Gemini => Color32::from_rgb(101, 141, 245),
        AgentType::OpenAi => Color32::from_rgb(25, 195, 155),
        AgentType::Ollama => Color32::from_rgb(226, 232, 240),
        AgentType::Custom => Color32::from_rgb(167, 139, 250),
    }
}

/// Brand mark for the collapsed header. Sourced from svgl.app (`assets/logos/`), dark
/// variants — the HUD card is near-black, and the light variants render as a black hole.
/// `Custom` has no mark by definition, so it falls back to the text label.
fn logo_of(agent: &AgentType) -> Option<egui::ImageSource<'static>> {
    Some(match agent {
        AgentType::Anthropic => egui::include_image!("../assets/logos/anthropic.svg"),
        AgentType::Gemini => egui::include_image!("../assets/logos/gemini.svg"),
        AgentType::OpenAi => egui::include_image!("../assets/logos/openai.svg"),
        AgentType::Ollama => egui::include_image!("../assets/logos/ollama.svg"),
        AgentType::Custom => return None,
    })
}

fn label_of(agent: &AgentType) -> &'static str {
    match agent {
        AgentType::Anthropic => "Claude",
        AgentType::Gemini => "Gemini",
        AgentType::OpenAi => "OpenAI",
        AgentType::Ollama => "Ollama",
        AgentType::Custom => "Agent",
    }
}

fn status_color(status: &AgentStatus) -> Color32 {
    match status {
        AgentStatus::Idle => Color32::from_rgb(52, 199, 123),
        AgentStatus::Thinking => Color32::from_rgb(245, 178, 61),
        AgentStatus::ToolExecuting => Color32::from_rgb(90, 160, 255),
        AgentStatus::QuotaWarning => WARN,
        AgentStatus::Error => ERROR,
    }
}

fn status_label(status: &AgentStatus) -> &'static str {
    match status {
        AgentStatus::Idle => "Ready",
        AgentStatus::Thinking => "Thinking",
        AgentStatus::ToolExecuting => "Running tool",
        AgentStatus::QuotaWarning => "Quota low",
        AgentStatus::Error => "Launch failed",
    }
}

/// Prompt cards render only the head of their queue. Without this line, anything behind
/// it is invisible. Returns the vertical space consumed.
fn queued_more(p: &egui::Painter, at: egui::Pos2, queue_len: usize) -> f32 {
    if queue_len <= 1 {
        return 0.0;
    }
    p.text(
        at,
        Align2::LEFT_TOP,
        format!("+{} more waiting", queue_len - 1),
        FontId::proportional(9.0),
        DIM,
    );
    12.0
}

fn usage_fraction(used: u64, limit: u64) -> f32 {
    if limit == 0 {
        return 0.0;
    }
    ((used as f64) / (limit as f64)).clamp(0.0, 1.0) as f32
}

fn with_alpha(color: Color32, alpha: f32) -> Color32 {
    Color32::from_rgba_unmultiplied(
        color.r(),
        color.g(),
        color.b(),
        (alpha.clamp(0.0, 1.0) * 255.0) as u8,
    )
}

/// Slack between the last painted row and the bottom of the drawer.
///
/// Not cosmetic — it decouples the two feedback loops. The window is sized from what the
/// last frame painted, and what a frame paints depends on the room it has (`room_for`
/// skips a section that won't fit). Sizing to the measurement exactly leaves the last
/// section landing right on the boundary, so it paints, shrinks the window, doesn't fit,
/// disappears, grows the window, paints again — a flicker at 30fps. The slack means a
/// section that fit once still fits after the shrink.
const DRAWER_SLACK: f32 = 16.0;

// ---------------------------------------------------------------- terminal

/// Monospace size for the session terminal. 11.5 is the smallest that stays legible on a
/// Retina panel while still fitting the ~100 columns an agent TUI wants.
const TERM_FONT: f32 = 11.5;

/// One entry of the xterm 256-colour palette.
///
/// ponytail: the 216-colour cube and the 24 greys are generated rather than typed out —
/// only the low 16 are arbitrary enough to need a table.
fn ansi_color(idx: u8) -> Color32 {
    const BASE: [(u8, u8, u8); 16] = [
        (0, 0, 0),
        (205, 49, 49),
        (13, 188, 121),
        (229, 229, 16),
        (36, 114, 200),
        (188, 63, 188),
        (17, 168, 205),
        (229, 229, 229),
        (102, 102, 102),
        (241, 76, 76),
        (35, 209, 139),
        (245, 245, 67),
        (59, 142, 234),
        (214, 112, 214),
        (41, 184, 219),
        (255, 255, 255),
    ];
    match idx {
        0..=15 => {
            let (r, g, b) = BASE[idx as usize];
            Color32::from_rgb(r, g, b)
        }
        16..=231 => {
            let i = idx - 16;
            let step = |v: u8| if v == 0 { 0 } else { 55 + v * 40 };
            Color32::from_rgb(step(i / 36), step((i % 36) / 6), step(i % 6))
        }
        _ => {
            let v = 8 + (idx - 232) * 10;
            Color32::from_rgb(v, v, v)
        }
    }
}

fn vt_color(color: vt100::Color, fallback: Color32) -> Color32 {
    match color {
        vt100::Color::Default => fallback,
        vt100::Color::Idx(i) => ansi_color(i),
        vt100::Color::Rgb(r, g, b) => Color32::from_rgb(r, g, b),
    }
}

/// Escape sequence a special key sends. Returns `None` for anything egui already reports
/// as `Event::Text` — handling both would type every character twice.
fn key_bytes(key: egui::Key, mods: &egui::Modifiers) -> Option<Vec<u8>> {
    use egui::Key;
    // Ctrl+letter is the control character, and it's how you interrupt an agent (^C) or
    // send EOF (^D). egui reports the letter as Text too, so this must come first.
    if mods.ctrl && !mods.command {
        let name = key.name();
        if let Some(c) = name.chars().next().filter(|_| name.len() == 1) {
            let upper = c.to_ascii_uppercase();
            if upper.is_ascii_alphabetic() {
                return Some(vec![upper as u8 - b'A' + 1]);
            }
        }
    }
    let seq: &[u8] = match key {
        Key::Enter => b"\r",
        // DEL, not BS: readline and every TUI on macOS expect 0x7f for the Delete key.
        Key::Backspace => b"\x7f",
        Key::Tab => b"\t",
        Key::Escape => b"\x1b",
        Key::ArrowUp => b"\x1b[A",
        Key::ArrowDown => b"\x1b[B",
        Key::ArrowRight => b"\x1b[C",
        Key::ArrowLeft => b"\x1b[D",
        Key::Home => b"\x1b[H",
        Key::End => b"\x1b[F",
        Key::Delete => b"\x1b[3~",
        Key::PageUp => b"\x1b[5~",
        Key::PageDown => b"\x1b[6~",
        _ => return None,
    };
    Some(seq.to_vec())
}

/// A run of same-styled cells on one row, ready to append to a text layout.
#[derive(Debug, PartialEq)]
struct Segment {
    /// Column the run starts at, for placing its background rect.
    col: u16,
    /// Cells the run covers — not `text.len()`, which differs for wide glyphs.
    width: u16,
    text: String,
    fg: Color32,
    bg: Color32,
    bold: bool,
}

/// Collapse one screen row into styled runs.
///
/// Split out from the painting so it can be tested without a GPU: this is where the
/// fiddly parts live (wide-glyph continuation cells, inverse video, run boundaries), and
/// with no screen-recording permission there is no way to eyeball the result.
fn row_segments(screen: &vt100::Screen, row: u16) -> Vec<Segment> {
    let (_, cols) = screen.size();
    let mut out: Vec<Segment> = Vec::new();
    let mut col = 0;
    while col < cols {
        let cell = screen.cell(row, col);
        // A wide glyph occupies two cells; the second reports empty contents and would
        // otherwise be painted as an extra space, shearing the rest of the row.
        if cell.is_some_and(|c| c.is_wide_continuation()) {
            col += 1;
            continue;
        }
        let wide = cell.is_some_and(|c| c.is_wide());
        let width = if wide { 2 } else { 1 };
        // Inverse video is how a TUI paints its selected row and its own cursor. Ignoring
        // it makes the highlighted item indistinguishable from everything around it.
        let inverse = cell.is_some_and(|c| c.inverse());
        let (text, mut fg, raw_bg, bold) = match cell {
            Some(c) if c.has_contents() => (
                c.contents().to_string(),
                vt_color(c.fgcolor(), TEXT),
                c.bgcolor(),
                c.bold(),
            ),
            _ => (" ".to_string(), TEXT, vt100::Color::Default, false),
        };
        let bg = vt_color(raw_bg, if inverse { TEXT } else { Color32::TRANSPARENT });
        if inverse {
            fg = CARD;
        }
        match out.last_mut() {
            // Runs merge only when nothing about the styling changed. Background is part
            // of that: a merged run paints one rect, so two different backgrounds in one
            // run would silently drop the second.
            Some(last) if last.fg == fg && last.bg == bg && last.bold == bold => {
                last.text.push_str(&text);
                last.width += width;
            }
            _ => out.push(Segment {
                col,
                width,
                text,
                fg,
                bg,
                bold,
            }),
        }
        col += 1;
    }
    out
}

/// Paint a VT screen into `rect` and report the character grid that fits, so the caller
/// can resize the PTY to match.
///
/// One galley per row, not per cell: a 100x30 grid is 3000 cells, and 3000 individual
/// `painter.text` calls at 30fps is a slideshow. Cells are coalesced into runs of
/// identical styling, which for agent output is usually a handful of runs per line.
fn paint_terminal(ui: &egui::Ui, rect: egui::Rect, screen: &vt100::Screen) -> (u16, u16) {
    let p = ui.painter().with_clip_rect(rect);
    let font = FontId::monospace(TERM_FONT);
    let (char_w, row_h) = ui.fonts(|f| (f.glyph_width(&font, ' '), f.row_height(&font)));
    if char_w <= 0.0 || row_h <= 0.0 {
        return (term::TERM_ROWS, term::TERM_COLS);
    }

    let (screen_rows, screen_cols) = screen.size();
    for row in 0..screen_rows {
        let y = rect.top() + row as f32 * row_h;
        if y + row_h > rect.bottom() + row_h {
            break;
        }
        let mut job = egui::text::LayoutJob::default();
        for seg in row_segments(screen, row) {
            if seg.bg != Color32::TRANSPARENT {
                let x = rect.left() + seg.col as f32 * char_w;
                p.rect_filled(
                    egui::Rect::from_min_size(
                        pos2(x, y),
                        vec2(char_w * seg.width as f32, row_h),
                    ),
                    0.0,
                    seg.bg,
                );
            }
            append_run(&mut job, &seg.text, seg.fg, seg.bold);
        }
        p.galley(pos2(rect.left(), y), ui.fonts(|f| f.layout_job(job)), TEXT);
    }

    // Block cursor, so you can see where your typing is going.
    let (cur_row, cur_col) = screen.cursor_position();
    if !screen.hide_cursor() && cur_row < screen_rows {
        p.rect_filled(
            egui::Rect::from_min_size(
                pos2(
                    rect.left() + cur_col as f32 * char_w,
                    rect.top() + cur_row as f32 * row_h,
                ),
                vec2(char_w, row_h),
            ),
            1.0,
            with_alpha(TEXT, 0.65),
        );
    }

    let cols = (rect.width() / char_w).floor().clamp(20.0, 400.0) as u16;
    let rows = (rect.height() / row_h).floor().clamp(5.0, 200.0) as u16;
    (rows, cols)
}

fn append_run(job: &mut egui::text::LayoutJob, text: &str, color: Color32, bold: bool) {
    job.append(
        text,
        0.0,
        egui::TextFormat {
            font_id: FontId::monospace(TERM_FONT),
            color,
            // egui's default monospace has no bold face; brightening is the honest
            // approximation and keeps a TUI's emphasised text distinguishable.
            extra_letter_spacing: if bold { 0.1 } else { 0.0 },
            ..Default::default()
        },
    );
}

// ---------------------------------------------------------------- app

struct NotchWatcherApp {
    state: SharedState,
    channels: PermissionChannels,
    /// Live PTYs, keyed by session id. Kept out of `AppState` because that gets serialised
    /// wholesale by `GET /state`.
    terminals: Terminals,
    /// Handle to the app-wide tokio runtime. Button handlers run on the egui thread,
    /// which is *not* inside the runtime, so bare `tokio::spawn` panics there.
    rt: tokio::runtime::Handle,
    /// Where the async folder picker drops its result for the next frame to pick up.
    picked_dir: Arc<Mutex<Option<String>>>,
    /// True while the native folder sheet is up. The sheet takes focus off the HUD window,
    /// which would otherwise read as "user clicked away" and collapse the drawer out from
    /// under the picker that opened it.
    picker_busy: Arc<std::sync::atomic::AtomicBool>,
    geometry: NotchGeometry,
    mode: HudMode,
    docked_as: Option<HudMode>,
    /// Last size actually sent to the viewport. The drawer's height depends on content,
    /// so the mode alone no longer tells us whether a re-dock is needed.
    docked_size: (f32, f32),
    /// How tall the drawer's content measured last frame. `None` until it has been
    /// painted once, which is what `DRAWER_HEIGHT` is still the fallback for.
    measured_drawer_h: Option<f32>,
    /// Which session's terminal `HudMode::Terminal` is showing.
    terminal_session: Option<String>,
    /// Last grid the PTY was told about, so a resize only fires when it actually changed.
    term_grid: (u16, u16),
    /// Pane changes arriving over `POST /ui`, drained once per frame.
    ui_request: UiRequest,
    /// When the pane last changed. Opening a pane activates the app, and the focus flag
    /// takes a few frames to catch up — without a grace period the auto-collapse below
    /// reads that in-between state as "user clicked away" and slams the pane shut on the
    /// same frame it opened.
    mode_since: Instant,
    start_time: Instant,
    show_launch_input: bool,
    /// Absolute paths of agent CLIs found on this machine, probed once at startup.
    available_clis: Vec<std::path::PathBuf>,
    launch_cmd: String,
    launch_custom: bool,
    launch_dir: String,
}

/// Display name for a probed CLI path — the binary name, not the whole path.
fn cli_label(path: &std::path::Path) -> String {
    path.file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| path.to_string_lossy().to_string())
}

impl NotchWatcherApp {
    fn new(
        cc: &eframe::CreationContext<'_>,
        state: SharedState,
        channels: PermissionChannels,
        terminals: Terminals,
        ui_request: UiRequest,
        geometry: NotchGeometry,
        rt: tokio::runtime::Handle,
    ) -> Self {
        // Required for `egui::Image` / `include_image!` to resolve the bundled SVGs.
        egui_extras::install_image_loaders(&cc.egui_ctx);

        let available_clis = available_agent_clis();
        println!(
            "Agent CLIs found: {:?}",
            available_clis.iter().map(|p| cli_label(p)).collect::<Vec<_>>()
        );

        let mut visuals = egui::Visuals::dark();
        // Only the *panel* is transparent — that's what lets the HUD's own painted card
        // show through. `window_fill` is what popups (the Cmd dropdown, context menus)
        // paint with; leaving it transparent made the dropdown a ghost you could read
        // the drawer through.
        visuals.panel_fill = Color32::TRANSPARENT;
        visuals.window_fill = CARD;
        visuals.window_stroke = Stroke::new(1.0, TRACK);
        visuals.widgets.noninteractive.bg_fill = CARD;
        visuals.widgets.inactive.bg_fill = CARD;
        cc.egui_ctx.set_visuals(visuals);

        Self {
            state,
            channels,
            terminals,
            rt,
            picked_dir: Arc::new(Mutex::new(None)),
            picker_busy: Arc::new(std::sync::atomic::AtomicBool::new(false)),
            geometry,
            mode: HudMode::Collapsed,
            docked_as: None,
            docked_size: (0.0, 0.0),
            measured_drawer_h: None,
            terminal_session: None,
            term_grid: (term::TERM_ROWS, term::TERM_COLS),
            ui_request,
            mode_since: Instant::now(),
            start_time: Instant::now(),
            show_launch_input: false,
            launch_cmd: available_clis
                .first()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default(),
            launch_custom: available_clis.is_empty(),
            available_clis,
            // Launched from a .app the cwd is `/`, which is a useless default to spawn in.
            launch_dir: std::env::current_dir()
                .ok()
                .filter(|p| p != std::path::Path::new("/"))
                .or_else(|| std::env::var("HOME").ok().map(std::path::PathBuf::from))
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default(),
        }
    }

    /// Open `session_id`'s terminal, growing the window to the terminal panel.
    ///
    /// Activating the app is not optional: StackWatch is an `Accessory`, so clicking its
    /// window focuses the window without making the *app* active — and an inactive app
    /// receives no key events at all, which would make the terminal look frozen.
    fn open_terminal(&mut self, ctx: &egui::Context, session_id: &str) {
        if !self.terminals.lock().unwrap().contains_key(session_id) {
            return;
        }
        self.terminal_session = Some(session_id.to_string());
        self.mode = HudMode::Terminal;
        self.state.lock().unwrap().select_session(session_id);
        notch::activate_app();
        ctx.send_viewport_cmd(egui::ViewportCommand::Focus);
    }

    /// Drain this frame's keyboard input into the focused session's PTY.
    fn pump_terminal_input(&mut self, ctx: &egui::Context) {
        let Some(session_id) = self.terminal_session.clone() else {
            return;
        };
        let mut out: Vec<u8> = Vec::new();
        ctx.input(|i| {
            for event in &i.events {
                match event {
                    // Text and Key both fire for a printable character; `key_bytes`
                    // returns None for those so it isn't typed twice. Ctrl-combos are the
                    // exception and are handled on the Key side.
                    egui::Event::Text(t) if !i.modifiers.ctrl && !i.modifiers.command => {
                        out.extend_from_slice(t.as_bytes())
                    }
                    egui::Event::Key {
                        key,
                        pressed: true,
                        modifiers,
                        ..
                    } => {
                        if let Some(bytes) = key_bytes(*key, modifiers) {
                            out.extend_from_slice(&bytes);
                        }
                    }
                    egui::Event::Paste(text) => out.extend_from_slice(text.as_bytes()),
                    _ => {}
                }
            }
        });
        if out.is_empty() {
            return;
        }
        if let Some(term) = self.terminals.lock().unwrap().get_mut(&session_id) {
            term.send(&out);
        }
    }
}

impl eframe::App for NotchWatcherApp {
    fn clear_color(&self, _visuals: &egui::Visuals) -> [f32; 4] {
        [0.0, 0.0, 0.0, 0.0]
    }

    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        ctx.request_repaint_after(Duration::from_millis(33));

        let (mut want_w, mut want_h) = self.geometry.hud_size(self.mode);
        if self.mode == HudMode::Drawer {
            // Fit the drawer to its content rather than to a fixed 350pt sized for the
            // worst case, which left a third of the panel as dead black space whenever
            // fewer cards were showing.
            //
            // The height comes from what the painter actually advanced through last
            // frame, not from a table of section heights kept in step with it by hand.
            // That table is exactly what went wrong first: the estimate drifted from the
            // real advances, `room_for` decided ACTIVITY wouldn't fit, and the section
            // silently vanished. The painter is the only thing that knows how tall the
            // painter is. One frame of lag, invisible at 30fps.
            want_h = self.geometry.notch_height
                + self.measured_drawer_h.unwrap_or(DRAWER_HEIGHT);
        }
        want_w = want_w.min(self.geometry.screen_width);
        // Re-dock on any size change, not only a mode change — the drawer's height is now
        // a function of state, so `docked_as` alone would freeze it at whatever the
        // content happened to be when it opened.
        if self.docked_as != Some(self.mode) || (want_w, want_h) != self.docked_size {
            if self.docked_as != Some(self.mode) {
                self.mode_since = Instant::now();
            }
            let (x, y) = self.geometry.dock_position(want_w);
            ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(vec2(want_w, want_h)));
            ctx.send_viewport_cmd(egui::ViewportCommand::OuterPosition(pos2(x, y)));
            self.docked_as = Some(self.mode);
            self.docked_size = (want_w, want_h);
        }

        // Collect a folder the async picker resolved since the last frame.
        if let Some(dir) = self.picked_dir.lock().unwrap().take() {
            self.launch_dir = dir;
        }

        // Apply a pane change asked for over `POST /ui`. Bound to a local first: the guard
        // temporary would otherwise live for the whole block, and `open_terminal` needs
        // `&mut self` while that borrow is still outstanding.
        let requested = self.ui_request.lock().unwrap().take();
        if let Some((mode, session_id)) = requested {
            match (mode, session_id) {
                // Opening a terminal has preconditions (the session must actually have a
                // pty) and side effects (activating the app so it can take keys), so it
                // goes through the same path the ACTIVITY click uses rather than around it.
                (HudMode::Terminal, Some(id)) => self.open_terminal(ctx, &id),
                (HudMode::Terminal, None) => {
                    let first = self.terminals.lock().unwrap().keys().next().cloned();
                    if let Some(id) = first {
                        self.open_terminal(ctx, &id);
                    }
                }
                (mode, _) => {
                    self.mode = mode;
                    if mode != HudMode::Terminal {
                        notch::activate_app();
                    }
                }
            }
        }

        // An agent that has quit leaves a dead PTY behind. Reap it here rather than in the
        // paint pass, so the ACTIVITY row stops offering a terminal that can't take input.
        {
            let mut terms = self.terminals.lock().unwrap();
            // `filter_map`, not `filter().map()`: the latter hands the closure a *reference*
            // to the tuple, so the `&mut TermSession` that `is_alive` needs is one level of
            // borrow too deep.
            let dead: Vec<String> = terms
                .iter_mut()
                .filter_map(|(id, t)| (!t.is_alive()).then(|| id.clone()))
                .collect();
            for id in dead {
                terms.remove(&id);
                let mut state = self.state.lock().unwrap();
                if let Some(session) = state.sessions.get_mut(&id) {
                    session.status = AgentStatus::Idle;
                    session.step_description = "Exited".to_string();
                }
                if self.terminal_session.as_deref() == Some(id.as_str()) {
                    // Don't yank the window out from under the user mid-read — just drop
                    // back to the drawer, where the session is still listed as Exited.
                    self.terminal_session = None;
                    self.mode = HudMode::Drawer;
                }
            }
        }

        if self.mode == HudMode::Terminal {
            self.pump_terminal_input(ctx);
        }

        // Click anywhere outside the HUD and it goes back to being a notch. There is no
        // "outside click" event to listen for — the HUD is a window, so what actually
        // happens is it loses focus, and that covers switching apps and hitting the
        // desktop alike.
        //
        // The drawer only. A terminal is a conversation in progress: you alt-tab to a
        // browser to copy an error into it, and having the pane shut itself on the way
        // makes it unusable for the thing it's for. The drawer is glanceable status, so
        // getting out of the way is exactly what it should do. Close a terminal
        // deliberately — ◂ Sessions, the notch, or ✕ End session.
        //
        // The grace period is load-bearing, not a fudge: opening a pane activates the app,
        // and until AppKit finishes that handshake the viewport still reports unfocused.
        // Without the delay a pane collapsed on the very frame it opened, so the terminal
        // could never be reached at all.
        const COLLAPSE_GRACE: Duration = Duration::from_millis(600);
        let focused = ctx.input(|i| i.viewport().focused.unwrap_or(true));
        if !focused
            && self.mode == HudMode::Drawer
            // `docked_as` lags `mode` by exactly the frame a pane opens on, because the
            // docking block above runs before the pane is chosen. Without this the grace
            // period is measured against the *previous* pane change and a terminal opened
            // this frame is collapsed on this frame — which is why it never appeared.
            && self.docked_as == Some(self.mode)
            && self.mode_since.elapsed() > COLLAPSE_GRACE
            && !self.picker_busy.load(std::sync::atomic::Ordering::Relaxed)
        {
            self.mode = HudMode::Collapsed;
            self.show_launch_input = false;
        }

        let s = self.state.lock().unwrap().clone();
        let elapsed = self.start_time.elapsed().as_secs_f32();
        let pulse = s.glow_setting.pulse_at(elapsed);
        let has_pending_perm = !s.pending_permissions.is_empty();
        // header follows whatever moved most recently; drawer follows the clicked tab.
        let header = s.header_view();
        let drawer = s.drawer_view();
        let glow = if has_pending_perm {
            1.0
        } else {
            s.glow_setting.intensity() * pulse
        };
        let accent = match (&header, has_pending_perm) {
            (_, true) => WARN,
            (Some(h), false) => accent_of(&h.agent_type),
            (None, false) => DIM,
        };
        let notch_h = self.geometry.notch_height;

        egui::CentralPanel::default()
            .frame(egui::Frame::none())
            .show(ctx, |ui| {
                let card = ui.max_rect();
                let p = ui.painter().clone();

                let rounding = Rounding {
                    nw: 0.0,
                    ne: 0.0,
                    sw: BOTTOM_RADIUS,
                    se: BOTTOM_RADIUS,
                };
                p.rect_filled(card, rounding, CARD);
                p.rect_stroke(
                    card,
                    rounding,
                    Stroke::new(1.0_f32, with_alpha(accent, 0.18 + 0.55 * glow)),
                );

                // ---- header row
                let cy = card.top() + notch_h / 2.0;
                let status_dot_color = match (&header, has_pending_perm) {
                    (_, true) => WARN,
                    (Some(h), false) => status_color(&h.status),
                    (None, false) => TRACK, // nothing running: a dim, dead dot
                };
                p.circle_filled(
                    pos2(card.left() + 16.0, cy),
                    3.5 * pulse,
                    status_dot_color,
                );
                // Brand mark where the agent name used to be — a logo reads at a glance in
                // a 32pt strip in a way an 11.5pt word never does.
                let logo = match (&header, has_pending_perm) {
                    (Some(h), false) => logo_of(&h.agent_type),
                    _ => None,
                };
                match logo {
                    Some(src) => {
                        let side = 15.0;
                        ui.allocate_ui_at_rect(
                            egui::Rect::from_min_size(
                                pos2(card.left() + 26.0, cy - side / 2.0),
                                vec2(side, side),
                            ),
                            |ui| {
                                ui.add(egui::Image::new(src).fit_to_exact_size(vec2(side, side)));
                            },
                        );
                    }
                    None => {
                        p.text(
                            pos2(card.left() + 27.0, cy),
                            Align2::LEFT_CENTER,
                            match (&header, has_pending_perm) {
                                (_, true) => "⚠️ PERM REQ",
                                (Some(h), false) => label_of(&h.agent_type),
                                (None, false) => "No agent",
                            },
                            FontId::proportional(11.5),
                            accent,
                        );
                    }
                }

                // No expand/collapse chevron: egui's default font has no glyph for ▴/▾, so
                // it rendered as a tofu box. Not worth bundling a font for — the whole bar
                // is the click target anyway.
                p.text(
                    pos2(card.right() - 14.0, cy),
                    Align2::RIGHT_CENTER,
                    match (&header, has_pending_perm) {
                        (_, true) => "Action Needed",
                        (Some(h), false) => status_label(&h.status),
                        (None, false) => "Not running",
                    },
                    FontId::proportional(11.5),
                    if header.is_some() { TEXT } else { DIM },
                );

                // ---- bottom edge gauge (nothing running -> nothing to gauge, don't paint one)
                if let Some(h) = &header {
                    let used = usage_fraction(h.tokens_used, h.token_limit);
                    let gy = card.bottom() - 2.5;
                    let (gl, gr) = (card.left() + BOTTOM_RADIUS, card.right() - BOTTOM_RADIUS);
                    let gauge = if used >= 0.9 || has_pending_perm { WARN } else { accent };
                    p.line_segment([pos2(gl, gy), pos2(gr, gy)], Stroke::new(1.5_f32, TRACK));
                    p.line_segment(
                        [pos2(gl, gy), pos2(gl + (gr - gl) * used, gy)],
                        Stroke::new(1.5_f32, with_alpha(gauge, 0.45 + 0.55 * glow)),
                    );
                }

                // ---- drawer content
                if self.mode == HudMode::Drawer {
                    let x = card.left() + PAD;
                    let wrap = card.width() - PAD * 2.0;
                    let mut y = card.top() + notch_h;

                    let rule = |y: f32| {
                        p.line_segment(
                            [pos2(x, y), pos2(x + wrap, y)],
                            Stroke::new(1.0_f32, TRACK),
                        );
                    };
                    rule(y);

                    // 1. Session Tabs Strip & Launch Button
                    y += 6.0;
                    // HashMap iteration order is arbitrary and reshuffles every frame —
                    // sort so tabs hold still under the cursor.
                    let mut tabs: Vec<_> = s.sessions.values().collect();
                    tabs.sort_by(|a, b| a.session_id.cmp(&b.session_id));
                    ui.allocate_ui_at_rect(
                        egui::Rect::from_min_size(pos2(x, y), vec2(wrap, 20.0)),
                        |ui| {
                            ui.horizontal(|ui| {
                                // Launch stays pinned; only the tabs scroll, so the button
                                // can never be pushed off the edge by a long session list.
                                if ui.button(egui::RichText::new("🚀 + Launch").color(TEXT).size(10.0)).clicked() {
                                    self.show_launch_input = !self.show_launch_input;
                                }
                                egui::ScrollArea::horizontal()
                                    .id_source("session-tabs")
                                    // Leave room for Quit so tabs never push it off the edge.
                                    .max_width((ui.available_width() - 44.0).max(0.0))
                                    .show(ui, |ui| {
                                        ui.horizontal(|ui| {
                                            for sess in tabs {
                                                let is_active =
                                                    s.active_session_id.as_deref() == Some(sess.session_id.as_str());
                                                let text_color = if sess.status == AgentStatus::Error {
                                                    ERROR
                                                } else if is_active {
                                                    accent
                                                } else {
                                                    DIM
                                                };
                                                let tab_label = format!("[{}]", sess.agent_name);
                                                if ui.button(egui::RichText::new(tab_label).color(text_color).size(10.0)).clicked() {
                                                    let mut state_guard = self.state.lock().unwrap();
                                                    state_guard.select_session(&sess.session_id);
                                                }
                                            }
                                        });
                                    });
                                // The right-click context menu can't help when collapsed: an
                                // egui menu is an Area clipped to the viewport, and the
                                // collapsed viewport is 32pt tall — nowhere to draw. This
                                // button is the affordance that always works.
                                if ui.button(egui::RichText::new("Quit").color(DIM).size(10.0)).clicked() {
                                    std::process::exit(0);
                                }
                            });
                        },
                    );

                    y += 22.0;

                    // Launcher inline form if toggled
                    if self.show_launch_input {
                        rule(y);
                        y += 6.0;
                        ui.allocate_ui_at_rect(
                            egui::Rect::from_min_size(pos2(x, y), vec2(wrap, 62.0)),
                            |ui| {
                                ui.horizontal(|ui| {
                                    ui.label(egui::RichText::new("Cmd:").size(10.0).color(DIM));
                                    // Dropdown over CLIs actually installed here, not every
                                    // agent that exists. Offering one you don't have is just
                                    // a launch failure the user could have been spared.
                                    let selected = if self.launch_custom {
                                        "Custom…".to_string()
                                    } else {
                                        cli_label(std::path::Path::new(&self.launch_cmd))
                                    };
                                    egui::ComboBox::from_id_source("launch-agent")
                                        .width(84.0)
                                        .selected_text(egui::RichText::new(selected).size(10.0))
                                        .show_ui(ui, |ui| {
                                            for cli in &self.available_clis {
                                                let picked = !self.launch_custom
                                                    && self.launch_cmd == cli.to_string_lossy();
                                                if ui
                                                    .selectable_label(
                                                        picked,
                                                        egui::RichText::new(cli_label(cli)).size(10.0),
                                                    )
                                                    .clicked()
                                                {
                                                    self.launch_cmd = cli.to_string_lossy().to_string();
                                                    self.launch_custom = false;
                                                }
                                            }
                                            if ui
                                                .selectable_label(
                                                    self.launch_custom,
                                                    egui::RichText::new("Custom…").size(10.0),
                                                )
                                                .clicked()
                                            {
                                                self.launch_custom = true;
                                                self.launch_cmd.clear();
                                            }
                                        });
                                    if self.launch_custom {
                                        ui.add(egui::TextEdit::singleline(&mut self.launch_cmd).desired_width(64.0));
                                    }
                                    ui.label(egui::RichText::new("Dir:").size(10.0).color(DIM));
                                    ui.add(egui::TextEdit::singleline(&mut self.launch_dir).desired_width(120.0));
                                    // MUST be the async dialog. The sync `FileDialog` runs
                                    // `NSOpenPanel::runModal`, which spins a *nested* native
                                    // run loop — and this handler is already inside winit's
                                    // event callback. That reentrancy wedges the event loop:
                                    // beachball, no panel. `AsyncFileDialog` presents via a
                                    // completion handler instead, so the loop keeps turning.
                                    if ui.button(egui::RichText::new("📁").size(10.0)).clicked() {
                                        // ...but the async panel is a *sheet on the HUD window*,
                                        // and an inactive Accessory app can't make a sheet key.
                                        // Without this the panel opens dead and window-modal:
                                        // the HUD stops taking clicks and the cursor spins
                                        // forever. See `notch::activate_app`.
                                        notch::activate_app();
                                        let slot = self.picked_dir.clone();
                                        let start = self.launch_dir.clone();
                                        let busy = self.picker_busy.clone();
                                        busy.store(true, std::sync::atomic::Ordering::Relaxed);
                                        self.rt.spawn(async move {
                                            let mut dialog = rfd::AsyncFileDialog::new();
                                            if !start.is_empty() {
                                                dialog = dialog.set_directory(&start);
                                            }
                                            if let Some(handle) = dialog.pick_folder().await {
                                                *slot.lock().unwrap() =
                                                    Some(handle.path().to_string_lossy().to_string());
                                            }
                                            // Cleared on cancel too — otherwise a dismissed
                                            // picker leaves the HUD permanently unable to
                                            // auto-collapse.
                                            busy.store(false, std::sync::atomic::Ordering::Relaxed);
                                        });
                                    }
                                });
                                // ponytail: no "Prompt:" field. The session opens straight
                                // into its own terminal, so the first message is just the
                                // first thing you type — a one-shot prompt box was a second,
                                // worse way to say the same thing, and it couldn't answer a
                                // follow-up question the agent asked.
                                ui.horizontal(|ui| {
                                    if ui.button(egui::RichText::new("Spawn").color(Color32::from_rgb(52, 199, 123)).size(10.0)).clicked() {
                                        let payload = SessionLaunchPayload {
                                            agent_command: self.launch_cmd.clone(),
                                            working_directory: self.launch_dir.clone(),
                                        };
                                        // `block_on`, not `spawn`: opening a pty and forking
                                        // is sub-millisecond, and the session id has to come
                                        // back on *this* frame to open its terminal. This
                                        // thread is outside the runtime, so blocking on it is
                                        // legal (a bare `tokio::spawn` here would panic — see
                                        // the `rt` field).
                                        let (session_id, failed) =
                                            self.rt.block_on(launch_session(
                                                &self.state,
                                                &self.terminals,
                                                &payload,
                                            ));
                                        self.show_launch_input = false;
                                        // A failed launch has no pty; the failure card in the
                                        // drawer is what the user needs to see, not an empty
                                        // terminal.
                                        if failed.is_none() {
                                            self.open_terminal(ctx, &session_id);
                                        }
                                    }
                                });
                            },
                        );
                        y += 52.0;
                    }

                    // 2. Pending Permission Prompt Card (Urgent)
                    if let Some(perm) = s.pending_permissions.first() {
                        rule(y);
                        y += 6.0;
                        p.text(
                            pos2(x, y),
                            Align2::LEFT_TOP,
                            format!("APPROVAL REQUIRED ({})", perm.agent_name.to_uppercase()),
                            FontId::proportional(9.0),
                            WARN,
                        );
                        y += 13.0;
                        // Advance by what the galley *measured*, not a guess. A wrapped
                        // two-line detail used to be painted under the buttons below it.
                        let details_galley = ui.fonts(|f| {
                            f.layout(
                                format!("{}: {}", perm.action_type, perm.details),
                                FontId::monospace(10.0),
                                TEXT,
                                wrap,
                            )
                        });
                        let details_h = details_galley.size().y;
                        p.galley(pos2(x, y), details_galley, TEXT);
                        y += details_h + 4.0;

                        ui.allocate_ui_at_rect(
                            egui::Rect::from_min_size(pos2(x, y), vec2(wrap, 22.0)),
                            |ui| {
                                ui.horizontal(|ui| {
                                    if ui.button(egui::RichText::new("✓ Approve").color(Color32::from_rgb(52, 199, 123)).size(11.0)).clicked() {
                                        resolve_permission_channel(&self.channels, self.state.clone(), &perm.request_id, true);
                                    }
                                    if ui.button(egui::RichText::new("✗ Deny").color(WARN).size(11.0)).clicked() {
                                        resolve_permission_channel(&self.channels, self.state.clone(), &perm.request_id, false);
                                    }
                                });
                            },
                        );
                        y += 24.0;
                        y += queued_more(&p, pos2(x, y), s.pending_permissions.len());
                    }

                    // 2b. Launch Failure Prompt Card — same shape as the permission card
                    if let Some(fail) = s.pending_launch_failures.first() {
                        rule(y);
                        y += 6.0;
                        p.text(
                            pos2(x, y),
                            Align2::LEFT_TOP,
                            format!("LAUNCH FAILED ({})", fail.agent_name.to_uppercase()),
                            FontId::proportional(9.0),
                            ERROR,
                        );
                        y += 13.0;
                        // Was `y += 18.0` regardless of how tall the reason wrapped to. A
                        // spawn failure's text runs to several lines, so Kill it/Later,
                        // LOCAL AGENTS and ACTIVITY all got painted on top of each other.
                        let reason_galley = ui.fonts(|f| {
                            f.layout(fail.reason.clone(), FontId::monospace(10.0), TEXT, wrap)
                        });
                        let reason_h = reason_galley.size().y;
                        p.galley(pos2(x, y), reason_galley, TEXT);
                        y += reason_h + 4.0;

                        ui.allocate_ui_at_rect(
                            egui::Rect::from_min_size(pos2(x, y), vec2(wrap, 22.0)),
                            |ui| {
                                ui.horizontal(|ui| {
                                    if ui.button(egui::RichText::new("🗑 Kill it").color(ERROR).size(11.0)).clicked() {
                                        self.state.lock().unwrap().remove_session(&fail.session_id);
                                    }
                                    // "Later" drops only the prompt — the tab stays red so the
                                    // failed attempt is still on record.
                                    if ui.button(egui::RichText::new("Later").color(DIM).size(11.0)).clicked() {
                                        self.state.lock().unwrap().dismiss_launch_failure(&fail.session_id);
                                    }
                                });
                            },
                        );
                        y += 24.0;
                        y += queued_more(&p, pos2(x, y), s.pending_launch_failures.len());
                    }

                    // 3. Session Section
                    // ponytail: no ACTIVITY step-description block — a wall of 10pt monospace
                    // nobody reads, and its unbounded height overran the rows below it.
                    rule(y);
                    y += 8.0;
                    // "CONTEXT", not "SESSION": this is context-window fill, the only usage
                    // number a transcript actually reports. Plan/5-hour/weekly quota lives
                    // behind the API, not on disk — so it isn't shown rather than guessed.
                    p.text(
                        pos2(x, y),
                        Align2::LEFT_TOP,
                        "CONTEXT",
                        FontId::proportional(9.0),
                        DIM,
                    );
                    let (d_used, d_limit) = match &drawer {
                        Some(d) => (d.tokens_used, d.token_limit),
                        None => (0, 0),
                    };
                    let d_frac = usage_fraction(d_used, d_limit);
                    p.text(
                        pos2(x + wrap, y),
                        Align2::RIGHT_TOP,
                        if drawer.is_some() {
                            format!(
                                "{} / {}  ·  {:.0}%",
                                thousands(d_used),
                                thousands(d_limit),
                                d_frac * 100.0
                            )
                        } else {
                            "—".to_string()
                        },
                        FontId::monospace(9.5),
                        if d_frac >= 0.9 { WARN } else if drawer.is_some() { TEXT } else { DIM },
                    );

                    // ponytail: no "$X spent / resets in Yh Zm" row. Both were
                    // `SessionLimit::default()` constants that nothing ever updated — a
                    // hardcoded $0.14 and a frozen 2h 14m countdown. Same fake-data problem
                    // as the seeded demo session (D13). Real plan usage (5-hour, weekly)
                    // isn't on disk anywhere; it comes off API response headers per request.

                    // From here down the sections are optional and the space above them is
                    // variable (a wrapped failure reason can eat most of the drawer). Each
                    // one must claim its room before it paints, or it lands on top of the
                    // section before it — which is exactly what a fixed `y +=` used to do.
                    // Gate against the drawer's *maximum* height, not the current window.
                    // The window is now sized to last frame's content, so gating on it
                    // would mean a section could never grow back once it had been skipped
                    // once — the window would already have shrunk to exclude it.
                    let floor = card.top() + notch_h + DRAWER_HEIGHT;
                    let room_for = |y: f32, needed: f32| y + needed <= floor;

                    // 4. Local Agents — agent CLIs running anywhere on this machine.
                    // 20 (rule + heading) + 20 per row.
                    if !s.detected_processes.is_empty()
                        && room_for(y, 40.0 + 20.0 * s.detected_processes.len().min(3) as f32)
                    {
                        y += 20.0;
                        rule(y);
                        y += 8.0;
                        p.text(
                            pos2(x, y),
                            Align2::LEFT_TOP,
                            "LOCAL AGENTS",
                            FontId::proportional(9.0),
                            DIM,
                        );
                        // Says why these rows have no terminal: they were started
                        // elsewhere, and a process's tty belongs to whoever opened it.
                        p.text(
                            pos2(x + wrap, y),
                            Align2::RIGHT_TOP,
                            "started elsewhere · monitor + kill",
                            FontId::proportional(8.5),
                            TRACK,
                        );
                        y += 12.0;
                        for proc in s.detected_processes.iter().take(3) {
                            let row_rect = egui::Rect::from_min_size(pos2(x, y), vec2(wrap, 18.0));
                            ui.allocate_ui_at_rect(row_rect, |ui| {
                                ui.horizontal(|ui| {
                                    ui.label(
                                        egui::RichText::new(format!("{} ({})", proc.name, proc.pid))
                                            .monospace()
                                            .size(9.5)
                                            .color(TEXT),
                                    );
                                    ui.with_layout(
                                        egui::Layout::right_to_left(egui::Align::Center),
                                        |ui| {
                                            // A stale PID (already exited since the last
                                            // scan) or a permissions error both fail
                                            // silently here — the next scan tick drops it
                                            // from the list either way.
                                            if ui
                                                .small_button(
                                                    egui::RichText::new("✕ Kill").color(ERROR).size(9.0),
                                                )
                                                .clicked()
                                            {
                                                let _ = kill_local_process(proc.pid);
                                            }
                                            ui.label(
                                                egui::RichText::new(format!(
                                                    "{:.0}% cpu · {:.0} MB",
                                                    proc.cpu_usage, proc.memory_mb
                                                ))
                                                .monospace()
                                                .size(9.0)
                                                .color(DIM),
                                            );
                                        },
                                    );
                                });
                            });
                            y += 20.0;
                        }
                    }

                    // 5. Activity — one row per session, most-recently-updated first.
                    // Rows are clickable (same `select_session` a tab click uses) so the
                    // pane is something you interact with, not just read. Height-bounded
                    // via `ScrollArea::max_height`, not `p.text`'s unbounded painter text —
                    // that's what got the old ACTIVITY block deleted (see BUGS.md): an
                    // unbounded wall of 10pt monospace overran LOCAL AGENTS below it.
                    // 40 for the rule + heading, 40 for the bounded scroll area.
                    if !s.sessions.is_empty() && room_for(y, 80.0) {
                        y += 20.0;
                        rule(y);
                        y += 8.0;
                        p.text(
                            pos2(x, y),
                            Align2::LEFT_TOP,
                            "ACTIVITY",
                            FontId::proportional(9.0),
                            DIM,
                        );
                        p.text(
                            pos2(x + wrap, y),
                            Align2::RIGHT_TOP,
                            "▸ click to open terminal",
                            FontId::proportional(8.5),
                            TRACK,
                        );
                        y += 12.0;
                        let mut recent: Vec<_> = s.sessions.values().collect();
                        recent.sort_by(|a, b| b.last_updated.cmp(&a.last_updated));
                        // Snapshot the keys and drop the lock before the loop: `open_terminal`
                        // locks `terminals` too, and holding it across the click handler
                        // would deadlock the render thread against itself.
                        let live: std::collections::HashSet<String> =
                            self.terminals.lock().unwrap().keys().cloned().collect();
                        // ACTIVITY is the last section, so it takes whatever drawer is
                        // left rather than a fixed 40pt. The constant left a dead black
                        // band under the list whenever the sections above it were short,
                        // and clipped the list whenever they weren't.
                        // Bounded by the sessions actually listed, not by the space left:
                        // stretching to the floor is what re-created the dead band this
                        // was meant to remove, just inside a scroll area instead of below
                        // it. Four rows then it scrolls.
                        let activity_h = (20.0 * s.sessions.len().min(4) as f32).max(24.0);
                        ui.allocate_ui_at_rect(
                            egui::Rect::from_min_size(pos2(x, y), vec2(wrap, activity_h)),
                            |ui| {
                                egui::ScrollArea::vertical()
                                    .id_source("activity-stream")
                                    .max_height(activity_h)
                                    .show(ui, |ui| {
                                        for sess in recent {
                                            let is_active = s.active_session_id.as_deref()
                                                == Some(sess.session_id.as_str());
                                            let has_term = live.contains(&sess.session_id);
                                            // The marker is the affordance: a row you can
                                            // actually talk to looks different from one that
                                            // only reports.
                                            let label = format!(
                                                "{} {}: {}",
                                                if has_term { "▸" } else { " " },
                                                sess.agent_name,
                                                sess.step_description
                                            );
                                            let row = ui.selectable_label(
                                                is_active,
                                                egui::RichText::new(label)
                                                    .monospace()
                                                    .size(9.0)
                                                    .color(if has_term { TEXT } else { DIM }),
                                            );
                                            if row.clicked() {
                                                if has_term {
                                                    self.open_terminal(ctx, &sess.session_id);
                                                } else {
                                                    self.state
                                                        .lock()
                                                        .unwrap()
                                                        .select_session(&sess.session_id);
                                                }
                                            }
                                            if has_term {
                                                row.on_hover_text("Open this session's terminal");
                                            }
                                        }
                                    });
                            },
                        );
                        y += activity_h;
                    }

                    // What the window should be next frame. Measured, not estimated —
                    // see the docking block.
                    self.measured_drawer_h = Some(y - card.top() - notch_h + DRAWER_SLACK);
                }

                // ---- terminal content
                if self.mode == HudMode::Terminal {
                    let x = card.left() + PAD;
                    let wrap = card.width() - PAD * 2.0;
                    let mut y = card.top() + notch_h;
                    p.line_segment(
                        [pos2(x, y), pos2(x + wrap, y)],
                        Stroke::new(1.0_f32, TRACK),
                    );
                    y += 6.0;

                    let session_id = self.terminal_session.clone();
                    let title = session_id
                        .as_ref()
                        .and_then(|id| s.sessions.get(id))
                        .map(|sess| sess.agent_name.clone())
                        .unwrap_or_else(|| "session".to_string());

                    ui.allocate_ui_at_rect(
                        egui::Rect::from_min_size(pos2(x, y), vec2(wrap, 20.0)),
                        |ui| {
                            ui.horizontal(|ui| {
                                if ui
                                    .button(egui::RichText::new("◂ Sessions").color(TEXT).size(10.0))
                                    .clicked()
                                {
                                    self.mode = HudMode::Drawer;
                                }
                                ui.label(
                                    egui::RichText::new(format!("[{title}]"))
                                        .color(accent)
                                        .monospace()
                                        .size(10.0),
                                );
                                ui.with_layout(
                                    egui::Layout::right_to_left(egui::Align::Center),
                                    |ui| {
                                        if ui
                                            .button(egui::RichText::new("Quit").color(DIM).size(10.0))
                                            .clicked()
                                        {
                                            std::process::exit(0);
                                        }
                                        if ui
                                            .button(
                                                egui::RichText::new("✕ End session")
                                                    .color(ERROR)
                                                    .size(10.0),
                                            )
                                            .clicked()
                                        {
                                            if let Some(id) = &session_id {
                                                if let Some(t) =
                                                    self.terminals.lock().unwrap().get_mut(id)
                                                {
                                                    t.kill();
                                                }
                                            }
                                            // The reap pass next frame removes the pty and
                                            // drops us back to the drawer.
                                        }
                                        ui.label(
                                            egui::RichText::new("keystrokes go to the agent")
                                                .color(TRACK)
                                                .size(9.0),
                                        );
                                    },
                                );
                            });
                        },
                    );
                    y += 26.0;

                    let term_rect = egui::Rect::from_min_max(
                        pos2(x, y),
                        pos2(card.right() - PAD, card.bottom() - 8.0),
                    );
                    // A touch darker than the card, so the terminal reads as a well rather
                    // than as more HUD chrome.
                    p.rect_filled(
                        term_rect.expand(4.0),
                        Rounding::same(6.0),
                        Color32::from_rgb(6, 7, 10),
                    );

                    let grid = session_id.as_ref().and_then(|id| {
                        let terms = self.terminals.lock().unwrap();
                        let t = terms.get(id)?;
                        let parser = t.parser.lock().ok()?;
                        Some(paint_terminal(ui, term_rect, parser.screen()))
                    });

                    // Tell the PTY the grid it's actually drawing into, so the TUI reflows
                    // instead of laying out for a size the window no longer is. Only on a
                    // real change — resizing every frame makes agents redraw constantly.
                    if let (Some(grid), Some(id)) = (grid, session_id.as_ref()) {
                        if grid != self.term_grid {
                            self.term_grid = grid;
                            if let Some(t) = self.terminals.lock().unwrap().get_mut(id) {
                                t.resize(grid.0, grid.1);
                            }
                        }
                    }
                }

                // Only the header strip toggles collapse/expand. The old version sensed
                // clicks over the whole card, underneath every drawer button — egui doesn't
                // give overlapping Sense::click() regions mutual exclusion, so clicking
                // Approve/Deny/a session tab also collapsed the drawer in the same frame,
                // discarding the click before it could resolve anything.
                let header_rect = egui::Rect::from_min_size(card.min, vec2(card.width(), notch_h));
                let hit = ui.interact(header_rect, egui::Id::new("notch-hud"), Sense::click());
                if hit.clicked() {
                    // From the terminal, the notch is a step back to the session list, not
                    // a way to slam the whole panel shut on a running agent.
                    self.mode = match self.mode {
                        HudMode::Collapsed => HudMode::Drawer,
                        HudMode::Drawer => HudMode::Collapsed,
                        HudMode::Terminal => HudMode::Drawer,
                    };
                }
                // The app is an Accessory (no Dock icon, no ⌘Q) — without this the only way
                // out is Ctrl+C in whatever terminal launched it.
                hit.context_menu(|ui| {
                    if ui.button("Quit Agent Notch Watcher").clicked() {
                        std::process::exit(0);
                    }
                });
            });
    }
}

fn main() {
    let shared_state: SharedState = Arc::new(Mutex::new(AppState::default()));
    let channels: PermissionChannels = Arc::new(Mutex::new(HashMap::new()));
    let terminals: Terminals = new_terminals();
    let ui_request: UiRequest = Arc::new(Mutex::new(None));

    // The runtime is built here, not inside a worker thread, so the egui thread can get a
    // `Handle` to it. Without one, every `tokio::spawn` from a button handler panics with
    // "must be called from the context of a Tokio 1.x runtime" — the runtime is running,
    // just not on *this* thread. That silently broke the Spawn button.
    let rt = tokio::runtime::Runtime::new().expect("failed to build tokio runtime");
    let rt_handle = rt.handle().clone();

    let server_state = shared_state.clone();
    let server_chans = channels.clone();
    let server_terms = terminals.clone();
    let server_ui = ui_request.clone();
    rt.spawn(async move {
        start_http_server(server_state.clone(), server_chans, server_terms, server_ui);
        start_universal_tailer(server_state).await;
    });
    // ponytail: the runtime lives as long as the app does. Dropping it here would abort the
    // server and tailer the moment `main` moves on to `run_native`.
    std::mem::forget(rt);

    let sys_state = shared_state.clone();
    std::thread::spawn(move || {
        let mut sys = System::new_all();
        loop {
            let detected = scan_system_agents(&mut sys);
            {
                let mut state = sys_state.lock().unwrap();
                state.update_detected_processes(detected);
            }
            std::thread::sleep(Duration::from_millis(1500));
        }
    });

    let geometry = notch::detect_geometry();
    let (w, h) = geometry.hud_size(HudMode::Collapsed);
    let (x, y) = geometry.dock_position(w);
    println!(
        "Docking HUD: screen {:.0}pt, notch {:.0}x{:.0}pt -> {:.0}x{:.0} at ({:.0}, {:.0})",
        geometry.screen_width, geometry.notch_width, geometry.notch_height, w, h, x, y
    );

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("Agent Notch Watcher")
            .with_inner_size([w, h])
            .with_position([x, y])
            .with_transparent(true)
            .with_decorations(false)
            .with_always_on_top()
            .with_resizable(false)
            .with_active(false),
        ..Default::default()
    };

    let app_state = shared_state.clone();
    let app_chans = channels.clone();
    let app_terms = terminals.clone();
    eframe::run_native(
        "StackWatch",
        options,
        Box::new(move |cc| {
            notch::dock_window(cc);
            Ok(Box::new(NotchWatcherApp::new(
                cc, app_state, app_chans, app_terms, ui_request, geometry, rt_handle,
            )))
        }),
    )
    .expect("Failed to launch eframe Native GUI App");
}


#[cfg(test)]
mod tests {
    use super::*;

    fn screen_of(cols: u16, bytes: &[u8]) -> vt100::Parser {
        let mut parser = vt100::Parser::new(3, cols, 0);
        parser.process(bytes);
        parser
    }

    #[test]
    fn test_row_segments_merge_by_style_and_split_on_colour_change() {
        // No screen-recording permission means the painted grid can't be eyeballed, so
        // the run-coalescing is pinned here instead. Merging too eagerly would paint the
        // whole row in one colour; never merging would mean one text section per cell.
        let p = screen_of(10, b"ab\x1b[31mcd\x1b[m");
        let segs = row_segments(p.screen(), 0);
        assert_eq!(segs[0].text, "ab", "same style runs together");
        assert_eq!(segs[1].text, "cd", "a colour change starts a new run");
        assert_eq!(segs[1].fg, ansi_color(1), "red is palette index 1");
        assert_ne!(segs[0].fg, segs[1].fg);
        // Trailing blanks are still emitted, as spaces, so the row stays grid-aligned.
        assert_eq!(segs.iter().map(|s| s.width).sum::<u16>(), 10);
    }

    #[test]
    fn test_row_segments_keep_wide_glyphs_one_cell_pair() {
        // A CJK glyph covers two cells; the second is a continuation that reports empty
        // contents. Emitting a space for it would shift the rest of the row left by one.
        let p = screen_of(6, "日本x".as_bytes());
        let segs = row_segments(p.screen(), 0);
        let text: String = segs.iter().map(|s| s.text.as_str()).collect();
        assert!(text.starts_with("日本x"), "got {text:?}");
        assert_eq!(
            segs.iter().map(|s| s.width).sum::<u16>(),
            6,
            "widths must total the grid, counting each wide glyph as two cells"
        );
    }

    #[test]
    fn test_row_segments_swap_colours_for_inverse_video() {
        // How a TUI paints its selected row. Without this the highlight vanishes.
        let p = screen_of(4, b"\x1b[7mSEL\x1b[m");
        let segs = row_segments(p.screen(), 0);
        assert_eq!(segs[0].text, "SEL");
        assert_eq!(segs[0].fg, CARD, "inverse text takes the card colour");
        assert_eq!(segs[0].bg, TEXT, "...on a filled background");
    }

    #[test]
    fn test_control_keys_map_to_their_escape_sequences() {
        use egui::{Key, Modifiers};
        assert_eq!(key_bytes(Key::Enter, &Modifiers::NONE), Some(b"\r".to_vec()));
        assert_eq!(
            key_bytes(Key::ArrowUp, &Modifiers::NONE),
            Some(b"\x1b[A".to_vec())
        );
        // Backspace must be DEL, not BS — readline and every TUI on macOS expect 0x7f.
        assert_eq!(key_bytes(Key::Backspace, &Modifiers::NONE), Some(vec![0x7f]));
        // ^C is how you interrupt a running agent.
        assert_eq!(
            key_bytes(Key::C, &Modifiers { ctrl: true, ..Default::default() }),
            Some(vec![0x03])
        );
        // A plain letter arrives as Event::Text; returning bytes here too would type it twice.
        assert_eq!(key_bytes(Key::C, &Modifiers::NONE), None);
    }
}
