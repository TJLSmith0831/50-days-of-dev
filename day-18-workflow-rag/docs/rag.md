# Retrieval-Augmented Generation

Retrieval-Augmented Generation (RAG) answers questions by combining a
retriever with a language model. Documents are split into chunks, each
chunk is embedded into a vector, and the vectors are stored in an index.
At query time the question is embedded, the most similar chunks are
retrieved, and those chunks are placed in the model's prompt as context.

A typical RAG pipeline has three stages:

1. **Ingest** — load documents, chunk them, embed them, and build a
   vector index.
2. **Retrieve** — embed the query and fetch the top-k most similar
   chunks (nodes) from the index.
3. **Synthesize** — pass the retrieved nodes and the question to the LLM
   to generate a grounded answer.

RAG reduces hallucination because the model answers from retrieved
context instead of relying only on its training data.
