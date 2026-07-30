# Evaluating LLM Output

There are two ways to score generated answers, and they trade off
differently.

**Golden sets** are hand-written question/answer pairs. A run is scored by
comparing the produced answer to the reference — exact match for short
factual answers, or an overlap metric for longer ones. Golden sets are
deterministic, cheap to re-run, and catch regressions reliably. The cost
is up front and it is large: someone has to write and maintain the
references, and any question outside the set is unmeasured.

**LLM-as-judge** hands the question and the answer to a second model and
asks for a score, usually on a small integer scale like 1 to 5, sometimes
with a short justification. No references are needed, so it scales to any
question, including ones nobody anticipated. The cost is noise. Judges
have known biases: they prefer longer answers, they favor the first
option in a pairwise comparison, and small models tend to collapse toward
a single middle score regardless of quality. A judge that returns 4 for
everything has measured nothing.

Two mitigations matter. Use a judge at least as capable as the model
being judged — a small local judge is the usual source of flat scores.
And average across many questions rather than reading any single verdict,
since the noise is per-call and partially cancels in aggregate.
