# Local vs Hosted Models

Where the model runs changes what the surrounding system has to handle.

**Local models** run on the machine through a server like Ollama, which
listens on port 11434 and speaks a chat API that client libraries treat
much like a hosted one. Data never leaves the host, there is no
per-token cost, and the thing works offline. In exchange, generation is
slower, the models that fit in local memory are smaller and weaker, and
the first call after startup pays a model-load delay. Small local models
are adequate for mechanical roles — classification, rewriting, routing —
and noticeably weaker at anything requiring judgment.

**Hosted models** are the opposite trade. The frontier-scale models are
only available this way, latency is lower under load because the provider
runs the hardware, and scaling is somebody else's problem. The costs are
per-token billing, an API key to manage, a rate limit to back off from,
and the fact that every prompt leaves the machine.

Mixed deployments are common and often the right answer: run the cheap,
high-volume steps locally and send only the steps that need capability to
a hosted model. Caching sits directly on this seam, since the calls worth
caching are the expensive hosted ones.
