# Day 20 — RAG Scorecard

Contract-clause RAG over 50 real CUAD contracts, and six deterministic evals over it. **No LLM judge anywhere** — a lawyer already located every answer, so every metric is arithmetic over a labelled span.

## Does retrieval earn its place? Yes, provably.

| eval | no retrieval | with retrieval | |
|---|---|---|---|
| **exact_match** | **0.00** — *no signal, never varied* | **0.56** | **+0.56** |
| abstention | 0.43 | 0.76 | +0.33 |
| token_f1 | 0.33 *(boilerplate floor)* | 0.46 | +0.13 |
| context_recall | 0.58 | 0.85 | *mechanical — no chunks to recall* |
| citation_fidelity | 0.01 | 0.99 | *mechanical — nothing to cite* |

`exact_match = 0.00` on the ablation is the whole argument. Across 104 answerable questions, the model with no contract text produced correct clause text **exactly zero times**. The answer is contract-specific and simply isn't in the weights. Only the top three rows are honest comparisons; the bottom two move because the ablation has no chunks by construction.

## Without evidence, the model says yes to everything

```
                  the hard half — abstention
 lawyer says          n   model said found   correct   rate
 NO RETRIEVAL
   clause IS present  104              104       104   100%
   clause is ABSENT   146              143         3     2%
 WITH RETRIEVAL
   clause IS present  104               77        77    74%
   clause is ABSENT   146               34       112    77%
```

Asked "does this contract contain a cap on liability?" with no contract in front of it, `gpt-4.1-mini` answered **found on 247 of 250 questions** — including 143 of the 146 clauses lawyers confirmed are absent. Retrieval takes absent-clause accuracy from **2% to 77%**.

## Where it still fails, and why

Top-k retrieval **cannot return nothing**. Ask for a clause the contract lacks and the retriever still hands over six plausible chunks, so the model picks the closest and calls it found — 34 times out of 146. Every one is lexically adjacent but legally distinct:

| asked for | model returned | actually is |
|---|---|---|
| Termination for Convenience | *"automatically renewed for another one (1) year"* | auto-renewal |
| Exclusivity | *"No Joint Venturer shall… pledge, sell, or transfer an interest"* | anti-assignment |
| License Grant | *"Aduro shall be the sole and exclusive owner of… hereby assigns"* | IP assignment |

Separately, `context_recall` 0.85 against `token_f1` 0.46 splits the two halves: **retrieval usually finds the clause; the model then extracts the wrong span boundaries.** Different problem, different fix. Part of the recall gap is a k-limit rather than bad ranking — CUAD's License Grant answers run to 9 gold spans (median 2), and top-6 chunks cannot cover them all.

## Why CUAD

An eval only carries information if the thing it grades can fail *and* you can tell when it did. CUAD gives both: a lawyer-located character span for every answerable question, and an explicit `is_impossible` flag for the 146 questions where the clause genuinely isn't there. That second half is what makes abstention — the hard part of RAG — measurable at all.

The `spread` column flags any metric that never varies. It fired once, on the ablation's `exact_match`, and that was the finding rather than a defect.

## Run

```bash
uv run main.py
```

Needs `OPENAI_API_KEY` in `.env` (see `.env.example`). REPL: `ask <n>`, `eval`, `eval norag`, `both`, `exit`.
`uv run evals.py` runs the metric self-check alone. One `eval` pass is ~12 min (250 cases).

## Stack

Python · `gpt-4.1-mini` · `text-embedding-3-small` · [CUAD](https://www.atticusprojectai.org/cuad) (Hendrycks et al., NeurIPS 2021, CC BY 4.0) · `rich`

See [BRIEF.md](BRIEF.md) for full findings and [AGENTS.md](AGENTS.md) for gotchas.
