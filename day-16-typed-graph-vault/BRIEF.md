# Typed Graph Vault — Demo Brief / Handoff Doc

**Hook:** Flat RAG finds notes that *sound like* the question. Graph traversal finds the chain of decisions that actually answer it — and proves the answer came from the right notes.

---

## What graph engineering is (20–30s research beat)

Graph engineering went viral as a term, but underneath the hype is a real retrieval idea: **follow typed relationships instead of similarity scores**.

- **The primitive is simple.** Nodes are things you know about (a person, a project, a decision, an incident). Edges are the connections between them. That is the whole idea.
- **Why it matters for AI.** Agents have three ways to find knowledge: keyword search, vector search, or graph traversal. Keyword fails when the answer uses different words. Vector search fails when the answer is spread across several notes that, individually, are not similar to the question. Graph traversal is the only one that can follow a reasoning chain.
- **The example that breaks vector search.** "Why did we drop Redis for the job queue?" Vector search returns ten notes that mention Redis. The actual answer lives across three notes: the component, the decision that governs it, and the incident that motivated the earlier decision. A graph follows `decided_by` → `supersedes` → `caused_by` and reaches the answer in three hops.
- **Typed edges are the difference.** An untyped edge says "these two notes are related" — one bit. A typed edge says *how* they are related: `supersedes`, `depends_on`, `decided_by`, `caused_by`. Without types the chain survives but the meaning is gone; the agent has to re-read every note and guess the direction.
- **GraphRAG is the umbrella.** Microsoft GraphRAG extracts entities and relationships with an LLM at index time, builds community summaries, and answers by map-reducing over them. It works but is brutally expensive. LazyGraphRAG flips the design: build a cheap structural graph at index time and do the expensive reasoning at query time. HippoRAG 2 fuses graph structure with embeddings and wins on multi-hop benchmarks. The trend line: lazy indexing, agentic traversal, small controlled edge vocabularies, and honest routing — use the graph only for questions that need it.
- **The scoreboard.** Graphs win multi-hop reasoning (53.4% vs 42.9% vector RAG on GraphRAG-Bench), temporal reasoning (graph-based Mem0 scores 58.1 vs OpenAI memory at 21.7), and corpus-wide synthesis. They lose simple fact lookup and can be expensive. Practitioner consensus: route by question type — vector for lookups, graph for chains.
- **The math that kills graph projects.** Entity resolution. At 95% per-hop accuracy a 5-hop chain is 77% trustworthy; at 85% it is 44%. The expensive part of graph engineering is not graph algorithms — it is deciding what is the same thing. Human-curated links solve that by construction.

**Sources:**

- Louis Bouchard, *Graph Engineering Explained: What Actually Changed*: <https://www.louisbouchard.ai/graph-engineering-explained/>
- The AI Operator, *What Is Graph Engineering? A Field Guide for Builders*: <https://theaioperator.io/p/what-is-graph-engineering-a-field>
- Web search findings: GRAG/GraphRAG, SubgraphRAG, HippoRAG 2, LazyGraphRAG.

---

## What this build proves

1. **Human-curated typed edges beat extraction.** `graph.yaml` defines the allowed relation vocabulary; each Markdown note declares its outgoing typed links. No LLM extraction, no entity-resolution errors, no compounding per-hop uncertainty.
2. **The vault is the source of truth and is validated.** Invalid frontmatter, duplicate IDs, unknown relations, or missing targets block querying until fixed. The system refuses to silently drop bad data.
3. **Grounded answers are deterministic.** The planner (Qwen3:14b) sees only the graph's shape: node IDs, kinds, each node's outgoing typed links, and the relation vocabulary. It never sees a note body. It returns a constrained traversal plan. Python executes the plan. Only then are the reached note bodies sent to Mistral for a cited answer. If the plan is invalid or the path is empty, the REPL says `No grounded graph path found.` and never falls back to world knowledge.
4. **A standalone HTML/SVG visualizer proves the evidence path.** `graph` renders the full graph plus the latest traversal path as a self-contained `graph.html` and opens it in the default browser.

