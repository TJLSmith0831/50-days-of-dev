# Armadillo CLI — Ship Day Brief

**Hook:** A local-first CLI agent that learns your codebase before writing a line of code — four-phase design methodology (DDD → BDD → SDD → TDD), OKF knowledge graphs, and frontier model handoff.

> **Repo:** `~/../armadillo-cli` (separate repository, pushed independently)
> **Day:** 7 — Ship Day (Week 1 portfolio-grade build)
> **Status:** This folder is a pointer; all code lives in the armadillo-cli repo.

---

## What it proves (the trust story)

Not "an agent wrote code." Four beats that make the output _trustworthy_:

1.  **Interrogated (DDD)** — the agent grills you for domain understanding, one question at a time with recommended answers, before proceeding.
2.  **Grounded (BDD)** — it explores ideal behaviors using the domain concepts from DDD, producing OKF documents in `.armadillo/behaviors/`.
3.  **Specified (SDD)** — it breaks down requirements into actionable tasks with clear acceptance criteria, linked to behaviors via OKF markdown links.
4.  **Verified (TDD)** — it writes failing tests first, implements to pass, then refactors — optionally handing off to Claude Code for the implementation phase.

Each phase produces OKF documents (markdown + YAML frontmatter) in `.armadillo/`, creating a navigable knowledge graph that persists across sessions.

**Demo scenario:** "Add a logging system to the CLI." This gives the agent enough domain surface to grill meaningfully — log levels, output destinations, formats, error handling — without being so broad that the four-phase flow runs too long for a 70-90s demo.

---

## Why this approach works

Most AI coding assistants:
- Jump straight to implementation without understanding the problem space
- Start fresh each session, forgetting previous understanding
- Send code and context to cloud servers without user control
- Get tied to specific cloud providers and their ecosystems
- Have no structured methodology

Armadillo CLI addresses this at the intersection of three frustrations:

- **Persistent context, not amnesia**: Every AI assistant I'd used started fresh each session, forgetting everything it learned about my codebase. OKF knowledge graphs in `.armadillo/` persist that understanding as markdown — human-readable, git-friendly, and loaded back into context on the next session.
- **Privacy and data ownership**: I didn't want my code and project context sent to cloud servers without control. Local-first means the primary copy lives on my device — Ollama handles planning locally, frontier models are consulted for implementation only, and session state stays in SQLite at `~/.armadillo/sessions.db`.
- **Structured methodology, not jump-to-code**: AI assistants jump straight to implementation without understanding the problem space. The four-phase methodology (DDD → BDD → SDD → TDD) enforces understanding first — the agent grills you for domain knowledge, explores behaviors, breaks down specs, and only then writes code. Adaptive flow lets it skip phases when it already has sufficient knowledge.

Model routing ties it together: local models (Ollama, <14B) handle the planning and grilling where privacy and cost matter; frontier models (Claude Code) handle implementation where quality matters. Dynamic tool generation via `.armadillo/tools.yaml` lets the agent adapt to project-specific needs without hardcoding.

---

## Record-time setup

*   **Fresh demo directory**: create a clean directory for the demo (e.g., `mkdir ~/demo-logging && cd ~/demo-logging`). Run armadillo-cli from there so the demo shows the tool working on a fresh project, not dogfooding itself. The `.armadillo/` directory and OKF knowledge graph are created from scratch on screen.
*   **Ollama running** with both models pulled: `llama3.2:3b` (quick tasks, ~3s) and `qwen3:14b` (design-phase grilling, ~11s). Warm both with `ollama run <model>` once before recording — cold start adds real seconds.
*   **Model routing demo**: the demo shows the router in action — `llama3.2:3b` for quick tool calls, `qwen3:14b` for DDD/BDD/SDD grilling, Claude Code for TDD handoff. This is the full three-tier model story.
*   **`~/.armadillo/sessions.db`** accumulates real runs. Use `--fresh` flag or delete the file before recording so the demo doesn't imply prior fake history.
*   **ANTHROPIC_API_KEY** in `.env` for Claude Code handoff. Never on screen. If you don't have a key, `/handoff` falls back to manual instructions — still a valid demo beat.
*   **Demo feature request**: "Add a logging system to the CLI" — scoped enough for a 70-90s demo, rich enough for all four phases to produce meaningful OKF documents.
*   **Ardo mascot**: displays on first session load. iTerm2 renders `assets/ardo.png` inline via OSC 1337; all other terminals get ASCII fallback.

