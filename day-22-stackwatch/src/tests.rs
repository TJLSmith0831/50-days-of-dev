use super::*;

#[test]
fn test_default_state_is_genuinely_empty() {
    let state = AppState::default();
    assert_eq!(state.glow_setting, GlowSetting::Max);
    // No seeded demo session: cold start must be honest about nothing running.
    assert!(state.sessions.is_empty(), "cold start must seed no fake session");
    assert_eq!(state.active_session_id, None);
    assert!(!state.activity_seen);
    assert_eq!(state.header_view(), None, "empty state -> header paints nothing");
    assert_eq!(state.drawer_view(), None);
}

#[test]
fn test_event_only_agent_still_populates_the_header() {
    // `/event` agents never register a session — the HUD must still show them.
    let mut state = AppState::default();
    state.apply_event(AgentEvent {
        agent_type: Some(AgentType::OpenAi),
        status: AgentStatus::Thinking,
        step_description: "Planning".to_string(),
        tokens_used: Some(500),
        glow_setting: None,
    });
    let view = state.header_view().expect("event activity must reach the header");
    assert_eq!(view.agent_type, AgentType::OpenAi);
    assert_eq!(view.status, AgentStatus::Thinking);
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
        parent_pid: Some(1),
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
    let (w, h) = notch.hud_size(HudMode::Collapsed);
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
    let (cw, ch) = notch.hud_size(HudMode::Collapsed);
    let (ew, eh) = notch.hud_size(HudMode::Drawer);
    assert!(ew > cw && eh > ch, "expanding must widen and drop a drawer");
    assert!(ew <= notch.screen_width, "HUD must never exceed the display");
}

#[test]
fn test_terminal_mode_grows_to_a_readable_panel() {
    let notch = NotchGeometry {
        screen_width: 1512.0,
        notch_width: 200.0,
        notch_height: 32.0,
    };
    let (dw, dh) = notch.hud_size(HudMode::Drawer);
    let (tw, th) = notch.hud_size(HudMode::Terminal);
    assert!(tw > dw && th > dh, "a live TUI needs more room than the status drawer");
    // The drawer is ~420pt wide, about 45 monospace columns — Claude Code wraps its own
    // box-drawing at that width and reads as broken. This is the whole reason the third
    // window state exists.
    assert!(tw >= 800.0, "terminal panel must fit ~100 columns of monospace");
}

#[test]
fn test_no_hud_mode_overflows_a_small_display() {
    // An external 1280pt display, or a notch-less Mac — 900pt of terminal must clamp
    // rather than hang off the side of the screen.
    let small = NotchGeometry::fallback(1280.0);
    for mode in [HudMode::Collapsed, HudMode::Drawer, HudMode::Terminal] {
        let (w, _) = small.hud_size(mode);
        assert!(w <= small.screen_width, "{mode:?} overflows a 1280pt display");
        let (x, _) = small.dock_position(w);
        assert!(x >= 0.0, "{mode:?} docks off the left edge");
    }
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
            parent_pid: Some(1),
            name: name.to_string(),
            cpu_usage: 1.0,
            memory_mb: 64.0,
            agent_type,
        }
    }

    let mut state = AppState::default();
    // sysinfo yields processes in hash order, so the list reshuffled every scan tick and
    // the brand badge picked whoever hashed first. Sort is by pid: stable under the cursor.
    state.update_detected_processes(vec![
        p(103, "claude", AgentType::Anthropic),
        p(102, "ollama", AgentType::Ollama),
    ]);

    assert_eq!(
        state.agent_type,
        AgentType::Ollama,
        "brand badge must lock onto a real agent"
    );
    assert_eq!(state.detected_processes[0].name, "ollama");
    assert_eq!(state.detected_processes[1].name, "claude");
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
            parent_pid: Some(1),
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

    assert_eq!(state.sessions.len(), 2);
    assert_eq!(state.active_session_id.as_deref(), Some("claude-1"));

    state.select_session("gemini-1");
    assert_eq!(state.active_session_id.as_deref(), Some("gemini-1"));
}

