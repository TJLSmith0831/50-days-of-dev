# Typed Graph Vault Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local-first REPL that validates a Markdown vault as a typed knowledge graph, answers natural-language questions with a Mistral-planned deterministic traversal, and visualizes the graph plus latest evidence path in standalone HTML.

**Architecture:** Markdown notes and a vault-local `graph.yaml` are the source of truth. A pure Python parsing/validation layer constructs an in-memory directed graph; it rejects an invalid vault rather than silently dropping data. The REPL sends only schema/node metadata to Ollama for a constrained traversal plan, executes that plan in Python, then sends only reached notes to Mistral for a cited answer. A no-dependency HTML/SVG renderer receives the same graph and optional path.

**Tech Stack:** Python 3.13, uv, `ollama` Python client, PyYAML, Pydantic, pytest, `mistral:latest` through local Ollama, standalone HTML/SVG.

---

## Repository context

- The root workspace automatically registers `day-*` packages, and a new Python day must declare `[tool.uv] package = false`.
- Day 15 already uses Ollama and `mistral:latest`; use its `OLLAMA_HOST` convention but do not reuse its data or implementation.
- Each day is self-contained. The tracker already reserves Day 16 for Graph engineering.
- This project must be usable without an API key. Do not create or read `.env` files.
- The tracked `example-vault/` makes a fresh clone demonstrable. The untracked `vault/` is the user's private source of truth and takes precedence when present.

## Domain contract

### Vault

A **vault** is a directory containing `graph.yaml` and Markdown notes. `graph.yaml` is required and contains a configurable vocabulary of directed relation types, each with a name and human-readable description. A note is a Markdown file with YAML frontmatter containing a unique `id`, a `kind`, and zero or more `links`. Each link has a `relation` and `target` note ID.

### Graph

A **node** is one valid note. A **typed edge** is a directed link from the declaring note to its target. Traversal can move `outbound` or `inbound`; every output path retains the actual edge direction and relation type.

### Grounded answer

A **grounded answer** is a Mistral response generated only after deterministic traversal and from the bodies of the reached notes. A planner may choose only known node IDs, configured relation types, and `inbound`/`outbound` directions. Invalid/malformed plans or empty results produce `No grounded graph path found`; the REPL never falls back to model world knowledge.

## Example-vault contract

Create a small architecture-decision corpus that makes causal traversal inspectable:

- `job-queue` component links via `decided_by` to `adr-007-postgres-queue`.
- `adr-007-postgres-queue` links via `supersedes` to `adr-003-redis-queue` and via `caused_by` to `incident-2026-03-11`.
- Add `redis-queue`, `postgres-queue`, `adr-012-retry-policy`, and `incident-2026-04-02` to make incoming and outgoing relationship queries meaningful.
- `graph.yaml` defines `decided_by`, `supersedes`, `caused_by`, and `depends_on`, including descriptions that the planner can use.

## Task 1: Scaffold the self-contained Python day

**Files:**
- Create: `day-16-typed-graph-vault/pyproject.toml`
- Create: `day-16-typed-graph-vault/.gitignore`
- Create: `day-16-typed-graph-vault/main.py`
- Create: `day-16-typed-graph-vault/src/__init__.py`
- Create: `day-16-typed-graph-vault/tests/conftest.py`
- Create: `day-16-typed-graph-vault/tests/test_repl.py`

**Step 1: Write the failing REPL startup/vault-selection tests**

```python
def test_select_vault_prefers_private_vault(tmp_path: Path) -> None:
    (tmp_path / "example-vault").mkdir()
    (tmp_path / "vault").mkdir()

    assert select_vault(tmp_path) == tmp_path / "vault"


def test_select_vault_falls_back_to_example_vault(tmp_path: Path) -> None:
    (tmp_path / "example-vault").mkdir()

    assert select_vault(tmp_path) == tmp_path / "example-vault"
```

**Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_repl.py -v`

Expected: FAIL because `select_vault` and the package do not exist.

**Step 3: Add project metadata and the minimal entrypoint**

- Require Python `>=3.13,<3.14`.
- Add runtime dependencies: `ollama`, `pydantic`, `pyyaml`.
- Add `[tool.uv] package = false`.
- Ignore `vault/` and generated `graph.html` only; track `example-vault/`.
- Implement `select_vault(project_root)` in `src/repl.py`; raise a clear error if neither location exists.
- Make `main.py` call the REPL runner rather than containing business logic.

**Step 4: Run the focused test**

Run: `uv run --with pytest pytest tests/test_repl.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add day-16-typed-graph-vault
git commit -m "feat: scaffold typed graph vault"
```

## Task 2: Define graph models and vault parsing

**Files:**
- Create: `day-16-typed-graph-vault/src/models.py`
- Create: `day-16-typed-graph-vault/src/vault.py`
- Create: `day-16-typed-graph-vault/tests/test_vault.py`

**Step 1: Write failing parsing tests**

```python
def test_load_vault_builds_nodes_and_typed_edges(vault_dir: Path) -> None:
    graph = load_vault(vault_dir)

    assert graph.nodes["job-queue"].kind == "component"
    assert graph.edges == [
        Edge(source="job-queue", relation="decided_by", target="adr-007", direction="outbound")
    ]


def test_load_vault_reads_relation_descriptions(vault_dir: Path) -> None:
    graph = load_vault(vault_dir)

    assert graph.relations["decided_by"] == "governed by a decision record"
```

**Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_vault.py -v`

Expected: FAIL because graph models and `load_vault` do not exist.

**Step 3: Implement the smallest parser**

- Model `RelationSchema`, `Link`, `Node`, `Edge`, and `Graph` with Pydantic dataclasses/models.
- Parse required `graph.yaml` with `yaml.safe_load`.
- Parse every `*.md` note's first YAML frontmatter block using `yaml.safe_load`; retain the remaining Markdown body unchanged.
- Preserve a deterministic file/name order for nodes and links so output and tests are stable.
- Build a directed `Edge` for each declared link. Do not infer edges from Markdown prose.

**Step 4: Run the focused tests**

Run: `uv run --with pytest pytest tests/test_vault.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add day-16-typed-graph-vault/src day-16-typed-graph-vault/tests
git commit -m "feat: parse typed markdown vaults"
```

## Task 3: Enforce full-vault validation

**Files:**
- Modify: `day-16-typed-graph-vault/src/vault.py`
- Modify: `day-16-typed-graph-vault/tests/test_vault.py`

**Step 1: Write failing validation tests**

```python
@pytest.mark.parametrize(
    ("fixture_name", "expected_message"),
    [
        ("duplicate-id", "duplicate node id: job-queue"),
        ("unknown-relation", "unknown relation: replaces"),
        ("missing-target", "unknown link target: missing-note"),
        ("malformed-frontmatter", "invalid frontmatter"),
    ],
)
def test_load_vault_collects_validation_errors(
    fixture_name: str, expected_message: str, fixture_root: Path
) -> None:
    with pytest.raises(VaultValidationError) as error:
        load_vault(fixture_root / fixture_name)

    assert expected_message in error.value.messages
```

**Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_vault.py -v`

Expected: FAIL because invalid vaults are accepted or only the first failure is reported.

**Step 3: Implement complete validation**

- Collect all parse/schema/duplicate/relation/target errors before raising `VaultValidationError`.
- Require a non-empty `id` and `kind` for each note.
- Verify every link relation exists in `graph.yaml` and every target is a known note ID.
- Expose error messages as an ordered list for deterministic tests and REPL output.
- Do not return a partial `Graph` from `load_vault`.

**Step 4: Run the focused tests**

Run: `uv run --with pytest pytest tests/test_vault.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add day-16-typed-graph-vault/src/vault.py day-16-typed-graph-vault/tests/test_vault.py
git commit -m "feat: block invalid graph vaults"
```

## Task 4: Implement deterministic bidirectional traversal

**Files:**
- Create: `day-16-typed-graph-vault/src/traversal.py`
- Create: `day-16-typed-graph-vault/tests/test_traversal.py`

**Step 1: Write failing traversal tests**

```python
def test_traverse_follows_requested_outbound_relations(graph: Graph) -> None:
    result = traverse(
        graph,
        TraversalPlan(start_nodes=["job-queue"], relations=["decided_by", "supersedes"], direction="outbound"),
    )

    assert [node.id for node in result.nodes] == ["job-queue", "adr-007-postgres-queue", "adr-003-redis-queue"]
    assert [edge.relation for edge in result.path] == ["decided_by", "supersedes"]


