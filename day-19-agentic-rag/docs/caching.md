# Caching LLM Calls

Two different things get called "caching" in LLM systems, and they solve
different problems.

**Prompt caching** stores the model's internal representation of a long,
unchanging prefix — a system prompt, a tool schema block, a retrieved
document set — so repeated requests that share that prefix skip
recomputing it. The lookup is exact: the prefix must match byte for byte
up to the cache breakpoint. It reduces cost and time-to-first-token on
the *same* prompt, and does nothing for a prompt that is merely similar.

**Semantic caching** stores past question/answer pairs and, on a new
question, embeds it and searches for a past question above a similarity
threshold. A hit returns the stored answer without calling the model at
all. This catches paraphrases — "what's the refund window" and "how long
do I have to return this" hit the same entry — but it can serve a stale
or subtly wrong answer when the threshold is set too loose. Tuning that
threshold is an evaluation problem: too tight and the hit rate collapses,
too loose and the cache starts lying.

A semantic cache is also a form of memory: it is a store of past
interactions consulted before acting. The difference from agent memory is
scope — a cache is keyed by question and shared across users, while
memory is keyed by conversation and belongs to one.