#[test]
fn test_concurrent_sessions_do_not_clobber_each_other() {
    // The whole point of per-source tracking: two agents running at once must not
    // fight over one shared status.
    let mut state = AppState::default();
    let ev = |status: AgentStatus, step: &str| AgentEvent {
        agent_type: None,
        status,
        step_description: step.to_string(),
        tokens_used: None,
        glow_setting: None,
    };

    state.apply_session_event("/a.jsonl", AgentType::Anthropic, "Claude Code", ev(AgentStatus::Thinking, "reading lib.rs"));
    state.apply_session_event("/b.jsonl", AgentType::Gemini, "Antigravity", ev(AgentStatus::ToolExecuting, "running tests"));

    assert_eq!(state.sessions.len(), 2);
    assert_eq!(state.sessions["/a.jsonl"].status, AgentStatus::Thinking);
    assert_eq!(state.sessions["/b.jsonl"].status, AgentStatus::ToolExecuting);

    // Header follows the most recent update, not the selected tab.
    state.select_session("/a.jsonl");
    assert_eq!(state.header_view().unwrap().agent_type, AgentType::Gemini);
    assert_eq!(state.drawer_view().unwrap().step_description, "reading lib.rs");

    state.apply_session_event("/a.jsonl", AgentType::Anthropic, "Claude Code", ev(AgentStatus::Idle, "done"));
    assert_eq!(state.header_view().unwrap().agent_type, AgentType::Anthropic);
}

#[test]
fn test_failed_launch_marks_session_and_queues_a_prompt() {
    let mut state = AppState::default();
    state.register_session("s-1", AgentType::Anthropic, "claud");
    state.mark_session_failed("s-1", "No such file or directory (os error 2)");

    assert_eq!(state.sessions["s-1"].status, AgentStatus::Error);
    assert_eq!(state.pending_launch_failures.len(), 1);

    // "Later" clears the prompt but leaves the failed tab on record.
    state.dismiss_launch_failure("s-1");
    assert!(state.pending_launch_failures.is_empty());
    assert_eq!(state.sessions["s-1"].status, AgentStatus::Error);
}

#[test]
fn test_remove_session_fallback() {
    let mut state = AppState::default();
    state.register_session("s-1", AgentType::Anthropic, "Claude Code");
    state.register_session("s-2", AgentType::Gemini, "Antigravity");
    state.select_session("s-1");

    state.remove_session("s-1");
    assert_eq!(state.active_session_id.as_deref(), Some("s-2"), "falls back to a survivor");

    state.remove_session("s-2");
    assert_eq!(state.active_session_id, None, "last one killed -> genuinely no session");
    assert!(state.sessions.is_empty());
    assert_eq!(state.header_view(), None);
}

#[test]
fn test_known_clis_classify_to_their_brand() {
    // A CLI offered in the dropdown must colour its tab as the right brand, so every
    // known command has to survive the name classifier.
    for (cmd, expected) in [
        ("claude", AgentType::Anthropic),
        ("gemini", AgentType::Gemini),
        ("codex", AgentType::OpenAi),
        ("ollama", AgentType::Ollama),
    ] {
        assert_eq!(match_agent_type_from_name(cmd), expected, "{cmd} must classify to its brand");
        assert!(KNOWN_AGENT_CLIS.contains(&cmd), "{cmd} must be offered");
    }
    // Classification works off the full path too — that's what the launcher passes.
    assert_eq!(
        match_agent_type_from_name("/Users/x/.nvm/versions/node/v24.16.0/bin/claude"),
        AgentType::Anthropic
    );
}

#[test]
fn test_only_installed_clis_are_offered() {
    // Every returned path must be a real executable, and nothing outside the known list.
    for path in available_agent_clis() {
        assert!(path.is_absolute(), "launcher needs absolute paths to work from a .app");
        let name = path.file_name().unwrap().to_string_lossy().to_string();
        assert!(KNOWN_AGENT_CLIS.contains(&name.as_str()), "unexpected offer: {name}");
    }
}