def test_traverse_supports_inbound_edges(graph: Graph) -> None:
    result = traverse(
        graph,
        TraversalPlan(start_nodes=["adr-007-postgres-queue"], relations=["decided_by"], direction="inbound"),
    )

    assert [node.id for node in result.nodes] == ["adr-007-postgres-queue", "job-queue"]
```

**Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_traversal.py -v`

Expected: FAIL because `traverse` does not exist.

**Step 3: Implement traversal**

- Define `TraversalPlan` with known `start_nodes`, an ordered non-empty relation list, and `inbound` or `outbound` direction.
- Validate plan values against the loaded graph before traversal.
- At each relation step, follow matching edges in the requested direction.
- Preserve ordered, de-duplicated nodes and actual source/relation/target edge details in `TraversalResult`.
- Return an empty result only after a valid plan cannot reach any next node; do not silently change relation order or direction.

**Step 4: Run the focused tests**

Run: `uv run --with pytest pytest tests/test_traversal.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add day-16-typed-graph-vault/src/traversal.py day-16-typed-graph-vault/tests/test_traversal.py
git commit -m "feat: traverse typed graph paths"
```

## Task 5: Add Mistral planning and grounded synthesis boundaries

**Files:**
- Create: `day-16-typed-graph-vault/src/llm.py`
- Create: `day-16-typed-graph-vault/tests/test_llm.py`
- Modify: `day-16-typed-graph-vault/src/models.py`

**Step 1: Write failing tests with a fake Ollama client**

```python
def test_plan_question_accepts_only_known_graph_values(graph: Graph) -> None:
    client = FakeClient('{"start_nodes":["job-queue"],"relations":["decided_by"],"direction":"outbound"}')

    assert plan_question(client, "Why was Redis dropped?", graph).start_nodes == ["job-queue"]


def test_plan_question_rejects_unknown_model_values(graph: Graph) -> None:
    client = FakeClient('{"start_nodes":["imaginary"],"relations":["made_up"],"direction":"sideways"}')

    assert plan_question(client, "Anything", graph) is None


def test_answer_receives_only_traversed_note_content(graph: Graph, result: TraversalResult) -> None:
    client = CapturingFakeClient("Redis was replaced after the incident. [adr-007-postgres-queue]")

    answer = synthesize_answer(client, "Why was Redis dropped?", result)

    assert "incident-2026-04-02" not in client.last_prompt
    assert answer.text.startswith("Redis was replaced")
```

**Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_llm.py -v`

Expected: FAIL because LLM boundary functions do not exist.

**Step 3: Implement the LLM adapter**

- Default model name is exactly `mistral:latest`; default host is `OLLAMA_HOST` or `http://localhost:11434`.
- Use Ollama's structured JSON response mode when available; otherwise parse a strict JSON response and reject invalid content.
- Give the planner only: question text, known node IDs/titles/kinds, relation names/descriptions, and valid directions. Do not send note bodies.
- Validate returned JSON with `TraversalPlan` and graph membership. Return `None` for malformed, unknown, or unsupported plans.
- Give the synthesizer only: the question, ordered traversal path, IDs/titles, and bodies of reached nodes. Require inline note-ID citations and tell it to decline if the evidence is insufficient.
- Keep all client calls behind injectable functions/classes so tests never require Ollama.

**Step 4: Run the focused tests**

Run: `uv run --with pytest pytest tests/test_llm.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add day-16-typed-graph-vault/src/llm.py day-16-typed-graph-vault/src/models.py day-16-typed-graph-vault/tests/test_llm.py
git commit -m "feat: add grounded mistral queries"
```

## Task 6: Generate the standalone graph visualizer

**Files:**
- Create: `day-16-typed-graph-vault/src/renderer.py`
- Create: `day-16-typed-graph-vault/tests/test_renderer.py`

