use super::*;

#[test]
fn test_default_state() {
    let state = AppState::default();
    assert_eq!(state.agent_type, AgentType::Anthropic);
    assert_eq!(state.status, AgentStatus::Idle);
    assert_eq!(state.glow_setting, GlowSetting::Max);
    assert_eq!(state.session_limit.tokens_used, 74200);
}

#[test]
fn test_usage_percentage_calculation() {
    let mut limit = SessionLimit::default();
    limit.tokens_used = 50000;
    limit.token_limit = 100000;
    assert_eq!(limit.usage_percentage(), 50.0);

    limit.tokens_used = 95000;
    assert_eq!(limit.usage_percentage(), 95.0);
}

#[test]
fn test_warning_threshold_detection() {
    let mut limit = SessionLimit::default();
    limit.tokens_used = 89000;
    limit.token_limit = 100000;
    assert!(!limit.is_warning_threshold());

    limit.tokens_used = 92000;
    assert!(limit.is_warning_threshold());
}

#[test]
fn test_formatted_time_remaining() {
    let mut limit = SessionLimit::default();
    limit.reset_seconds_remaining = 8040; // 2h 14m
    assert_eq!(limit.formatted_time_remaining(), "2h 14m");
}

#[test]
fn test_event_application() {
    let mut state = AppState::default();
    let event = AgentEvent {
        agent_type: Some(AgentType::Gemini),
        status: AgentStatus::Thinking,
        step_description: "Retrieving context...".to_string(),
        tokens_used: Some(78000),
        glow_setting: Some(GlowSetting::Subtle),
    };

    state.apply_event(event);

    assert_eq!(state.agent_type, AgentType::Gemini);
    assert_eq!(state.status, AgentStatus::Thinking);
    assert_eq!(state.step_description, "Retrieving context...");
    assert_eq!(state.session_limit.tokens_used, 78000);
    assert_eq!(state.glow_setting, GlowSetting::Subtle);
}

#[test]
fn test_event_json_serialization() {
    let json_data = r#"{
        "agent_type": "openai",
        "status": "toolexecuting",
        "step_description": "Executing tool: grep_search",
        "tokens_used": 85000,
        "glow_setting": "off"
    }"#;

    let event: Result<AgentEvent, _> = serde_json::from_str(json_data);
    assert!(event.is_ok());

    let parsed = event.unwrap();
    assert_eq!(parsed.agent_type, Some(AgentType::OpenAi));
    assert_eq!(parsed.status, AgentStatus::ToolExecuting);
    assert_eq!(parsed.glow_setting, Some(GlowSetting::Off));
}

#[test]
fn test_match_agent_type_from_name() {
    assert_eq!(match_agent_type_from_name("ollama"), AgentType::Ollama);
    assert_eq!(match_agent_type_from_name("Claude"), AgentType::Anthropic);
    assert_eq!(match_agent_type_from_name("antigravity"), AgentType::Gemini);
    assert_eq!(match_agent_type_from_name("unknown_bin"), AgentType::Custom);
}

#[test]
fn test_detected_process_struct() {
    let proc = DetectedProcess {
        pid: 1234,
        name: "ollama".to_string(),
        cpu_usage: 12.5,
        memory_mb: 256.0,
        agent_type: AgentType::Ollama,
    };
    assert_eq!(proc.pid, 1234);
    assert_eq!(proc.agent_type, AgentType::Ollama);
}

#[test]
fn test_hud_docks_flush_at_top_center() {
    // The bug: the window was never positioned, so macOS centered it mid-screen.
    let notch = NotchGeometry::fallback(1512.0);
    let (x, y) = notch.dock_position(600.0);
    assert_eq!(y, 0.0, "HUD must sit flush against the top edge, not float");
    assert_eq!(x, 456.0, "HUD must be horizontally centered on the display");
}

#[test]
fn test_hud_content_clears_the_notch_cutout() {
    let notch = NotchGeometry {
        screen_width: 1512.0,
        notch_width: 200.0,
        notch_height: 32.0,
    };
    let (w, h) = notch.hud_size(false);
    let shoulder = notch.shoulder_width(w);
    assert!(shoulder > 0.0, "collapsed HUD needs usable space beside the notch");
    assert_eq!(
        shoulder * 2.0 + notch.notch_width,
        w,
        "shoulders must tile exactly around the cutout"
    );
    assert_eq!(h, 32.0, "collapsed HUD hugs the notch height exactly");
}

#[test]
fn test_expanded_hud_grows_a_drawer_below_the_notch() {
    let notch = NotchGeometry {
        screen_width: 1512.0,
        notch_width: 200.0,
        notch_height: 32.0,
    };
    let (cw, ch) = notch.hud_size(false);
    let (ew, eh) = notch.hud_size(true);
    assert!(ew > cw && eh > ch, "expanding must widen and drop a drawer");
    assert!(ew <= notch.screen_width, "HUD must never exceed the display");
}

#[test]
fn test_glow_setting_drives_the_aura() {
    // Stealth must be genuinely off and genuinely steady — no residual pulse.
    assert_eq!(GlowSetting::Off.intensity(), 0.0);
    assert_eq!(GlowSetting::Off.pulse_at(0.4), 1.0);
    assert_eq!(GlowSetting::Off.pulse_at(7.3), 1.0);

    assert!(GlowSetting::Subtle.intensity() < GlowSetting::Max.intensity());

    let samples: Vec<f32> = (0..40)
        .map(|i| GlowSetting::Max.pulse_at(i as f32 * 0.1))
        .collect();
    let lo = samples.iter().cloned().fold(f32::MAX, f32::min);
    let hi = samples.iter().cloned().fold(f32::MIN, f32::max);
    assert!(lo > 0.3, "pulse must never blink the HUD out, got {lo}");
    assert!(hi <= 1.0, "pulse must stay within alpha range, got {hi}");
    assert!(hi - lo > 0.2, "Max glow must visibly breathe");
}

