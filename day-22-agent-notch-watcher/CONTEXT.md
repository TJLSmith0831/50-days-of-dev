# Context — Agent Notch Watcher

## Ubiquitous Language & Terms

### Active Session
A live, ongoing execution sequence of an AI agent (e.g., Claude Code, Antigravity, Cursor, Codex, Goose, Aider, Ollama), tracked by the watcher through real-time transcript telemetry or direct IPC hooks.

### Session Launcher
An interactive launcher inside the notch drawer that lets users pick an agent binary (e.g., Claude Code, Antigravity, Ollama) and a target workspace folder to spawn a new agent session directly from the HUD.

### Universal JSONL Tailer
A lightweight background tailer that monitors active log and transcript files (`*.jsonl`, `*.log`, `transcript*.json`) across standard session directories (`~/.claude/`, `~/.cursor/`, `.gemini/`, `.aider/`) to extract status, token usage, and tool activity generically.

### Agent Hook Binding
An active communication channel (`POST /event` and `POST /permission/request` on `127.0.0.1:8765`) used by agent runtimes, CLI wrappers, or Claude Code hooks to push real-time events and blocking permission prompts.

### Session Tab
A header tab in the expanded notch drawer representing an active or attached agent session, displaying its agent badge, workspace name, status dot, and token telemetry.

### Interactive Permission Prompt
An urgent actionable card rendered inside the notch drawer when an agent pauses to request approval for a sensitive operation (e.g., file write, shell command, tool execution), containing direct **Approve** and **Deny** controls.

### Permission Alert Notification
A high-priority alert system triggering a macOS native system notification, sound chime, and auto-expanding glowing notch animation whenever an agent requires user approval.