**Step 1: Write failing renderer tests**

```python
def test_render_graph_writes_standalone_svg_html(tmp_path: Path, graph: Graph) -> None:
    output = render_graph(graph, highlighted_path=[], output_path=tmp_path / "graph.html")

    html = output.read_text()
    assert "<svg" in html
    assert "job-queue" in html
    assert "decided_by" in html


def test_render_graph_marks_latest_traversal(tmp_path: Path, graph: Graph, result: TraversalResult) -> None:
    html = render_graph(graph, highlighted_path=result.path, output_path=tmp_path / "graph.html").read_text()

    assert 'class="edge highlighted"' in html
```

**Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_renderer.py -v`

Expected: FAIL because `render_graph` does not exist.

**Step 3: Implement the no-dependency renderer**

- Emit one self-contained UTF-8 HTML file with embedded CSS and SVG; do not use a CDN, server, or third-party JavaScript.
- Use a deterministic simple layout grouped by `kind` or stable grid position.
- Render directional arrows, relation labels, node IDs/titles, and a legend.
- Add CSS classes for nodes/edges in the latest traversal path; leave all other content visible.
- Return the written path. The REPL may open it with Python's `webbrowser` module, but rendering itself must work in a headless test.

**Step 4: Run the focused tests**

Run: `uv run --with pytest pytest tests/test_renderer.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add day-16-typed-graph-vault/src/renderer.py day-16-typed-graph-vault/tests/test_renderer.py
git commit -m "feat: render typed graph visualizations"
```

## Task 7: Assemble the REPL and reload behavior

**Files:**
- Modify: `day-16-typed-graph-vault/src/repl.py`
- Modify: `day-16-typed-graph-vault/main.py`
- Modify: `day-16-typed-graph-vault/tests/test_repl.py`

**Step 1: Write failing REPL behavior tests**

```python
def test_reload_keeps_previous_graph_when_new_vault_is_invalid(app: ReplApp, vault_dir: Path) -> None:
    original = app.graph
    (vault_dir / "broken.md").write_text("---\nid: broken\nlinks:\n  - relation: nope\n    target: missing\n---")

    message = app.reload()

    assert "reload failed" in message.lower()
    assert app.graph is original


def test_ask_declines_when_planner_or_traversal_has_no_grounded_path(app: ReplApp) -> None:
    app.planner = lambda *_: None

    assert app.ask("What is the capital of France?") == "No grounded graph path found."
```

**Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_repl.py -v`

Expected: FAIL because the stateful REPL app does not exist.

**Step 3: Implement the REPL app**

- Create `ReplApp` with the current successfully loaded `Graph`, current vault path, injectable LLM functions, and latest `TraversalResult`.
- At startup, select and validate the vault. Print validation errors and do not enter interactive query mode if no valid graph is available.
- Implement `ask`, `show`, `graph`, `reload`, `help`, and `quit` commands.
- `ask` must: plan, validate, traverse, decline when no valid grounded result exists, synthesize from result only, store the latest path, then print answer/citations/path.
- `graph` must render the current graph with the latest path and open it through `webbrowser.open` only after writing successfully.
- `reload` must replace the active graph only if full validation succeeds; otherwise retain the exact previous object and print all errors.
- Handle blank/unknown commands without crashing.

**Step 4: Run the REPL test suite**

Run: `uv run --with pytest pytest tests/test_repl.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add day-16-typed-graph-vault/main.py day-16-typed-graph-vault/src/repl.py day-16-typed-graph-vault/tests/test_repl.py
git commit -m "feat: add typed graph repl"
```

## Task 8: Add the tracked example vault and deterministic self-check

**Files:**
- Create: `day-16-typed-graph-vault/example-vault/graph.yaml`
- Create: `day-16-typed-graph-vault/example-vault/*.md`
- Modify: `day-16-typed-graph-vault/main.py`
- Create: `day-16-typed-graph-vault/tests/test_example_vault.py`

**Step 1: Write the failing end-to-end fixture test**

