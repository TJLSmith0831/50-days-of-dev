# Agent Memory

An agent's memory is split by how long a fact needs to survive.

**Short-term memory** is the conversation itself: the message list carried
in the context window for the current session. It is complete and exact,
but bounded — once the transcript outgrows the window it must be trimmed
or summarized, and whatever is dropped is gone. Common strategies are a
sliding window over the last N turns, or a rolling summary where older
turns are compressed by the model into a paragraph that stays in context.

**Long-term memory** survives the session. Facts worth keeping — a user's
preferences, a decision made three conversations ago — are written to a
store and retrieved later by relevance rather than recency. In practice
that store is usually a vector index, which makes long-term memory a
retrieval problem: the agent embeds the current situation, searches the
memory store, and pastes the top hits back into context. The failure
modes are retrieval's failure modes, so recall matters more than
precision here — a memory that is never retrieved may as well not exist.

Deciding *what* to write to long-term memory is the hard part. Writing
every turn floods the store and degrades retrieval; writing nothing
leaves the agent amnesiac. Most systems use an explicit extraction step,
which is one more model call to evaluate and tune.