---

## Recording workflow

**The agent is non-deterministic.** Do not expect the exact questions, answers, or OKF content to match this document word-for-word. The shot list below is a guide, not a script.

**Recommended flow:**

1.  `cd ~/demo-logging` and start the REPL with `uv run --project ~/../armadillo-cli main.py --fresh` off-camera (runs armadillo-cli against the fresh demo directory; router handles per-phase model selection)
2.  Begin recording once the REPL is active and Ardo is displayed
3.  Type your demo input in a typewriter style — character-by-character visible typing, not pasted text
4.  Watch what the agent actually does
5.  Write captions based on the real behavior, not the expected behavior
6.  Only re-record if something is obviously failing (Ollama down, model missing, tool errors)

**Adapt the shot list:**

*   If the model asks 2 questions instead of 4, that's fine — the grilling still happened.
*   If it skips a phase (adaptive flow), that's fine — show that the agent recognized sufficient knowledge.
*   If the handoff succeeds but looks different than described, that's fine — the integration worked.
*   Only re-record if the flow breaks (no grilling, no OKF generation, handoff fails).

<!-- TODO: Record any deviations from this workflow you encounter. -->

---

## Behaviors that can appear on screen (know these before recording)

Fully local (for the REPL), fully live — tokens stream as they're generated, Rich panels render incrementally.

*   **Ardo mascot display**: Ardo the Armadillo appears on first session load. iTerm2 shows the PNG inline; other terminals get ASCII art. Warm, friendly first impression.
*   **Streaming token display**: the model's response appears character-by-character in the Rich panel, not all at once. This is the live feel — don't cut early.
*   **Four-phase methodology (DDD → BDD → SDD → TDD)**: the agent follows the methodology enforced via system prompt. It grills for domain understanding (DDD), explores behaviors (BDD), breaks down into tasks (SDD), then writes tests + implements (TDD). Each phase produces OKF documents.
*   **OKF document generation**: the agent creates markdown files with YAML frontmatter in `.armadillo/domain/`, `.armadillo/behaviors/`, `.armadillo/specs/`, `.armadillo/tests/`. These are the knowledge graph — human-readable, git-friendly.
*   **Adaptive phase skipping**: if the agent has sufficient knowledge (from existing OKF or codebase context), it can skip phases. It confirms with the user before skipping.
*   **Five core tools**: Read, Write, Edit, Bash, and dynamic tool generation. Write/Edit/Bash to `.armadillo/` are auto-approved; writes to project dirs require manual approval.
*   **Dynamic tool generation**: if the agent needs a capability not in the toolset, it generates a new tool definition, validates it, and adds it to `.armadillo/tools.yaml`. Generated tools execute through bash, so the dangerous-command blocklist and approval prompts apply automatically.
*   **@file mentions expand to absolute paths**: type `@main.py` and the harness resolves to the full path before tool calls.
*   **Slash commands**: `/help` shows commands, `/save` persists the session, `/sessions` lists available sessions, `/exit` quits cleanly, `/handoff` hands off to Claude Code.
*   **Model routing**: local models handle planning (DDD/BDD/SDD grilling); frontier models handle implementation (TDD). The `/handoff` command triggers Claude Code headless execution.
*   **Sandbox approval gates**: writes to `.armadillo/` are auto-approved; writes to project directories prompt for approval. Dangerous bash commands are blocked or require explicit confirmation.
*   **Session persistence**: SQLite at `~/.armadillo/sessions.db`. Sessions survive process crashes. `--thread-id <id>` resumes; `--fresh` starts clean.
*   **Context truncation**: when history exceeds ~24000 tokens (chars/4 estimation), oldest messages are dropped. System message always kept.
*   **Claude Code handoff modes**: `/handoff` defaults to `acceptEdits` (file writes flow; Bash still prompts). Configurable to `bypassPermissions` via `models.handoff_permission_mode` in config.yaml — completes the full red-green cycle. Show the confirmation if you use bypass mode.
*   **Ollama down**: the preflight check fails with a clear error message if Ollama isn't running. Verify Ollama is warm before recording.
*   **Missing model**: if the specified model isn't pulled, the harness falls back. Both work, but use the intended model for the demo.