---

## Setup

```bash
cd day-16-typed-graph-vault
uv sync
uv run main.py --self-check
```

For live `ask` questions:

```bash
ollama list   # must include qwen3:14b and mistral:latest
uv run main.py
```

Both models are already present on this machine.

---

## Pre-recording workflow

**Step 1 — Test without recording.**

1. `uv run pytest` — 16 tests should pass.
2. `uv run main.py --self-check` — must print `self-check OK`.
3. `uv run main.py` and run the full demo sequence below. Confirm:
   - `ask Why did we replace the Redis job queue?` returns a Mistral answer citing the reached notes and prints the typed path.
   - `graph` writes `day-16-typed-graph-vault/graph.html` and opens it.
   - `show adr-007-postgres-queue` prints the note body and links.
   - `reload` and `quit` work cleanly.
4. If `ask` returns `No grounded graph path found.` consistently, stop and diagnose (Ollama not running, model missing, planner producing invalid JSON).

**Step 2 — Record the VHS tape.**

Once Step 1 passes, record the terminal demo into `demo.gif` using the included tape or the auto generator.

**Step 3 — Capture the rendered graph.**

With the latest traversal path highlighted, take a screenshot of `graph.html` and save it as `graph-screenshot.png`.

---

## Demo scenario

Single terminal, REPL session:

```bash
uv run main.py
```

At the `graph>` prompt, type:

```text
ask Why did we replace the Redis job queue?
graph
show adr-007-postgres-queue
reload
quit
```

Expected beats:

- Startup prints the vault loaded and the command help.
- `ask` prints a grounded answer with inline note citations and the path: `job-queue -> adr-007-postgres-queue -> adr-003-redis-queue -> incident-2026-03-11`.
- `graph` prints the written `graph.html` path and opens the browser.
- `show` prints the selected note body and its typed outgoing links.
- `reload` re-reads the vault and reports the node count.
- `quit` exits cleanly.

---

## VHS tape / REPL recording

**Output file:** `day-16-typed-graph-vault/demo.gif`

Use the `cli-demo-generator` skill or write a `.tape` file in the day folder. Recommended tape outline:

```tape
Output demo.gif
Set FontSize 20
Set Width 1200
Set Height 700
Set Theme Dracula
Set TypingSpeed 50ms

Type "cd day-16-typed-graph-vault"
Enter
Sleep 500ms

Type "uv run main.py --self-check"
Enter
Sleep 2s

Type "uv run main.py"
Enter
Sleep 2s

Type "ask Why did we replace the Redis job queue?"
Enter
Sleep 15s

Type "graph"
Enter
Sleep 3s

Type "show adr-007-postgres-queue"
Enter
Sleep 2s

Type "reload"
Enter
Sleep 2s

Type "quit"
Enter
Sleep 1s
```

**Critical notes for the tape:**

- The `ask` command is the money shot — it is the only place both models run. Give it enough time (10–15s) for Qwen3 to plan and Mistral to synthesize.
- `graph` opens a browser off-screen; that is fine. The terminal should print the path to `graph.html`.
- The startup line `Loaded 4 notes from example-vault` should be visible.
- Keep terminal width ≥ 100 columns so path output does not wrap.
- Dark theme is preferred.

---

## HTML visualizer screenshot

**Output file:** `day-16-typed-graph-vault/graph-screenshot.png`

After running `graph` in the REPL, the generated `graph.html` opens in the default browser. Capture the browser window showing:

- The full graph with four nodes: `job-queue`, `adr-007-postgres-queue`, `adr-003-redis-queue`, `incident-2026-03-11`.
- Directional arrows and relation labels: `decided_by`, `supersedes`, `caused_by`.
- The latest traversal path highlighted in the accent color (orange/red stroke by default).
- The standalone, no-dependency page layout.

If the browser does not open automatically, open `graph.html` manually from the project root.

---

## Shot list (~50–70s)

### Research / concept intro (15–20s)