#[test]
fn test_resolve_agent_command_leaves_paths_and_unknowns_alone() {
    assert_eq!(resolve_agent_command("/bin/ls"), "/bin/ls", "absolute paths pass through");
    assert_eq!(
        resolve_agent_command("definitely-not-a-real-binary"),
        "definitely-not-a-real-binary",
        "an unresolvable name still reaches spawn, so the failure surfaces normally"
    );
    // `ls` exists on every machine this runs on; resolution must produce a real path.
    let resolved = resolve_agent_command("ls");
    assert!(resolved.ends_with("/ls") && resolved.starts_with('/'), "got {resolved}");
}

#[test]
fn test_token_count_uses_whole_usage_block_not_one_field() {
    // The gauge looked stuck at a few hundred tokens because the old lookup grabbed
    // whichever token-ish key it hit first (per-message output_tokens), not the
    // session's actual context fill.
    let line = r#"{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"ok"}],
        "usage":{"input_tokens":4,"cache_creation_input_tokens":1200,"cache_read_input_tokens":86000,"output_tokens":250}}}"#;
    let ev = parse_jsonl_line(line).expect("must parse");
    assert_eq!(ev.tokens_used, Some(87_454), "context fill = input + cache + output");

    // Lines with no usage block still fall back to the old key search.
    let plain = r#"{"type":"PLANNER_RESPONSE","content":"searching","tokens":12400}"#;
    assert_eq!(parse_jsonl_line(plain).unwrap().tokens_used, Some(12400));
}

#[test]
fn test_only_known_agent_clis_are_detected() {
    // The bug this fixes: the scan matched the substrings `python` and `node`, so a stray
    // Python helper and CursorUIViewService appeared under LOCAL AGENTS — each with a Kill
    // button beside it. Matching is now exact on the binary name, case-insensitive.
    for name in [
        "claude", "Claude", "codex", "cursor-agent", "devin", "gemini", "ollama", "aider",
        "amp", "opencode", "goose", "copilot",
    ] {
        assert!(is_agent_cli(name), "{name} is a known agent CLI");
    }
    for name in [
        "python", "python3", "node", "CursorUIViewService", "Cursor Helper (Renderer)",
        "claude-helper", "nodejs", "Google Chrome", "ollama-runner", "",
    ] {
        assert!(!is_agent_cli(name), "{name} must not be listed as an agent");
    }
}

#[test]
fn test_agent_subprocesses_drop_but_independent_sessions_survive() {
    // `claude` forks workers that are themselves named `claude`. A child of a detected
    // agent is part of that agent, not a second one. But two *independent* top-level
    // `claude` processes are two real sessions — a herd manager that collapses them into
    // one row is lying about how many agents are running.
    fn p(pid: u32, parent_pid: u32, name: &str) -> DetectedProcess {
        DetectedProcess {
            pid,
            parent_pid: Some(parent_pid),
            name: name.to_string(),
            cpu_usage: 1.0,
            memory_mb: 64.0,
            agent_type: AgentType::Anthropic,
        }
    }
    let pids: Vec<u32> = top_level_agents(vec![
        p(100, 1, "claude"),   // session A, parented by launchd
        p(101, 100, "claude"), // A's forked worker -> drop
        p(102, 100, "claude"), // A's forked worker -> drop
        p(200, 1, "claude"),   // session B, independent -> keep
        p(201, 200, "claude"), // B's worker -> drop
    ])
    .iter()
    .map(|p| p.pid)
    .collect();
    assert_eq!(pids, vec![100, 200], "one row per session, not per forked worker");
}

