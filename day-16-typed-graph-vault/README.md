# Typed Graph Vault

A local Markdown knowledge graph with typed, validated links, a split-model REPL (Qwen3 planner + Mistral answerer), and a standalone traversal visualizer.

## Run

```bash
uv run main.py --self-check
uv run main.py
```

For live questions, run Ollama with `qwen3:14b` (planner) and `mistral:latest` (answerer). The tool uses tracked `example-vault/` by default. Create `vault/` for private notes; it is ignored by Git and overrides the example.

## Vault format

`graph.yaml` declares allowed directed relations. Each Markdown note uses frontmatter:

```yaml
---
id: job-queue
kind: component
links:
  - relation: decided_by
    target: adr-007-postgres-queue
---
```

Invalid frontmatter, duplicate IDs, unknown relations, or missing targets block querying. Commands: `ask <question>`, `show <node-id>`, `graph`, `reload`, `help`, and `quit`. `ask` declines with `No grounded graph path found.` when it cannot construct a valid evidence path.
