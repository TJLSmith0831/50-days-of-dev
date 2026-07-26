# Agent Memory Recall — Demo Brief

**Hook:** Most "agent memory" demos are just a long chat. That's not memory — that's context. This demo seeds a fact, runs three unrelated fresh-session turns, and proves Mem0 retrieves the fact when a stateless baseline can't.

---

## What it proves

1. **Fresh-session failure is real.** Each turn is an independent Ollama `mistral` chat call with zero prior history. Ask "what's my favorite language?" with no context and the model has no way to know — it fails/hallucinates (0/3 pairs pass).
2. **Mem0 recovers the right fact across sessions.** The seed fact and all three filler turns are stored under an isolated `user_id`, then searched before the recall question. The retrieved memory is injected into the prompt; the model answers correctly (3/3 pairs pass).
3. **It's fully local.** Ollama `mistral` for the agent and Mem0's internal extraction, Ollama `nomic-embed-text` for embeddings, and a local Chroma vector store — no Mem0 Cloud, no API key.

---

## What is agent memory? (5–10s definition beat)

Agent memory means an agent persists information *between* separate sessions or invocations, not just within one long conversation. A plain context window only works while the chat is open; memory (here, Mem0 over a local vector store) lets a new, fresh session recall facts from earlier ones.

---

## Setup

```bash
cd day-15-agent-memory
uv sync
uv run main.py   # ~2 min, 3 pairs × 2 lanes
```

Requires `mistral:latest` and `nomic-embed-text:latest` pulled in Ollama (both are already present).

---

## Pre-recording workflow

**Step 1 — Test without recording.**

1. `uv run main.py` end to end.
2. Confirm the final report shows:
   - `No-Mem` column: `Fail` for all three pairs (`Totals 0`).
   - `Mem` column: `Pass` for all three pairs (`Totals 3`).
3. If any memory-backed pair fails — **stop and do not record.** That's a Mem0 extraction or retrieval issue; re-run once (Chroma is reset automatically) and check Ollama is responsive.

**Step 2 — Record the terminal demo.**

Once Step 1 passes cleanly on a dry run, start recording.

**Step 3 — Create the Remotion video.**

Composite the "stateless vs memory-backed" concept intro with the terminal recording.

---

## Demo scenario

Single terminal, full run:

```bash
uv run main.py
```

Let it run live. The sequence is: seed fact → three unrelated filler turns → recall question, repeated for three independent pairs, first with no memory then with Mem0. End held on the pass/fail report.

---

## Shot list (~50–60s)

1. **Intro — the concept (10–15s):** animated diagram — a "Fresh Session" box (no memory lane) shows each turn as an isolated speech bubble that disappears; a "Memory-Backed" box shows each turn dropping into a Mem0 + Chroma store, then the recall question pulling the right fact back out. Caption: *separate sessions. no shared context. unless you store it.*
2. **Demo — Pair 1, no-memory lane (8–10s):** the seed and three fillers run, then the recall question. Caption: *no memory — every turn is a fresh session.*
3. **Demo — Pair 1, memory-backed lane (8–10s):** same seed and fillers, but you can see Mem0 storing and retrieving; the recall answer contains "Rust". Caption: *Mem0 stores across sessions, then retrieves the right fact.*
4. **Demo — Pair 2 and 3, side-by-side rhythm (10–12s):** quick cuts showing the no-memory `Fail` and memory `Pass` rows for Kyoto and Pixel. Caption: *three isolated pairs. same pattern.*
5. **Demo — the report (8–10s):** hold on the final table, highlight the `No-Mem 0` and `Mem 3` totals. Caption: *stateless: 0/3. memory-backed: 3/3.*
6. **Demo — the stack (3–5s):** hold on the last frame with a small overlay: Ollama `mistral` + `nomic-embed-text` + Chroma, all local. Caption: *no API key. no cloud memory.*

---

## What NOT to demo

- **The filler-turn responses.** They're there to prove the memory lane has to find the seed among four stored items, but the actual content of "what is 7×8?" is not the story.
- **Mem0's internal extraction step.** It's interesting but invisible in a terminal run; don't invent a debug view.
- **Any Mem0 Cloud or `MemoryClient` usage.** The whole point is local-only; showing a cloud client would contradict the brief.
- **A continuous chat with history threaded through.** That would let the no-memory lane pass trivially and undermine the claim.
- **A run where the no-memory lane accidentally guesses the keyword.** If that happens, the seed/filler wording needs to be adjusted before recording.

---

## Frame

- Terminal fullscreen, dark theme. Set the font large enough that the report table is readable without zooming.
- The report table is the money shot — end held on it for 2s.
- The `Mem` answer for each pair should be visible long enough to read the keyword (`Rust`, `Kyoto`, `Pixel`).

---

## LinkedIn post draft

> Most "agent memory" demos are just a long conversation. That's not memory — that's a big context window.
>
> I built a recall test that seeds a fact, runs three unrelated fresh-session turns, then asks a question that needs the seed. The no-memory lane has zero prior context and fails every time. The Mem0-backed lane stores every turn locally and answers correctly.
>
> Result: 0/3 pass without memory, 3/3 pass with it.
>
> The whole thing runs local: Ollama `mistral` as the agent and Mem0's extraction model, `nomic-embed-text` for embeddings, and Chroma as the vector store. No API key, no Mem0 Cloud.
>
> Day 15 of 50 — agent memory. #AIEngineering #AgentMemory #LLMOps

---

## Checks before recording

1. `ollama list` shows `mistral:latest` and `nomic-embed-text:latest`.
2. `ollama serve` is running and responsive on the default port.
3. `uv run main.py` dry run ends with `Totals 0` under No-Mem and `Totals 3` under Mem.
4. No `MTLCompilerService` / Metal errors from Ollama — restart `ollama serve` if they appear.
5. Terminal width ≥ 100 columns so the report table doesn't wrap.
6. `chroma_db/` is gitignored and will be reset automatically at run start.