#[test]
fn test_autodetect_prefers_identified_agent_over_generic_process() {
    fn p(pid: u32, name: &str, agent_type: AgentType) -> DetectedProcess {
        DetectedProcess {
            pid,
            name: name.to_string(),
            cpu_usage: 1.0,
            memory_mb: 64.0,
            agent_type,
        }
    }

    let mut state = AppState::default();
    // sysinfo yields processes in hash order and the scan matches bare `node`/`python`.
    // A stray node process must not hijack the brand badge or the top of the list.
    state.update_detected_processes(vec![
        p(101, "node", AgentType::Custom),
        p(102, "ollama", AgentType::Ollama),
        p(103, "claude", AgentType::Anthropic),
    ]);

    assert_eq!(
        state.agent_type,
        AgentType::Ollama,
        "brand badge must lock onto a real agent"
    );
    assert_eq!(state.detected_processes[0].name, "ollama");
    assert_eq!(state.detected_processes[1].name, "claude");
    assert_eq!(
        state.detected_processes.last().unwrap().name,
        "node",
        "unidentified processes sink below the real agents"
    );
}

#[test]
fn test_thousands_separator() {
    assert_eq!(thousands(0), "0");
    assert_eq!(thousands(999), "999");
    assert_eq!(thousands(1000), "1,000");
    assert_eq!(thousands(74200), "74,200");
    assert_eq!(thousands(1000000), "1,000,000");
}

#[test]
fn test_app_state_detected_processes_update() {
    let mut state = AppState::default();
    assert!(state.detected_processes.is_empty());

    let procs = vec![
        DetectedProcess {
            pid: 101,
            name: "ollama".to_string(),
            cpu_usage: 5.0,
            memory_mb: 512.0,
            agent_type: AgentType::Ollama,
        }
    ];

    state.update_detected_processes(procs);
    assert_eq!(state.detected_processes.len(), 1);
    assert_eq!(state.detected_processes[0].name, "ollama");
    assert_eq!(state.agent_type, AgentType::Ollama);
}

#[test]
fn test_permission_request_queue_and_resolve() {
    let mut state = AppState::default();
    let req = PermissionRequest {
        request_id: "perm-101".to_string(),
        session_id: "claude-50-days".to_string(),
        agent_name: "Claude Code".to_string(),
        action_type: "file_edit".to_string(),
        details: "replace_file_content target=\"src/lib.rs\"".to_string(),
        timeout_seconds: 60,
    };

    state.add_permission_request(req.clone());
    assert_eq!(state.pending_permissions.len(), 1);
    assert_eq!(state.pending_permissions[0].request_id, "perm-101");

    let resolved = state.resolve_permission("perm-101", true);
    assert!(resolved);
    assert!(state.pending_permissions.is_empty());
}

#[test]
fn test_multi_session_tabs_and_selection() {
    let mut state = AppState::default();
    state.register_session("claude-1", AgentType::Anthropic, "Claude Code");
    state.register_session("gemini-1", AgentType::Gemini, "Antigravity");

    assert_eq!(state.sessions.len(), 3); // includes default session
    assert_eq!(state.active_session_id, "claude-default");

    state.select_session("gemini-1");
    assert_eq!(state.active_session_id, "gemini-1");
}


#[test]
fn test_session_launch_payload_deserialization() {
    let json_str = r#"{
        "agent_command": "claude",
        "working_directory": "/Users/tjlsmith0831/Desktop/Programming/50-days-of-dev",
        "initial_prompt": "Write unit tests for module X"
    }"#;

    let payload: Result<SessionLaunchPayload, _> = serde_json::from_str(json_str);
    assert!(payload.is_ok());

    let val = payload.unwrap();
    assert_eq!(val.agent_command, "claude");
    assert_eq!(val.working_directory, "/Users/tjlsmith0831/Desktop/Programming/50-days-of-dev");
    assert_eq!(val.initial_prompt, "Write unit tests for module X");
}

#[test]
fn test_parse_jsonl_line() {
    let jsonl_line = r#"{"type": "PLANNER_RESPONSE", "content": "Running ripgrep search for auth terms", "tokens": 12400}"#;
    let event = parse_jsonl_line(jsonl_line);
    assert!(event.is_some());
    let ev = event.unwrap();
    assert_eq!(ev.status, AgentStatus::ToolExecuting);
    assert_eq!(ev.step_description, "Running ripgrep search for auth terms");
    assert_eq!(ev.tokens_used, Some(12400));
}

#[test]
fn test_parse_jsonl_line_matches_real_claude_code_transcript_shape() {
    // Real ~/.claude/projects/**/*.jsonl lines nest text inside message.content[] blocks,
    // not at the top level — this is the shape the tailer must actually handle.
    let assistant_line = r#"{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Reading src/lib.rs to trace the bug"}]},"sessionId":"abc"}"#;
    let ev = parse_jsonl_line(assistant_line).expect("must parse a real assistant turn");
    assert_eq!(ev.status, AgentStatus::Thinking);
    assert_eq!(ev.step_description, "Reading src/lib.rs to trace the bug");

    let tool_line = r#"{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Bash","input":{"command":"cargo test"}}]}}"#;
    let ev = parse_jsonl_line(tool_line).expect("must parse a tool_use turn");
    assert_eq!(ev.status, AgentStatus::ToolExecuting);
    assert!(!ev.step_description.is_empty());
}


