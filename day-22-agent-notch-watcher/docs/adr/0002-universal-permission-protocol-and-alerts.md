# 2. Universal Permission Protocol & Alert System

- Status: Accepted
- Date: 2026-08-02

## Context
The HUD lacked a mechanism to receive permission requests from agents, present interactive approvals, or alert the user when an agent is waiting for input. Additionally, support was limited to single mock agents rather than a universal suite of developer agents.

## Decision
1. **Hybrid Permission IPC Engine**: Expose a blocking HTTP/IPC approval endpoint (`127.0.0.1:8765/permission/request`) and CLI hook adapter so agents pause until approved/denied in the notch drawer.
2. **Multi-Channel Permission Alerts**: Trigger a native macOS notification, audio chime, and notch visual pulse (`GlowSetting::Max`) whenever an agent hits a permission checkpoint.
3. **Universal Agent Coverage**: Support signature matching and hook integrations for all major agent tools: Claude Code, Cursor, Antigravity/Gemini, Codex/OpenAI, Goose, Aider, Ollama, and OpenHands.

## Consequences
- Requires macOS notification permissions (`UserNotifications` framework or `notify-rust`).
- Agents block on local HTTP/socket response when waiting for user approval.
- Clean, unified permission UI across heterogeneous CLI and IDE agents.
