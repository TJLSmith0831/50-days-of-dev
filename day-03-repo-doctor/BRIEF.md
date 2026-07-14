# Repo Doctor — Demo Brief

**Hook:** An AI agent that fixes a broken Python repo — and proves it stayed inside the lines.

## What it proves (the trust story)
Not "an agent fixed a bug." Three beats that make the fix *trustworthy*:
1. **Caged** — a guardrail denies a dangerous move (red line, live).
2. **Surgical** — the diff is one line; no business logic touched.
3. **Verified** — FIXED is re-proven by a subprocess *outside* the agent, so it can't fake green.

## Record-time setup
- Fixture must be broken: `sandbox/pyproject.toml` has **no** `emoji` dep, so `import sandbox` fails. (Currently it *declares* `emoji` — remove it before recording or the FIXED beat is empty.)
- (Optional) A second fixture that fails on a missing system binary, to show ENV-BLOCKED.
- `.env` holds a live `ANTHROPIC_API_KEY`. Never on screen. Keys are auto-redacted in output, but don't rely on it for the file itself.

## Behaviors that can appear on screen (know these before recording)
The run is **live**: a header rule, then each tool call streams as a colored line as it happens, then a spinner during external verify, then the frozen report.

- **Live tool stream:** `✓ Tool  ...` (green, allowed) / `✗ Tool  <deny reason>` (red, denied). Allowed **Bash** lines print the raw input dict, e.g. `✓ Bash  {'command': 'uv sync'}` — expected, not a bug.
- **Guardrail denial is NOT guaranteed** — it only shows if the agent *attempts* a blocked action (non-whitelisted tool, `rm`/`curl`/`sudo`, editing `uv.lock`/`.venv`/`.git`, a path outside the repo, shell metacharacters, unsafe `python -c`). Do a dry run first; if no red line appears, re-run or use the tempt-a-denial fixture.
- **Three verdicts, and where they come from:**
  - `FIXED` (green panel) — external install + smoke both exit 0. Overrides whatever the agent claimed.
  - `ENV-BLOCKED` (yellow) — agent judged it an environment/prereq problem, **or** the SDK/agent was unavailable (prints `Agent unavailable: ...`, e.g. missing key or `claude` CLI).
  - `GAVE-UP` (red) — not green within limits, or the agent claimed FIXED but external verify disagreed (the trust guard firing).
- **Non-Python target:** prints "Repo Doctor currently supports Python repositories only; deferring without changes." and exits — no panels. Don't point it at a JS folder on camera.
- **Bad input:** missing path / not a directory / invalid `--smoke` override → one stderr line, no report.
- **Limits:** stops at 10 turns / $1.50 budget → `GAVE-UP` if not green by then.
- **Exit code:** 0 only on FIXED, else 1.

## Final report (the freeze frame)
Verdict panel → **Attempt log** table (per-turn tool/input/result, red rows for denials) → **Changes** (syntax-highlighted diff) → **Verified commands** table (`✓ pass` / `✗ fail`). Hold on this.

## Shot list (~45–60s)
1. **Cold open (5s):** `uv run --project . python main.py ./sandbox` on the broken repo. Header rule appears.
2. **Diagnose (10s):** live `✓ Bash uv sync` → `✓ Bash ... import sandbox` fails with `ModuleNotFoundError: emoji`. Caption: *classifies wiring vs env*.
3. **Guardrail denial (10s) — money shot:** a red `✗` line as the hook denies a blocked action. Caption: *tools, paths, and shell are whitelisted*.
4. **Fix (10s):** agent adds `emoji`, reinstalls, reruns smoke → passes (live green lines).
5. **Verify + report (15s):** "Verifying green outside the agent…" spinner, then the frozen report: **FIXED**, 1-line diff, `✓ pass` rows. Caption: *green is re-proven outside the agent*.
6. **(Optional) ENV-BLOCKED (10s):** run on the system-binary fixture → agent refuses to install, yellow verdict + remediation. Caption: *knows when not to act*.

## Frame
- Terminal only, dark theme, large font. No IDE chrome.
- Let the live stream and Rich panels breathe — they *are* the UI.
- End on the verdict panel held for 2s.

## Checks referenced
- `PYTHONPATH=. uv run pytest tests/test_main.py -q` (guardrail unit tests, 5 pass)
- `uv run --project . python sdk_smoke.py` (SDK connectivity)
