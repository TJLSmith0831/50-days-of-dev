# Day 07 — Armadillo CLI (Ship Day)

**This folder is a pointer.** All code lives in the separate [armadillo-cli repository](https://github.com/tjlsmith0831/armadillo-cli).

## What is Armadillo CLI?

A local-first CLI agent that learns your codebase before writing a line of code. It uses a four-phase design methodology (DDD → BDD → SDD → TDD), OKF knowledge graphs, and frontier model handoff to produce trustworthy code.

### Key Features

- **Four-phase methodology**: Domain-Driven Design → Behavior-Driven Design → Specification-Driven Design → Test-Driven Development
- **Persistent context**: OKF knowledge graphs in `.armadillo/` persist understanding as markdown across sessions
- **Local-first privacy**: Primary planning happens locally via Ollama; frontier models consulted only for implementation
- **Model routing**: Local models (<14B) handle planning/grilling; frontier models (Claude Code) handle implementation
- **Dynamic tool generation**: Agent adapts to project-specific needs via `.armadillo/tools.yaml`

## Ship Day Status

This is Week 1's portfolio-grade build. See [BRIEF.md](./BRIEF.md) for the full demo brief and Ship Day DoD checklist.

## Repository

[github.com/tjlsmith0831/armadillo-cli](https://github.com/tjlsmith0831/armadillo-cli)
