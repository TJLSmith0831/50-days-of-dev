#!/usr/bin/env bash
# Claude Code PreToolUse hook for Agent Notch Watcher HUD.
# Claude Code pipes a JSON payload (tool_name, tool_input, session_id, ...) on stdin
# and reads the allow/deny decision from this script's stdout JSON + exit code —
# it does NOT pass action/details as $1/$2, so a positional-arg version never fires.
# Wire it up in .claude/settings.json:
#   "hooks": {"PreToolUse": [{"matcher": "Bash|Edit|Write", "hooks": [{"type": "command", "command": "hooks/claude-notch-hook.sh"}]}]}
set -euo pipefail

payload="$(cat)"
tool_name="$(echo "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_name","tool"))' 2>/dev/null || echo "tool")"
tool_input="$(echo "$payload" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin).get("tool_input",{})))' 2>/dev/null || echo "{}")"
session_id="$(echo "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id","claude"))' 2>/dev/null || echo "claude")"
req_id="perm-$RANDOM"

response="$(curl -s --max-time 65 -X POST http://127.0.0.1:8765/permission/request \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "import json,sys; print(json.dumps({
    'request_id': sys.argv[1], 'session_id': sys.argv[2], 'agent_name': 'Claude Code',
    'action_type': sys.argv[3], 'details': sys.argv[4], 'timeout_seconds': 60}))" \
    "$req_id" "$session_id" "$tool_name" "$tool_input")")" || true

if [ -z "$response" ]; then
  # HUD not running — fail open to Claude Code's own permission prompt rather than block.
  echo '{}'
  exit 0
elif echo "$response" | grep -q '"allowed":true'; then
  echo '{"decision": "approve"}'
  exit 0
else
  echo '{"decision": "block", "reason": "Denied via Agent Notch Watcher HUD"}'
  exit 0
fi
