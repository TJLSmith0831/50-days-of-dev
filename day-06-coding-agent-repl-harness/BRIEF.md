# Coding Agent REPL Harness — Demo Brief

**Hook:** A terminal REPL that grills you for requirements before drafting a spec — then hands off to Claude Code for implementation.

## What it proves (the trust story)

Not "an agent wrote code." Three beats that make the spec _trustworthy_:

1.  **Interrogated** — the model interviews you one question at a time, recommending an answer for each, before drafting anything.
2.  **Grounded** — it explores the codebase (via Read/Glob/Grep) before asking when possible, so questions aren't hypothetical.
3.  **Handed off** — once the spec is settled, `/handoff` hands off to Claude Code headless for implementation via opsx:apply.

## Why this approach works

Most AI coding assistants jump straight to implementation without understanding the problem space. This harness enforces Spec Driven Design (SDD): research (local model) + spec planning (grilling) + implementation (Claude Code). The grilling is baked into the system prompt — the model can't skip it. You see the design tree resolve before any code is written.

## Record-time setup

*   Ollama running with `qwen3:14b` pulled (`ollama serve` + `ollama pull qwen3:14b`). Warm it with `ollama run qwen3:14b` once before recording — cold start adds real seconds to the first response.
*   `~/.coding-agent-harness/sessions.db` accumulates real runs. Use `--fresh` flag or delete the file before recording so the demo doesn't imply prior fake history.
*   (Optional) ANTHROPIC\_API\_KEY in `.env` for Claude Code handoff. Never on screen. If you don't have a key, the `/handoff` command will fall back to manual instructions — still a valid demo beat.
*   Pick a concrete, scoped feature request (e.g., "add a --verbose flag to the CLI") so the grilling feels purposeful, not generic.

## Recording workflow

**The agent is non-deterministic.** Do not expect the exact questions, answers, or spec content to match this document word-for-word. The shot list below is a guide, not a script.

**Recommended flow:**

1.  Start the REPL with `uv run main.py --model qwen3:14b --fresh` off-camera
2.  Begin recording once the REPL is active and the welcome message is displayed
3.  Type your demo input in a typewriter style — character-by-character visible typing, not pasted text
4.  Watch what the agent actually does
5.  Write captions based on the real behavior, not the expected behavior
6.  Only re-record if something is obviously failing (Ollama down, model missing, tool errors)

**Adapt the shot list:**

*   If the model asks 2 questions instead of 3, that's fine — the grilling still happened.
*   If the spec is shorter or longer than expected, that's fine — the content matters more than length.
*   If the handoff succeeds but looks different than described, that's fine — the integration worked.
*   Only re-record if the flow breaks (no grilling, no spec draft, handoff fails).

## Behaviors that can appear on screen (know these before recording)

Fully local (for the REPL), fully live — tokens stream as they're generated, Rich panels render incrementally.

*   **Streaming token display:** the model's response appears character-by-character in the Rich panel, not all at once at the end. This is the live feel — don't cut early.
*   **Grilling is the default flow:** the model will ask questions one at a time, each with a recommended answer. It won't draft a spec until the design tree is resolved. If you answer vaguely, it will drill in.
*   **@file mentions expand to absolute paths:** type `@main.py` and the harness resolves to the full path before tool calls. This is a convenience feature — show it once.
*   **Slash commands:** `/help` shows commands, `/save` persists the session, `/sessions` lists available sessions, `/exit` quits cleanly, `/handoff` hands off to Claude Code.
*   **Context truncation:** when history exceeds ~24000 tokens, oldest messages are dropped (system message always kept). You won't see this on screen unless you run a very long session.
*   **Claude Code handoff modes:** `/handoff` defaults to `acceptEdits` (file writes flow; Bash still prompts). `/handoff yolo` opts into `bypassPermissions` for that single call — prompts for confirmation first. Show the confirmation prompt if you use `yolo`.
*   **Ollama down:** the preflight check fails with a clear error message if Ollama isn't running. Verify Ollama is warm before recording so this never appears on screen.
*   **Missing model:** if `qwen3:14b` isn't pulled, the harness falls back to `llama3.2`. Both work, but `qwen3:14b` is the intended model.

## What NOT to demo

*   **Multi-turn spec refinement in one take.** The grilling can go deep. If the model asks more than 3-4 questions, it's better to cut and restart with a more specific initial request.
*   **Claude Code handoff without a key.** The fallback to manual instructions is fine, but it's less visually compelling than the actual handoff. If you have a key, use it.
*   **@file mention on a non-existent file.** The harness will still expand to the absolute path, but the tool call will fail. Avoid this on camera.

## Shot list (~70–90s)

1.  **Harness overview (10-15s):** Animated diagram showing the SDD workflow. Simple boxes and arrows: User (blue) → Local Model (green, qwen3:14b) → Grilling → Spec Draft → Claude Code Handoff (yellow). Animation plays once, then fades out as terminal demo begins. Caption: _local model for grilling, Claude Code for implementation_.
2.  **Cold open (5s):** REPL is already active with welcome message displayed. Caption: _local model, ready to grill_.
3.  **First question (10s):** model asks the first question with a recommended answer. Caption: _one question at a time, with a recommendation_.
4.  **Codebase exploration (10s):** model uses Read/Glob/Grep to explore the codebase before asking the next question. Caption: _grounded in the actual codebase_.
5.  **Grilling resolves (15s):** 2-3 more questions, each with a recommended answer. Caption: _the design tree resolves before any spec is drafted_.
6.  **Spec draft (10s):** model drafts the spec in a Rich panel. Caption: _the spec, built only on what survived questioning_.
7.  **Handoff (15s):** `/handoff` → Claude Code headless runs opsx:apply. Caption: _implementation handled by Claude Code_.
8.  **Session persistence (5s):** `/sessions` lists the saved session. Caption: _sessions persist automatically_.
9.  **Clean exit (5s):** `/exit` → "Goodbye."

## Frame

*   **Terminal only, dark theme, color enabled.** No IDE chrome. Let the Rich panels and streaming tokens be the visual.
*   **Font size: 16pt minimum.** The streaming tokens and Rich panels must be legible at 1080p. Anything smaller becomes unreadable when compressed for web.
*   **Window size: 120 columns x 40 rows minimum.** This ensures tool outputs and multi-line responses don't wrap awkwardly. Wider is better — 140 columns is ideal if screen space allows.
*   **Record at 2x or 3x zoom.** The terminal itself should occupy most of the frame. Don't record a tiny terminal window surrounded by empty desktop space.
*   **Avoid motion blur.** If recording a live terminal, ensure the capture frame rate is high enough (30fps minimum) so the streaming tokens don't smear.
*   **Hold on panels.** When a Rich panel finishes rendering, hold for 1-2s before cutting. Let the viewer read the content.
*   **End on "Goodbye." held for 1-2s.** Clean exit, no stack trace.

## Checks referenced

*   `uv run main.py --self-check` (preflight: Ollama connection, model availability, dependencies)
*   `uv run python test_harness.py` (offline smoke checks: tools, agent graph, REPL helpers, sessions, truncation, handoff)
*   `uv run python test_harness.py --with-llm --with-web` (live checks: Ollama + DuckDuckGo)