1. **The three retrieval methods (5s):** keyword, vector, graph. Show the Redis question and why vector search returns ten unrelated Redis notes. Caption: *vector search finds notes that sound like the question; graphs find notes connected to the answer.*
2. **Typed edges (5s):** same graph with untyped vs typed edges. Caption: *an untyped edge is one bit; a typed edge carries the relationship.*
3. **GraphRAG landscape (5–10s):** Microsoft GraphRAG vs LazyGraphRAG vs HippoRAG 2. Caption: *expensive extraction is giving way to cheap structure + smart traversal.*

### Terminal demo (35–50s)

1. **Self-check (3s):** `uv run main.py --self-check` → `self-check OK`. Caption: *validated typed graph, no Ollama needed.*
2. **REPL startup (3s):** `uv run main.py` → `Loaded 4 notes from example-vault`. Caption: *Markdown vault loaded as a typed graph.*
3. **Grounded question (20s):** type `ask Why did we replace the Redis job queue?`. Show the planner response, the traversal path, and Mistral's cited answer. Caption: *planner picks the path; traversal retrieves the notes; answer cites only what was reached.*
4. **Graph visualizer (10s):** type `graph`, show the browser with `graph.html` and the highlighted path. Caption: *same graph, latest evidence path highlighted.*
5. **Note inspection and reload (5s):** `show adr-007-postgres-queue` and `reload`. Caption: *inspect any node, reload the vault live.*
6. **Exit (2s):** `quit`. Caption: *clean exit.*

---

## What NOT to demo

- **A question the example vault cannot ground.** If you ask something not covered by the typed relations, the REPL correctly declines with `No grounded graph path found.` That is a good test but a bad demo unless the point is explicitly to show the guardrail.
- **Editing the vault on camera without showing validation.** If you demo `reload` after breaking the vault, show the error messages. Otherwise the validation story is invisible.
- **A fully local, no-model demo only.** `uv run main.py --self-check` proves the graph; `ask` proves the grounded-answer pipeline. The demo needs both.
- **`graph.html` as raw source.** Show the rendered browser, not the minified HTML string.

---

## Frame

- Terminal fullscreen, dark theme, font size ≥ 16pt.
- 1200×700 or larger canvas for the terminal GIF; 120 columns minimum.
- For the graph screenshot, capture the full browser window at 100% zoom so the SVG labels are crisp.
- Hold on the `ask` answer and the path line long enough to read the note IDs.
- End the terminal recording on `quit` or on the `graph.html` browser shot.

---

## LinkedIn post draft

> Flat RAG finds notes that sound like your question. Graph traversal finds the notes connected to your answer.
>
> Built a typed graph vault from Markdown + YAML. `graph.yaml` defines the allowed relations; each note declares typed links in frontmatter. The REPL plans a deterministic traversal with Qwen3, executes it in Python, then asks Mistral to synthesize a grounded answer from only the reached notes.
>
> Ask "Why did we replace the Redis job queue?" and the path is the proof: `job-queue -> adr-007-postgres-queue -> adr-003-redis-queue -> incident-2026-03-11`. No world-knowledge fallback. No hidden hallucination. `graph` renders the same path in a standalone HTML/SVG visualizer.
>
> Day 16 of 50 — graph engineering, not graph hype. #AIEngineering #GraphRAG #KnowledgeGraphs #LLMOps

---

## Checks before recording / handoff

1. `uv run pytest` — 16 tests pass.
2. `uv run main.py --self-check` — prints `self-check OK`.
3. `ollama list` shows `qwen3:14b` and `mistral:latest`.
4. `uv run main.py` dry run — `ask` produces a grounded answer with path; `graph` opens `graph.html`; `show`, `reload`, and `quit` work.
5. `graph.html` rendered in browser shows four nodes and the highlighted traversal path.
6. VHS tape saved as `demo.gif` and screenshot saved as `graph-screenshot.png`.
7. BRIEF.md, `demo.gif`, and `graph-screenshot.png` are staged for the final handoff.