```python
def test_example_vault_validates_and_has_causal_decision_path(project_root: Path) -> None:
    graph = load_vault(project_root / "example-vault")

    result = traverse(
        graph,
        TraversalPlan(
            start_nodes=["job-queue"],
            relations=["decided_by", "supersedes", "caused_by"],
            direction="outbound",
        ),
    )

    assert [node.id for node in result.nodes] == [
        "job-queue",
        "adr-007-postgres-queue",
        "adr-003-redis-queue",
        "incident-2026-03-11",
    ]
```

**Step 2: Run the test to verify it fails**

Run: `uv run --with pytest pytest tests/test_example_vault.py -v`

Expected: FAIL because the example vault is missing.

**Step 3: Create the example corpus and self-check**

- Write the approved relation schema and six Markdown notes with valid frontmatter/bodies.
- Add `--self-check` to `main.py`. It must load `example-vault`, run the deterministic causal plan, assert the expected ordered path, render `graph.html` to a temporary directory, and print `self-check OK`.
- The self-check must not import/call Ollama or open a browser.

**Step 4: Run the example and all unit tests**

Run: `uv run --with pytest pytest -v && uv run main.py --self-check`

Expected: all tests PASS and `self-check OK`.

**Step 5: Commit**

```bash
git add day-16-typed-graph-vault/example-vault day-16-typed-graph-vault/main.py day-16-typed-graph-vault/tests
git commit -m "feat: add graph vault demo corpus"
```

## Task 9: Document the runnable project and update its tracker entry

**Files:**
- Create: `day-16-typed-graph-vault/README.md`
- Create: `day-16-typed-graph-vault/AGENTS.md`
- Modify: `README.md`

**Step 1: Write failing documentation acceptance checklist**

Create a manual checklist requiring:

```text
[ ] A fresh clone can run `uv run main.py --self-check` without Ollama.
[ ] The README explains `example-vault/` versus ignored `vault/`.
[ ] The README shows the exact frontmatter and graph.yaml contracts.
[ ] The README documents every REPL command and the grounding failure behavior.
[ ] AGENTS.md lists only verified commands and Ollama gotchas.
```

**Step 2: Verify the checklist is incomplete**

Run: `test -f README.md && test -f AGENTS.md`

Expected: FAIL before the documents are created.

**Step 3: Write concise project documents**

- Explain how to create/copy a private vault without ever committing it.
- State that `mistral:latest` must be pulled and Ollama running for live questions; do not suggest a hosted fallback.
- Document parser rules, invalid-vault blocking, model boundaries, and generated visualizer behavior.
- Fill verified command dates only after executing commands.
- Update Day 16’s tracker description from `TBD` to the measured delivered outcome after live verification.

**Step 4: Verify documented checks**

Run: `uv run --with pytest pytest -v && uv run main.py --self-check`

Expected: PASS.

**Step 5: Commit**

```bash
git add day-16-typed-graph-vault README.md
git commit -m "docs: document typed graph vault"
```

## Task 10: Run the scoped live verification

**Files:**
- Modify only if verification exposes a reproducible defect.

**Step 1: Ensure the required local model is available**

Run: `ollama list | grep 'mistral:latest'`

Expected: a local `mistral:latest` model entry. If missing, stop and ask the user before downloading a model.

**Step 2: Run the no-model verification first**

Run: `uv run --with pytest pytest -v && uv run main.py --self-check`

Expected: all unit tests pass and `self-check OK`.

**Step 3: Run the REPL against the example vault**

Run: `uv run main.py`

Expected: startup states that `example-vault/` is loaded and shows the available commands.

**Step 4: Exercise grounding and visualization manually**

At the prompt, enter:

```text
ask Why did we replace the Redis job queue?
graph
show adr-007-postgres-queue
reload
quit
```

Expected: a Mistral answer cited to retrieved notes, an explicitly printed typed path, a local `graph.html` with highlighted path, note inspection output, successful reload, and clean exit.

**Step 5: Record only observed details**

Update the README, AGENTS.md, and root Day 16 tracker with actual model/runtime behavior only after this run succeeds.

**Step 6: Commit**

```bash
git add day-16-typed-graph-vault README.md
git commit -m "feat: verify typed graph vault"
```