#[test]
fn test_sibling_workers_of_one_launcher_collapse_to_one_row() {
    // Found by running it: Devin's app spawns two `devin` helpers under one parent that is
    // *not* itself on the allowlist, so parent-filtering can't tell they're one agent and
    // LOCAL AGENTS listed the same thing twice. Same name + same parent = same agent.
    // Two sessions started in two terminal tabs have different parents, so they survive.
    fn p(pid: u32, parent_pid: u32, name: &str) -> DetectedProcess {
        DetectedProcess {
            pid,
            parent_pid: Some(parent_pid),
            name: name.to_string(),
            cpu_usage: 1.0,
            memory_mb: 64.0,
            agent_type: AgentType::Custom,
        }
    }
    let pids: Vec<u32> = top_level_agents(vec![
        p(48819, 47682, "devin"), // Devin app's helper
        p(48842, 47682, "devin"), // ...and its twin -> collapse
        p(50000, 900, "claude"),  // a session in terminal tab A
        p(50001, 901, "claude"),  // a session in terminal tab B -> both survive
    ])
    .iter()
    .map(|p| p.pid)
    .collect();
    assert_eq!(pids, vec![48819, 50000, 50001]);
}

#[test]
fn test_context_window_is_per_agent() {
    let mut state = AppState::default();
    state.register_session("s", AgentType::Anthropic, "Claude Code");
    assert_eq!(state.sessions["s"].token_limit, 200_000, "Claude Code's real context window");
}

#[test]
fn test_source_of_derives_agent_from_file_location() {
    use std::path::Path;
    assert_eq!(source_of(Path::new("/Users/x/.claude/projects/foo/a.jsonl")), (AgentType::Anthropic, "Claude Code"));
    assert_eq!(source_of(Path::new("/Users/x/.gemini/brain/b.json")), (AgentType::Gemini, "Antigravity"));
    assert_eq!(source_of(Path::new("/Users/x/.cursor/logs/c.log")), (AgentType::Custom, "Cursor"));
    assert_eq!(source_of(Path::new("/Users/x/.aider/d.jsonl")), (AgentType::Custom, "Aider"));
}

#[test]
fn test_tailer_skips_history_and_reads_only_new_writes() {
    use std::io::Write;

    let path = std::env::temp_dir().join(format!("notch-tail-{}.jsonl", std::process::id()));
    let line = |t: &str| format!(r#"{{"type":"summary","content":"{t}"}}"#);
    std::fs::write(&path, format!("{}\n", line("old history"))).unwrap();

    let mut offsets = std::collections::HashMap::new();
    assert!(
        read_new_events(&mut offsets, &path).is_empty(),
        "pre-existing content must not replay into a session"
    );

    let mut f = std::fs::OpenOptions::new().append(true).open(&path).unwrap();
    // Trailing fragment: the agent is mid-write, so this line is not consumed yet.
    write!(f, "{}\n{{\"type\":\"summ", line("fresh")).unwrap();
    f.flush().unwrap();

    let events = read_new_events(&mut offsets, &path);
    assert_eq!(events.len(), 1);
    assert_eq!(events[0].step_description, "fresh");

    writeln!(f, "ary\",\"content\":\"completed\"}}").unwrap();
    f.flush().unwrap();
    let events = read_new_events(&mut offsets, &path);
    assert_eq!(events.len(), 1, "the half-written line resumes, it isn't lost");
    assert_eq!(events[0].step_description, "completed");

    std::fs::remove_file(&path).ok();
}


#[test]
fn test_session_launch_payload_deserialization() {
    // `initial_prompt` is gone — you type into the session's own terminal now. An older
    // caller still sending it must not start failing to launch, so the field is ignored
    // rather than rejected.
    let json_str = r#"{
        "agent_command": "claude",
        "working_directory": "/Users/tjlsmith0831/Desktop/Programming/50-days-of-dev",
        "initial_prompt": "Write unit tests for module X"
    }"#;

    let payload: Result<SessionLaunchPayload, _> = serde_json::from_str(json_str);
    assert!(payload.is_ok(), "a stale initial_prompt field must be ignored, not fatal");

    let val = payload.unwrap();
    assert_eq!(val.agent_command, "claude");
    assert_eq!(val.working_directory, "/Users/tjlsmith0831/Desktop/Programming/50-days-of-dev");
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