<!-- TODO: Record any unexpected behaviors you observe during dry runs. -->

---

## What NOT to demo

*   **All four phases in one take.** The full DDD → BDD → SDD → TDD flow can go deep. If the model asks more than 3-4 questions per phase, cut and restart with a more specific initial request. The demo shows all four phases, but keep each phase tight — 1-2 questions max per phase to fit the 70-90s window.
*   **Dynamic tool generation unless it's clean.** The generation loop can have sampling variance with smaller models. Only show it if you've verified it works end-to-end in a dry run.
*   **Claude Code handoff without a key.** The fallback to manual instructions is fine, but less visually compelling. If you have a key, use it.
*   **@file mention on a non-existent file.** The harness will still expand to the absolute path, but the tool call will fail. Avoid this on camera.

<!-- TODO: Record additional "don't demo" items based on your dry runs. -->

---

## Shot list (~90–120s)

All four phases shown in depth, with model routing visible. Adjust timings after dry runs.

1.  **Overview (10-15s):** Animated diagram showing the four-phase flow with model routing. User → qwen3:14b (DDD grilling) → OKF knowledge graph → BDD → SDD → Claude Code handoff (TDD). Caption: _local model for understanding, frontier model for implementation_.
2.  **Cold open (5s):** REPL active, Ardo displayed. Caption: _local-first, ready to learn_.
3.  **DDD grilling (15s):** qwen3:14b asks domain questions about logging — levels, outputs, formats — one at a time with recommended answers. Caption: _one question at a time, with a recommendation_.
4.  **OKF generation (10s):** model writes `DomainConcept` OKF documents to `.armadillo/domain/`. Caption: _knowledge graph, persisted as markdown_.
5.  **BDD behaviors (10s):** model explores ideal behaviors — what should be logged, when, error handling. Writes `Behavior` OKF docs to `.armadillo/behaviors/`. Caption: _behaviors grounded in domain concepts_.
6.  **SDD spec breakdown (10s):** model breaks down into tasks with acceptance criteria. Writes `SpecTask` OKF docs to `.armadillo/specs/`. Caption: _design tree resolves before any code_.
7.  **TDD / handoff (15s):** `/handoff` → Claude Code headless executes the red-green-refactor cycle. Caption: _implementation by the frontier model_.
8.  **Session persistence (5s):** `/sessions` lists the saved session. Caption: _sessions persist automatically_.
9.  **Clean exit (5s):** `/exit` → "Goodbye."

<!-- TODO: Adjust timings and captions after dry runs. The agent is non-deterministic — these are targets, not a script. -->

---

## Frame

*   **Terminal only, dark theme, color enabled.** No IDE chrome. Let the Rich panels, Ardo mascot, and streaming tokens be the visual.
*   **Font size: 16pt minimum.** The streaming tokens and Rich panels must be legible at 1080p. Anything smaller becomes unreadable when compressed for web.
*   **Window size: 120 columns x 40 rows minimum.** Ensures tool outputs and multi-line OKF documents don't wrap awkwardly. Wider is better — 140 columns is ideal.
*   **Record at 2x or 3x zoom.** The terminal itself should occupy most of the frame.
*   **Avoid motion blur.** Ensure capture frame rate is 30fps minimum so streaming tokens don't smear.
*   **Hold on panels.** When a Rich panel or OKF document finishes rendering, hold for 1-2s before cutting. Let the viewer read the content.
*   **End on "Goodbye." held for 1-2s.** Clean exit, no stack trace.

---

## Checks referenced

*   `uv run main.py --self-check` (preflight: Ollama connection, model availability, dependencies)
*   `uv run pytest` (full test suite — 23 test files covering all 20 specs)
*   `uv run pytest --cov=./` (test suite with coverage)

---

## Ship Day DoD checklist

- [ ] One-command run verified from a clean clone (`uv sync && uv run main.py`)
- [ ] Demo GIF/screenshot of the measurable result
- [ ] Real README (armadillo-cli repo has one)
- [ ] Pinned/reproducible deps (`pyproject.toml` + `uv.lock`)
- [ ] LinkedIn post _is_ the artifact

<!-- TODO: Check these off as you complete each item. -->
