# day-23-floo-network-integrations — Decision Log

Change 3 of 4 (per D14, amended): Graphify + Browserbase only — notes UX
(originally also slated here) was fully absorbed into change 1's own
`note-taking` capability during its grill-propose pass. Depends on change 1
(project/thread/session model) and change 2 (a live executor to inject
context into) both existing.

Full cross-cutting decision history: `openspec/explore/day-23-floo-network.md` (D1–D17).

## Carried forward from the shared log

- **D1** — unrelated to the 7 stale specs; no reference to them.
- **D8** — Graphify CLI shape: `graphify extract <project-dir> --out <out-dir> --no-viz --code-only` for safe key-less runs; primary artifact is `graph.json` (NetworkX node-link) + `GRAPH_REPORT.md` on disk, not stdout; recommended UI control surface (target-scope picker, run/re-run + incremental/code-only/deep-mode toggles, results view, query surface) already detailed in ticket 07.
- **D9** — Browserbase: `POST /v1/search {query, numResults}` with `x-bb-api-key` header from `.env`; response is link+title+metadata only, no synthesized answer, no official Rust SDK (raw REST call); citation-only forwarding rule (never raw HTML or answers).
- **D15** — testing tiers apply: unit tests for request/response parsing and citation formatting, no live network calls in automated tests (mock the HTTP layer).
- **D17** — distribution/packaging is a non-goal.

## I1: How do Browserbase search results reach the executor's context?
- **Decision**: A `/search <query>` slash command, usable in either mode. The harness calls Browserbase directly (no executor tool-loop involvement — consistent with D6's constraint that the harness can't hook into the executor's own loop), formats the numbered `[n]` citation list per D9, and appends it to the thread as a `role: "tool"` message (D4 schema) — which becomes part of what's sent to the executor on the next turn, the same mechanism already used for `/go` and `/propose`.
- **Why**: Reuses an existing, proven pattern (harness-injected messages via the normal conversation stream) rather than requiring a new MCP-tool integration path for the executor to call Browserbase directly.
- **Source**: recommended-accepted

## I2: Is Graphify's output ever injected into the executor's context?
- **Decision**: Yes — after each successful Graphify run, the harness automatically appends a `role: "tool"` message containing a truncated `GRAPH_REPORT.md` summary (first 4000 characters, with a note that the full report is available in the results pane) to the active thread.
- **Why**: Keeps the executor automatically aware of the codebase map without requiring the user to manually paste report content into chat; the 4000-character bound keeps a single run from dominating the thread's context while still being useful (the full report/graph remains browsable in the results pane per ticket 07's UI surface).
- **Source**: user

## I3: What new capabilities does this change introduce?
- **Decision**: Two — `graphify-integration` (shell-out CLI invocation, results pane per ticket 07's control surface, auto-injected report summary per I2) and `web-search` (Browserbase `/v1/search` call, `/search` command, citation-list injection per I1).
- **Why**: Matches the two genuinely independent integrations this change covers — no shared code path between shelling out to a local CLI tool and making a REST call to an external API.
- **Source**: recommended-accepted

## I4: What order do the task groups build in, and what's riskiest to front-load?
- **Decision**: 1) `web-search` first (simpler: one REST endpoint, well-documented response shape, no local binary dependency) — `/search` command, citation formatting, injection as a `role: "tool"` message. 2) `graphify-integration` second (riskier: shells out to an external CLI whose full flag surface wasn't exhaustively verified per D8's open note, output parsing depends on files on disk rather than a typed API response) — run/re-run, results pane, report-summary injection.
- **Why**: Browserbase's REST shape is fully verified and simple; Graphify's shell-out surface has more unknowns (unverified flags, disk-based output), so proving the injection-as-`role:"tool"`-message pattern against the simpler integration first de-risks reusing it for Graphify.
- **Source**: recommended-accepted

