mod notch;

use agent_notch_watcher::{
    match_agent_type_from_name, resolve_permission_channel, scan_system_agents,
    start_universal_tailer, thousands, AgentEvent, AgentStatus, AgentType, AppState,
    NotchGeometry, PermissionChannels, PermissionRequest, PermissionResponse,
    SessionLaunchPayload, SharedState,
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

const PAD: f32 = 18.0;
const BOTTOM_RADIUS: f32 = 14.0;

// ---------------------------------------------------------------- HTTP

#[derive(Clone)]
struct ServerRouterState {
    shared_state: SharedState,
    channels: PermissionChannels,
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
    let session_id = format!(
        "session-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis()
    );
    let agent_type = match_agent_type_from_name(&payload.agent_command);

    {
        let mut app_state = srv.shared_state.lock().unwrap();
        app_state.register_session(&session_id, agent_type, &payload.agent_command);
    }

    let mut cmd = tokio::process::Command::new(&payload.agent_command);
    if !payload.working_directory.is_empty() {
        cmd.current_dir(&payload.working_directory);
    }
    if !payload.initial_prompt.is_empty() {
        cmd.arg(&payload.initial_prompt);
    }
    let _ = cmd.spawn();

    (
        StatusCode::OK,
        Json(serde_json::json!({
            "status": "launched",
            "session_id": session_id,
            "agent_command": payload.agent_command
        })),
    )
}

fn start_http_server(shared_state: SharedState, channels: PermissionChannels) {
    let server_router_state = ServerRouterState {
        shared_state,
        channels,
    };

    tokio::spawn(async move {
        let app = Router::new()
            .route("/", get(handle_get_index))
            .route("/state", get(handle_get_state))
            .route("/event", post(handle_post_event))
            .route("/permission/request", post(handle_permission_request))
            .route("/session/launch", post(handle_session_launch))
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
    }
}

fn status_label(status: &AgentStatus) -> &'static str {
    match status {
        AgentStatus::Idle => "Ready",
        AgentStatus::Thinking => "Thinking",
        AgentStatus::ToolExecuting => "Running tool",
        AgentStatus::QuotaWarning => "Quota low",
    }
}

fn with_alpha(color: Color32, alpha: f32) -> Color32 {
    Color32::from_rgba_unmultiplied(
        color.r(),
        color.g(),
        color.b(),
        (alpha.clamp(0.0, 1.0) * 255.0) as u8,
    )
}

// ---------------------------------------------------------------- app

struct NotchWatcherApp {
    state: SharedState,
    channels: PermissionChannels,
    geometry: NotchGeometry,
    expanded: bool,
    docked_as: Option<bool>,
    start_time: Instant,
    show_launch_input: bool,
    launch_cmd: String,
    launch_dir: String,
}

impl NotchWatcherApp {
    fn new(
        cc: &eframe::CreationContext<'_>,
        state: SharedState,
        channels: PermissionChannels,
        geometry: NotchGeometry,
    ) -> Self {
        let mut visuals = egui::Visuals::dark();
        visuals.window_fill = Color32::TRANSPARENT;
        visuals.panel_fill = Color32::TRANSPARENT;
        cc.egui_ctx.set_visuals(visuals);

        Self {
            state,
            channels,
            geometry,
            expanded: false,
            docked_as: None,
            start_time: Instant::now(),
            show_launch_input: false,
            launch_cmd: "claude".to_string(),
            launch_dir: std::env::current_dir()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default(),
        }
    }
}

impl eframe::App for NotchWatcherApp {
    fn clear_color(&self, _visuals: &egui::Visuals) -> [f32; 4] {
        [0.0, 0.0, 0.0, 0.0]
    }

    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        ctx.request_repaint_after(Duration::from_millis(33));

        if self.docked_as != Some(self.expanded) {
            let (w, h) = self.geometry.hud_size(self.expanded);
            let (x, y) = self.geometry.dock_position(w);
            ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(vec2(w, h)));
            ctx.send_viewport_cmd(egui::ViewportCommand::OuterPosition(pos2(x, y)));
            self.docked_as = Some(self.expanded);
        }

        let s = self.state.lock().unwrap().clone();
        let elapsed = self.start_time.elapsed().as_secs_f32();
        let pulse = s.glow_setting.pulse_at(elapsed);
        let has_pending_perm = !s.pending_permissions.is_empty();
        let glow = if has_pending_perm {
            1.0
        } else {
            s.glow_setting.intensity() * pulse
        };
        let accent = if has_pending_perm {
            WARN
        } else {
            accent_of(&s.agent_type)
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
                let status_dot_color = if has_pending_perm { WARN } else { status_color(&s.status) };
                p.circle_filled(
                    pos2(card.left() + 16.0, cy),
                    3.5 * pulse,
                    status_dot_color,
                );
                p.text(
                    pos2(card.left() + 27.0, cy),
                    Align2::LEFT_CENTER,
                    if has_pending_perm { "⚠️ PERM REQ" } else { label_of(&s.agent_type) },
                    FontId::proportional(11.5),
                    accent,
                );

                p.text(
                    pos2(card.right() - 14.0, cy),
                    Align2::RIGHT_CENTER,
                    if self.expanded { "▴" } else { "▾" },
                    FontId::proportional(10.0),
                    DIM,
                );
                p.text(
                    pos2(card.right() - 28.0, cy),
                    Align2::RIGHT_CENTER,
                    if has_pending_perm { "Action Needed" } else { status_label(&s.status) },
                    FontId::proportional(11.5),
                    TEXT,
                );

                // ---- bottom edge gauge
                let lim = &s.session_limit;
                let used = (lim.usage_percentage() / 100.0).clamp(0.0, 1.0) as f32;
                let gy = card.bottom() - 2.5;
                let (gl, gr) = (card.left() + BOTTOM_RADIUS, card.right() - BOTTOM_RADIUS);
                let gauge = if lim.is_warning_threshold() || has_pending_perm { WARN } else { accent };
                p.line_segment([pos2(gl, gy), pos2(gr, gy)], Stroke::new(1.5_f32, TRACK));
                p.line_segment(
                    [pos2(gl, gy), pos2(gl + (gr - gl) * used, gy)],
                    Stroke::new(1.5_f32, with_alpha(gauge, 0.45 + 0.55 * glow)),
                );

                // ---- drawer content
                if self.expanded {
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
                    ui.allocate_ui_at_rect(
                        egui::Rect::from_min_size(pos2(x, y), vec2(wrap, 20.0)),
                        |ui| {
                            ui.horizontal(|ui| {
                                for (sid, sess) in s.sessions.iter() {
                                    let is_active = sid == &s.active_session_id;
                                    let tab_label = format!("[{}]", sess.agent_name);
                                    let text_color = if is_active { accent } else { DIM };
                                    if ui.button(egui::RichText::new(tab_label).color(text_color).size(10.0)).clicked() {
                                        let mut state_guard = self.state.lock().unwrap();
                                        state_guard.select_session(sid);
                                    }
                                }
                                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                    if ui.button(egui::RichText::new("🚀 + Launch").color(TEXT).size(10.0)).clicked() {
                                        self.show_launch_input = !self.show_launch_input;
                                    }
                                });
                            });
                        },
                    );

                    y += 22.0;

                    // Launcher inline form if toggled
                    if self.show_launch_input {
                        rule(y);
                        y += 6.0;
                        ui.allocate_ui_at_rect(
                            egui::Rect::from_min_size(pos2(x, y), vec2(wrap, 40.0)),
                            |ui| {
                                ui.horizontal(|ui| {
                                    ui.label(egui::RichText::new("Cmd:").size(10.0).color(DIM));
                                    ui.add(egui::TextEdit::singleline(&mut self.launch_cmd).desired_width(70.0));
                                    ui.label(egui::RichText::new("Dir:").size(10.0).color(DIM));
                                    ui.add(egui::TextEdit::singleline(&mut self.launch_dir).desired_width(120.0));
                                    if ui.button(egui::RichText::new("Spawn").color(Color32::from_rgb(52, 199, 123)).size(10.0)).clicked() {
                                        let cmd_str = self.launch_cmd.clone();
                                        let dir_str = self.launch_dir.clone();
                                        let state_ref = self.state.clone();
                                        tokio::spawn(async move {
                                            let session_id = format!("session-{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_millis());
                                            let agent_type = match_agent_type_from_name(&cmd_str);
                                            {
                                                let mut app = state_ref.lock().unwrap();
                                                app.register_session(&session_id, agent_type, &cmd_str);
                                            }
                                            let mut command = tokio::process::Command::new(&cmd_str);
                                            if !dir_str.is_empty() {
                                                command.current_dir(&dir_str);
                                            }
                                            let _ = command.spawn();
                                        });
                                        self.show_launch_input = false;
                                    }
                                });
                            },
                        );
                        y += 30.0;
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
                        let details_galley = ui.fonts(|f| {
                            f.layout(
                                format!("{}: {}", perm.action_type, perm.details),
                                FontId::monospace(10.0),
                                TEXT,
                                wrap,
                            )
                        });
                        p.galley(pos2(x, y), details_galley, TEXT);
                        y += 18.0;

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
                    }

                    // 3. Activity Section
                    rule(y);
                    y += 8.0;
                    p.text(
                        pos2(x, y),
                        Align2::LEFT_TOP,
                        "ACTIVITY",
                        FontId::proportional(9.0),
                        DIM,
                    );
                    y += 12.0;
                    let galley = ui.fonts(|f| {
                        f.layout(
                            s.step_description.clone(),
                            FontId::monospace(10.0),
                            TEXT,
                            wrap,
                        )
                    });
                    p.galley(pos2(x, y), galley, TEXT);

                    y += 24.0;
                    rule(y);
                    y += 8.0;
                    p.text(
                        pos2(x, y),
                        Align2::LEFT_TOP,
                        "SESSION",
                        FontId::proportional(9.0),
                        DIM,
                    );
                    p.text(
                        pos2(x + wrap, y),
                        Align2::RIGHT_TOP,
                        format!(
                            "{} / {}  ·  {:.0}%",
                            thousands(lim.tokens_used),
                            thousands(lim.token_limit),
                            lim.usage_percentage()
                        ),
                        FontId::monospace(9.5),
                        if lim.is_warning_threshold() { WARN } else { TEXT },
                    );

                    y += 14.0;
                    p.text(
                        pos2(x, y),
                        Align2::LEFT_TOP,
                        format!("${:.2} spent", lim.budget_used),
                        FontId::proportional(9.5),
                        DIM,
                    );
                    p.text(
                        pos2(x + wrap, y),
                        Align2::RIGHT_TOP,
                        format!("resets in {}", lim.formatted_time_remaining()),
                        FontId::proportional(9.5),
                        DIM,
                    );

                    // 4. Local Agents — top 3 detected processes (documented in README, never painted)
                    if !s.detected_processes.is_empty() {
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
                        y += 12.0;
                        for proc in s.detected_processes.iter().take(3) {
                            p.text(
                                pos2(x, y),
                                Align2::LEFT_TOP,
                                format!("{} ({})", proc.name, proc.pid),
                                FontId::monospace(9.5),
                                TEXT,
                            );
                            p.text(
                                pos2(x + wrap, y),
                                Align2::RIGHT_TOP,
                                format!("{:.0}% cpu · {:.0} MB", proc.cpu_usage, proc.memory_mb),
                                FontId::monospace(9.0),
                                DIM,
                            );
                            y += 13.0;
                        }
                    }
                }

                // Only the header strip toggles collapse/expand. The old version sensed
                // clicks over the whole card, underneath every drawer button — egui doesn't
                // give overlapping Sense::click() regions mutual exclusion, so clicking
                // Approve/Deny/a session tab also collapsed the drawer in the same frame,
                // discarding the click before it could resolve anything.
                let header = egui::Rect::from_min_size(card.min, vec2(card.width(), notch_h));
                let hit = ui.interact(header, egui::Id::new("notch-hud"), Sense::click());
                if hit.clicked() {
                    self.expanded = !self.expanded;
                }
            });
    }
}

fn main() {
    let shared_state: SharedState = Arc::new(Mutex::new(AppState::default()));
    let channels: PermissionChannels = Arc::new(Mutex::new(HashMap::new()));

    let server_state = shared_state.clone();
    let server_chans = channels.clone();
    std::thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            start_http_server(server_state.clone(), server_chans);
            start_universal_tailer(server_state.clone()).await;
        });
    });

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
    let (w, h) = geometry.hud_size(false);
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
    eframe::run_native(
        "Agent Notch Watcher",
        options,
        Box::new(move |cc| {
            notch::dock_window(cc);
            Ok(Box::new(NotchWatcherApp::new(cc, app_state, app_chans, geometry)))
        }),
    )
    .expect("Failed to launch eframe Native GUI App");
}

