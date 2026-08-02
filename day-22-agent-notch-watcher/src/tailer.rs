use crate::{AgentEvent, AgentStatus, AgentType, SharedState};
use serde_json::Value;
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader, Seek, SeekFrom};
use std::path::PathBuf;
use std::time::Duration;

/// Depth-first search for the first string value at any of these keys.
/// Real agent transcripts (Claude Code's `message.content[].text`, etc.) nest the
/// interesting text several levels deep — a top-level-only lookup misses it entirely.
fn find_str<'a>(v: &'a Value, keys: &[&str]) -> Option<&'a str> {
    match v {
        Value::Object(map) => {
            for k in keys {
                if let Some(s) = map.get(*k).and_then(|x| x.as_str()) {
                    if !s.is_empty() {
                        return Some(s);
                    }
                }
            }
            map.values().find_map(|child| find_str(child, keys))
        }
        Value::Array(arr) => arr.iter().find_map(|child| find_str(child, keys)),
        _ => None,
    }
}

/// True if any nested object (at any depth) has `"type": <one of `wanted`>`.
/// Content blocks carry their own `type` field one or more levels below the line's
/// top-level `type` — e.g. `message.content[].type == "tool_use"`.
fn contains_type(v: &Value, wanted: &[&str]) -> bool {
    match v {
        Value::Object(map) => {
            if let Some(t) = map.get("type").and_then(|x| x.as_str()) {
                if wanted.contains(&t) {
                    return true;
                }
            }
            map.values().any(|child| contains_type(child, wanted))
        }
        Value::Array(arr) => arr.iter().any(|child| contains_type(child, wanted)),
        _ => false,
    }
}

fn find_u64(v: &Value, keys: &[&str]) -> Option<u64> {
    match v {
        Value::Object(map) => {
            for k in keys {
                if let Some(n) = map.get(*k).and_then(|x| x.as_u64()) {
                    return Some(n);
                }
            }
            map.values().find_map(|child| find_u64(child, keys))
        }
        Value::Array(arr) => arr.iter().find_map(|child| find_u64(child, keys)),
        _ => None,
    }
}

pub fn parse_jsonl_line(line: &str) -> Option<AgentEvent> {
    let v: Value = serde_json::from_str(line).ok()?;
    if !v.is_object() {
        return None;
    }

    // Top-level `type`/`role` decide status; Claude Code transcript lines carry
    // "user" | "assistant" | "summary" | "system" here, plus nested tool_use/tool_result
    // blocks inside `message.content[]` for actual tool activity.
    let top_type = v.get("type").and_then(|s| s.as_str()).unwrap_or("");
    let role = v
        .get("message")
        .and_then(|m| m.get("role"))
        .and_then(|s| s.as_str())
        .unwrap_or("");
    let has_tool_block = contains_type(&v, &["tool_use", "tool_result"]);

    let status = if let Some(st) = v.get("status").and_then(|s| s.as_str()) {
        match st.to_lowercase().as_str() {
            "thinking" => AgentStatus::Thinking,
            "toolexecuting" | "tool_executing" | "executing" => AgentStatus::ToolExecuting,
            "quotawarning" | "quota_warning" => AgentStatus::QuotaWarning,
            _ => AgentStatus::Idle,
        }
    } else if has_tool_block
        || top_type.to_uppercase().contains("TOOL")
        || top_type.to_uppercase().contains("PLANNER")
    {
        AgentStatus::ToolExecuting
    } else if role == "assistant" || top_type.to_uppercase().contains("THINK") {
        AgentStatus::Thinking
    } else if role == "user" || top_type == "summary" || top_type == "system" {
        AgentStatus::Idle
    } else {
        AgentStatus::Thinking
    };

    let step_description = v
        .get("step_description")
        .and_then(|s| s.as_str())
        .map(|s| s.to_string())
        .or_else(|| {
            find_str(&v, &["text", "content", "message", "description", "command", "name"])
                .map(|s| s.to_string())
        })?;

    let tokens_used = find_u64(&v, &["tokens_used", "tokens", "output_tokens", "input_tokens"]);

    let agent_type = if let Some(at) = v.get("agent_type").and_then(|s| s.as_str()) {
        match at.to_lowercase().as_str() {
            "anthropic" | "claude" => Some(AgentType::Anthropic),
            "gemini" | "antigravity" => Some(AgentType::Gemini),
            "openai" | "gpt" => Some(AgentType::OpenAi),
            "ollama" => Some(AgentType::Ollama),
            _ => Some(AgentType::Custom),
        }
    } else {
        None
    };

    Some(AgentEvent {
        agent_type,
        status,
        step_description,
        tokens_used,
        glow_setting: None,
    })
}

fn push_matching_files(dir: &PathBuf, paths: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else { return };
    for entry in entries.flatten() {
        let p = entry.path();
        if let Some(ext) = p.extension() {
            if ext == "jsonl" || ext == "log" || ext == "json" {
                paths.push(p);
            }
        }
    }
}

pub fn scan_log_directories() -> Vec<PathBuf> {
    let mut paths = Vec::new();
    let home = std::env::var("HOME").unwrap_or_default();
    if home.is_empty() {
        return paths;
    }

    // Real Claude Code sessions live one directory per project under `~/.claude/projects/`,
    // not flat in `~/.claude/transcripts` (that path never exists).
    let projects_dir = PathBuf::from(format!("{}/.claude/projects", home));
    if let Ok(entries) = std::fs::read_dir(&projects_dir) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() {
                push_matching_files(&p, &mut paths);
            }
        }
    }

    let flat_dirs = vec![
        format!("{}/.cursor/logs", home),
        format!("{}/.gemini/brain", home),
        format!("{}/.aider", home),
    ];
    for dir_str in flat_dirs {
        push_matching_files(&PathBuf::from(dir_str), &mut paths);
    }
    paths
}

pub async fn start_universal_tailer(shared_state: SharedState) {
    let mut file_offsets: HashMap<PathBuf, u64> = HashMap::new();

    loop {
        let files = scan_log_directories();
        for path in files {
            if let Ok(mut file) = File::open(&path) {
                let offset = file_offsets.entry(path.clone()).or_insert(0);
                if let Ok(metadata) = file.metadata() {
                    if metadata.len() > *offset {
                        if file.seek(SeekFrom::Start(*offset)).is_ok() {
                            let reader = BufReader::new(file);
                            let mut new_offset = *offset;
                            for line in reader.lines().flatten() {
                                new_offset += line.len() as u64 + 1;
                                if let Some(event) = parse_jsonl_line(&line) {
                                    if let Ok(mut state) = shared_state.lock() {
                                        state.apply_event(event);
                                    }
                                }
                            }
                            *file_offsets.get_mut(&path).unwrap() = new_offset;
                        }
                    }
                }
            }
        }
        tokio::time::sleep(Duration::from_millis(1500)).await;
    }
}
