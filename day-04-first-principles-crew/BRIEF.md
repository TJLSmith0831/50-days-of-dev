# First-Principles Crew — Demo Brief

## The Problem

Most strategic decisions fail because they rest on unexamined assumptions. We say "should we do X?" without asking "what must be true for X to work?" — then we're surprised when the invisible premises collapse.

**Hook:** This tool forces those assumptions into the light before you commit. Three local agents strip a messy decision down to its irreducible truths — then let you interrogate any one of them, live.

## Why this approach works

Not "an agent gave advice." Three beats that make the recommendation _defensible_:

1.  **Challenged** — the Skeptic flags every shaky assumption baked into the problem, not just the obvious one.
2.  **Reduced** — the Physicist keeps only what survives scrutiny; the Builder's recommendation is traceable back to those fundamentals ("Rests on:").
3.  **Interrogable** — `drill <fundamental>` re-runs just the Physicist against one claim and forces it to defend or revise it, live, on camera.

## Why not just ask an LLM?

A single LLM gives you a confident answer — but it bakes the assumptions into its reasoning without making them visible. This crew separates the work: one agent finds the holes, one distills what's solid, one builds on that foundation. You see the premises before you see the conclusion.

## Real-world use case

You're a CTO deciding whether to migrate to microservices. The obvious answer is "yes, everyone's doing it" — but that answer rests on invisible assumptions: that your team can handle distributed systems complexity, that the performance bottleneck is actually monolith architecture, that you have the operational maturity to run 20 services instead of 1. This tool forces those assumptions into the open before you bet the company on them.

## Record-time setup

*   Ollama running with `llama3.2` pulled, reachable at `http://localhost:11434` (`ollama run llama3.2` once to warm it — cold start adds real seconds to the first panel).
*   `decisions.md` is `.gitignore`d and accumulates real runs — clear or ignore it before recording so the demo doesn't imply prior fake history.
*   Pick a problem with an obviously shaky premise (the built-in default works: "Should we rebuild our legacy monolith as microservices?") so the Skeptic's `?` flags read as genuinely useful, not filler.

## Behaviors that can appear on screen (know these before recording)

Fully local, fully live — every agent's output streams as its own colored panel as it finishes, not all at once at the end.

*   **Colored panels, one per voice:** Skeptic = red, Physicist = yellow, Builder = green, Problem/Help/metric = cyan. Color is the at-a-glance cue for whose turn it is — don't record in a theme that mutes ANSI color.
*   **Metric line is the payoff, not decoration:** "M assumptions challenged → N fundamentals → 1 recommendation in T s (local llama3.2)." Parsed from the structured output, not string-scraped — hold on this line a beat.
*   `**drill <n or text>**` — accepts a fundamental's number _or_ a substring of its wording (e.g. `drill legacy`). A substring matching more than one fundamental prints an "Ambiguous match" listing instead of guessing; no match prints "No fundamental matches". Only the Physicist re-runs — no new Skeptic/Builder panels for a drill.
*   `**help**` — prints the command panel again without re-running the crew (instant, no LLM call — useful if you fumble a command live).
*   **Free-text follow-up** — anything not matching a command re-runs the _full_ crew with your text appended as a "Follow-up:" to the original problem. Slower than `drill`; don't do this by accident on camera when you meant `drill`.
*   **Ctrl-D / Ctrl-C exit cleanly** — prints "Goodbye." and exits 0. No stack trace. Safe to use as the closing beat instead of typing `exit`.
*   **Ollama down** — crew run or drill fails, prints a red "Ollama isn't responding. Start it with `ollama serve`..." instead of a raw traceback. Verify Ollama is warm before recording so this never appears on screen.
*   **Structured-output parse failure** (rare on llama3.2) — prints "Structured output parsing failed; showing raw result." and the raw text. If it happens mid-recording, just re-run the same problem.

## What NOT to demo

*   **Tab-completion.** It was tried and pulled: macOS's stdlib `readline` is actually libedit, and its Tab-triggered redisplay hit a genuine, hard-to-reproduce infinite redraw loop (confirmed via a live stack trace pinned at ~100% CPU) rather than a bug in the completer logic. Don't type Tab expecting anything — it's a no-op now, not a feature.

## Shot list (~45–60s)

1.  **Cold open (5s):** `uv run main.py`, hit Enter to accept the default problem. Header rule + Problem panel appear. Caption: _the question we're actually trying to answer_.
2.  **Skeptic (10s):** red panel, assumptions flagged with `?`. Caption: _what we quietly assumed without realizing it_.
3.  **Physicist → Builder (10s):** yellow panel of fundamentals, then green recommendation with "Rests on:" traceable to specific fundamentals. Caption: _the answer, built only on what survived scrutiny_.
4.  **Metric line (3s):** hold on "M assumptions challenged → N fundamentals → 1 recommendation in T s (local llama3.2)." Caption: _we didn't just get an answer — we got a defensible one_.
5.  **Drill — money shot (15s):** `drill <a distinctive word from one fundamental>` → single yellow Physicist panel re-litigating just that claim, live. Caption: _challenge any premise, not just the conclusion_.
6.  **Clean exit (5s):** Ctrl-D → "Goodbye."

## Frame

*   Terminal only, dark theme with color enabled, large font. No IDE chrome.
*   Let each panel land on its own beat — don't cut before the Builder panel finishes rendering.
*   End on "Goodbye." held for 1–2s.

## Checks referenced

*   `uv run main.py --demo` (offline self-check: `metric_line` and `format_decision`, no LLM call)