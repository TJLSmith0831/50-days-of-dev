# Day 20 — RAG Scorecard — AGENTS.md
Contract-clause RAG over 50 real CUAD contracts, and six deterministic evals over it — the sharp one being abstention, because 146 of the 250 questions ask about a clause lawyers confirmed is **not there**.

## Stack
Python · OpenAI `gpt-4.1-mini` (answers) · `text-embedding-3-small` (1,747 chunks) · CUAD via `huggingface_hub` · `rich` (CLI)

## Commands (verified 2026-07-31)
`uv run main.py` — needs `OPENAI_API_KEY` in `day-20-rag-evals/.env` (see `.env.example`).
REPL: `ask <n>` · `eval` · `eval norag` · `both` · `exit`. `uv run evals.py` runs the metric self-check alone.

## Concept
An eval only means something if its ground truth is decidable. CUAD gives a lawyer-located character span for every answerable question and an explicit `is_impossible` flag for every clause that genuinely isn't in the contract — so all six metrics are arithmetic over a labelled span, and no LLM judge appears anywhere in this day.

## Gotchas
- **Top-k cannot return nothing.** Ask about a cap on liability in a contract that has none and the retriever still hands over six chunks of indemnity and warranty language. This is not a bug to fix in `Corpus.search`; it is the thing `evals.abstention` exists to measure, and it is where the system fails (34 invented clauses out of 146 absent ones).
- **Don't put the eval rubric in the prompt.** `agent.SYSTEM` states the extraction task and deliberately says nothing about answering verbatim (`citation_fidelity` grades that) or about preferring abstention (`abstention` grades that). An earlier version of this day told the model to "cite only numbers that appear" and "stay under 60 words" while two evals graded exactly those, so both scored 1.00 on every case and could not have done otherwise.
- `token_f1`/`exact_match` are **skipped, not zeroed**, on absent-clause cases. A model that correctly says "not present" has not got the extraction wrong — it's graded by `abstention`. Scoring 0 there would punish the behaviour the day most wants to reward, and would drag the mean down with 146 of 250 cases.
- `context_recall` compares **character offsets**, not strings. The same sentence can appear twice in a contract, and the gold answer is defined by position. It also uses interval *overlap*, so a gold span straddling a chunk boundary counts as retrieved — the `_demo()` pins the off-by-one.
- `short_question()` is load-bearing. Every CUAD question is wrapped in identical boilerplate (`Highlight the parts (if any) of this contract related to "X"…`), so embedding the raw question makes all 41 categories look alike. Only the topic and its description are distinguishing.
- Chunk overlap (`CHUNK_OVERLAP = 200`) matters: CUAD gold spans run to several hundred characters, and a clause split across a boundary is unretrievable from either half.
- `.cuad_cache.json` is generated state, gitignored, and **52 MB** — it's 1,747 × 1536 floats as JSON. Keyed by embed model + chunk params + chunk count, so changing any of them misses the cache rather than silently serving misaligned vectors.
- **Rich's `console.status` renders nothing when stdout isn't a tty.** A piped `both` run printed no output for ~24 minutes and looked hung. `run_eval` uses `console.print` every 25 cases instead — keep it that way for recorded demos and CI-ish runs.
- Budget: one `eval` pass is 250 chat calls + 250 query embeddings ≈ **12 min** at ~2.8 s/case. `both` is double that. Run the two passes separately unless you want a 24-minute wait.
- CUAD is CC BY 4.0 (Hendrycks et al., NeurIPS 2021). The contracts are real EDGAR filings and the labels are real lawyer annotations — attribute it, and treat its labels as ground truth with the usual caveat that annotation of "is this a License Grant?" has genuine edge cases.
