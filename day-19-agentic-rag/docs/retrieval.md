# Retrieval

Retrieval decides which chunks the model gets to see, which usually
matters more to answer quality than the generation step does.

**Dense retrieval** embeds every chunk into a vector, embeds the query the
same way, and returns the top-k nearest by cosine similarity. It is one
vector search per query, fast enough to be the default, and it catches
paraphrases that keyword search misses. Its weakness is that a single
vector has to summarize a whole chunk, so it is imprecise about which of
several plausibly-relevant chunks is *most* relevant.

**Reranking** fixes that ordering. A cross-encoder takes the query and one
candidate chunk together and scores the pair directly, which is far more
accurate than comparing two independently-made vectors — but it costs one
model pass per candidate, so it cannot score the whole corpus. The
standard pattern is a funnel: dense retrieval fetches a wide candidate
set, and the reranker reorders the top 20 or 50 down to the final k.

Retrieval is evaluated on its own, before any answer is generated. The
usual metrics are recall@k — was the right chunk anywhere in the returned
set — and a rank-sensitive metric like nDCG that also rewards putting it
first. Vague queries are where retrieval degrades most: an
underspecified query embeds to a vector near the center of the corpus and
returns a spread of weakly-related chunks rather than the right ones.