## I5: Web search is dropped from this change entirely
- **Decision**: No Browserbase integration, no `/search` command, no citation-list formatting, no `BROWSERBASE_API_KEY` handling. The `web-search` capability and its spec are removed from this change; D9 and I1 no longer apply. This change is Graphify only.
- **Why**: Both executors ship with web search built in, so a harness-side integration would duplicate a tool the executor already reaches for on its own — and would do it worse, since the harness can only inject citations as text on the *next* turn while the executor can search mid-turn and act on what it finds. It also removes an HTTP client, a secret to manage, and a rate-limit/backoff path from the harness for no capability gained.
- **Source**: user

## I6: Graphify ships implemented but unverified
- **Decision**: The shell-out, argument construction, output parsing, truncation, and failure handling are implemented and unit-tested, but have never run against a real `graphify`. A `ponytail:` comment on `run_graphify` records this.
- **Why**: `graphify` is not installed on this machine and is not published under that name on pip or npm; the npm package of that name is an unrelated project, so installing it to "verify" would prove nothing and add a supply-chain risk. D8 already flagged the flag surface as not exhaustively verified. Claiming a live run works would be a claim not run — the honest position is that the code matches D8's documented shape and the disk-parsing/failure paths are covered by tests using stand-in processes.
- **Source**: recommended-accepted

## I7: `graph.json` renders as a force-directed graph with a filterable community legend
- **Decision**: The results pane draws `graph.json` as a canvas force-directed layout (`d3-force`) with a communities sidebar — colour swatch, name, node count, per-community checkboxes and select-all — plus hover labels, drag-to-pan, scroll-to-zoom and double-click-to-fit. Node radius scales with degree; edges are tinted by their source community; a weak per-community centroid force makes the clusters legible. Filtering hides marks without re-running the layout, so surviving nodes never move under the reader.
- **Why**: The `graphify-integration` spec already required "an explorable, filterable graph"; the first pass only rendered node/edge counts, which did not meet it. The user supplied Graphify's own screenshot as the target. `d3-force` is the one added dependency — a hand-rolled force simulation is exactly the kind of clever code that is unpleasant to debug later, and canvas (not SVG) is what keeps several hundred nodes smooth.
- **Source**: user

## I8: Communities beyond the eighth fold into a neutral "Other"
- **Decision**: The eight documented categorical hues are assigned in fixed order to the eight largest communities; every remaining community renders in one neutral grey "Other" entry that still appears in the legend with its combined count. Colour follows the entity — the ranking is computed once over the whole graph, so filtering never repaints the survivors.
- **Why**: A node-link graph is an all-pairs form (any two communities can land adjacent), and the validated palette only clears the colour-blind separation floor at four hues — running the validator over all eight all-pairs fails hard (worst pair ΔE 1.6 deutan). Eight is already generous; generating a ninth hue is never correct. Identity is therefore carried by the legend, the hover label and the filter, with colour as a grouping cue only. Raised with the user explicitly against the alternative of ~16 hues matching the reference screenshot more literally; they chose to keep 8 + Other, accepting that on a repo with many small directories a majority of nodes can render grey.
- **Source**: user

## I9: Verification used a real import-graph extractor, not fabricated data
- **Decision**: The stand-in `graphify` used to verify the pane parses real `import`/`use`/`mod` statements out of this monorepo's actual source files, producing real nodes (files), real edges (imports) and real communities (directories). It is a scratchpad tool and is not committed.
- **Why**: The first stand-in emitted synthetic data copied from Graphify's marketing screenshot (FastAPI community names), which made the pane look right while proving nothing about it. The user called this out. A verification fixture that invents its data can't tell you the renderer is correct — parsing the real repo showed genuine structure (`lib.rs` importing all three modules, `App.tsx` importing `EventView.tsx`) and is what the screenshots now show.
- **Source**: user

## Open items for this change (to grill)

- Verify `graphify_args` and the run/query flow against a real `graphify` install (per I6).
