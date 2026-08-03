## 1. Web search

Dropped in full per I5 — both executors have web search built in, so a
harness-side Browserbase integration would duplicate it. No `/search` command,
no HTTP client, no API key handling.

- [x] 1.1 ~~Browserbase HTTP client~~ — removed per I5
- [x] 1.2 ~~`/search <query>` command~~ — removed per I5
- [x] 1.3 ~~Citation-list formatting~~ — removed per I5
- [x] 1.4 ~~Citation-list injection~~ — removed per I5
- [x] 1.5 ~~HTTP error handling and backoff~~ — removed per I5
- [x] 1.6 ~~Mocked-HTTP unit tests~~ — removed per I5

## 2. Graphify integration

- [x] 2.1 Implement Graphify shell-out (`graphify extract <target> --out <out-dir> --no-viz --code-only`) with incremental/code-only/deep-mode toggle flags
- [x] 2.2 Implement `graph.json` and `GRAPH_REPORT.md` reading from the output directory after a successful run
- [x] 2.3 Implement the results pane: target-scope picker, run/re-run button, toggles, rendered report view, explorable graph view
- [x] 2.4 Implement the query surface (`graphify query`/`path`/`explain` invocations and result display)
- [x] 2.5 Implement report-summary injection: truncate `GRAPH_REPORT.md` to 4000 chars, append as a `role: "tool"` JSONL message with a pointer to the full results pane
- [x] 2.6 Implement failure handling: non-zero exit surfaces stderr in the results pane, no message injected
- [x] 2.7 `cargo test` unit tests: output-directory parsing, truncation boundary, failure path injects nothing — note: the "target must stay inside the active project" guard is *not* covered, since it sits in the `run_graphify` Tauri command; item 2 of `day-23-floo-network/FOLLOW-UPS.md`

## 3. Verification

- [x] 3.1 ~~`/search` walkthrough~~ — removed per I5
- [ ] 3.2 Manual walkthrough against a real Graphify install — **blocked per I6**: `graphify` is not installed on this machine and is not published under that name on pip or npm. The pane, the run/query commands, and the injection path are wired and unit-tested; a live run needs the real binary.
- [x] 3.3 ~~`/search` E2E~~ — removed per I5
- [x] 3.4 Graphify round trip driven through the app against a stubbed process (per C9 in change 1, since no real `graphify` exists here): pane populates from a fixture output directory, the summary is injected into the thread, and the failure path surfaces stderr while injecting nothing
- [x] 3.5 Confirm `openspec status` shows all tasks complete before archiving
