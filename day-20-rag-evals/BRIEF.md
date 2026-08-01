# Day 20 — RAG Scorecard — BRIEF.md

## What was built

Contract-clause RAG over CUAD, and the eval harness that grades it. `corpus.py` downloads CUAD v1 via `huggingface_hub`, takes a deterministic sample of 50 contracts (sorted by title, 8k–60k chars), chunks each into 1,200-char overlapping windows (1,747 chunks), embeds with `text-embedding-3-small`, and searches top-6 by cosine scoped to one contract. `agent.py` asks `gpt-4.1-mini` to either extract the clause or report it absent. `evals.py` scores six metrics, all deterministic. `main.py` is a Rich REPL: `ask <n>` runs one case, `eval` runs all 250, `eval norag` runs the identical cases with no retrieved text.

The case set is 250 lawyer-labelled questions across 5 CUAD categories chosen for having both plentiful positives and negatives — **104 answerable, 146 where the clause is genuinely absent**.

## The eval suite

| eval | what it catches |
|---|---|
| `context_recall` | did the retrieved chunks contain the gold span (character-offset overlap) |
| `token_f1` | SQuAD token-F1 of the answer against the best-matching gold span |
| `exact_match` | stricter normalised containment, either direction |
| `citation_fidelity` | is the answer actually in the excerpts, or answered from memory |
| `abstention` | on the 146 absent-clause cases, did it correctly say so |
| `spread` (column) | flags any metric that never varied — no information, whatever the mean |

No LLM judge anywhere. That is the payoff of a domain with decidable ground truth.

## Results — 250 cases

| eval | no retrieval | with retrieval |
|---|---|---|
| context_recall | 0.58 | 0.85 |
| token_f1 | 0.33 | 0.46 |
| **exact_match** | **0.00** (spread 0.000 — *no signal*) | **0.56** |
| citation_fidelity | 0.01 | 0.99 |
| abstention | 0.43 | 0.76 |

Abstention split:

| | n | said found | correct | rate |
|---|---|---|---|---|
| no-RAG, clause IS present | 104 | 104 | 104 | 100% |
| no-RAG, clause is ABSENT | 146 | 143 | 3 | **2%** |
| RAG, clause IS present | 104 | 77 | 77 | 74% |
| RAG, clause is ABSENT | 146 | 34 | 112 | **77%** |

## Discoveries

1. **The ablation's `exact_match` is 0.00 with zero spread.** Across 104 answerable questions the model with no contract text produced correct clause text *exactly zero times*. This is the cleanest possible demonstration that RAG is load-bearing — the answer is contract-specific and not in the weights. `spread` flagged it as "no signal", which here is the result rather than a defect: the baseline is a floor, not a fluke.

2. **Without evidence the model says yes to everything.** It answered "found" on **247 of 250** questions, including 143 of the 146 clauses lawyers confirmed absent. An LLM asked "does this contract contain X?" with nothing to read essentially never says no. Retrieval moves absent-clause accuracy from **2% → 77%**.

3. **Top-k cannot return nothing, and that is where RAG still fails.** 34 of 146 absent clauses were invented. Every inspected case is lexically adjacent but legally distinct: Termination-for-Convenience answered with an auto-renewal clause; Exclusivity answered with an anti-assignment restriction; License Grant answered with an IP *assignment* clause (assignment is the opposite of a licence). The retriever surfaces the most similar chunk and has no way to signal "none of these is the right kind".

4. **Retrieval and generation fail differently, and the split says which to fix.** `context_recall` 0.85 vs `token_f1` 0.46 — retrieval usually finds the clause and the model then extracts the wrong span boundaries. Fixing the retriever would not move token_f1 much.

5. **Part of the recall gap is a k-limit, not bad ranking.** CUAD's License Grant answers carry up to 9 gold spans (median 2), and top-6 chunks cannot cover them all — 15 of 25 License Grant cases scored partial recall. Raising k or scoring recall@span rather than recall@case would separate these; as measured, "retrieval quality" and "k is too small" are conflated.

6. **`token_f1` 0.33 on the ablation is a floor, not knowledge.** Legal boilerplate shares enough vocabulary after normalisation that a fabricated clause overlaps a real one by a third. Its spread is 0.100 — much flatter than the 0.347 with retrieval. Quote `exact_match` for the RAG-vs-no-RAG claim; token_f1 alone would overstate the baseline.

7. **The prompt deliberately omits the rubric.** `agent.SYSTEM` states the extraction task and says nothing about answering verbatim or about preferring abstention, because `citation_fidelity` and `abstention` grade exactly those. An earlier version of this day (different domain) told the model to "cite only numbers that appear" and "stay under 60 words" while two evals checked precisely that — both scored 1.00 on all cases and could not have done otherwise.

## Verification

- `uv run evals.py` — self-check passes; 20 asserts pinning normalisation, token-F1 boundary behaviour, character-offset overlap (including a gold span straddling a chunk boundary), and all four abstention quadrants.
- `printf 'eval\nexit\n' | uv run main.py` and `printf 'eval norag\nexit\n' | uv run main.py` — both full 250-case runs completed 2026-07-31; every number above is read off that output.
- Corpus: 50 real contracts, 1,747 chunks, 250 questions, 146 of them absent-clause.
- False positives spot-checked by hand against the contract text (the four in finding 3).
- Not run: no check that CUAD's own labels are free of annotation error. "Is this a License Grant?" has genuine edge cases, and some of the 34 inventions may be defensible readings.

## Honest limits

- 5 of CUAD's 41 categories, 50 of its 510 contracts. Categories were chosen for positive/negative balance, which makes abstention measurable but is not a random sample of contract review.
- Retrieval is scoped to the correct contract. A real repository tool must also pick the right document; cross-contract confusion is untested here.
- `temperature=0` is not full determinism with the OpenAI API; expect small movement on rerun.
- Chunking is fixed-width, not clause-aware. A structure-aware splitter would likely raise `context_recall` and is the obvious next lever.
