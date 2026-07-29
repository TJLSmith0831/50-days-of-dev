# Running Models Locally

Ollama serves open-weight language models on localhost at port 11434.
After installing Ollama, pull a model with `ollama pull llama3.2` and
start the server with `ollama serve`. Client libraries then send chat
requests to the local server exactly as they would to a hosted API.

Embeddings can also run locally without Ollama. The
`BAAI/bge-small-en-v1.5` model from HuggingFace is a small English
embedding model that runs on CPU and is a common default for local RAG
setups. The first use downloads the model weights (around 100 MB); later
runs load them from the local cache.

Local models keep data on the machine, cost nothing per call, and work
offline, at the price of slower generation and lower quality than large
hosted models.
