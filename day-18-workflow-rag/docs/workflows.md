# LlamaIndex Workflows

Workflows are LlamaIndex's event-driven orchestration framework for
multi-step AI applications. A workflow is a class whose methods are
decorated with `@step`. Each step consumes one or more event types and
emits new events; the framework routes events to the steps that accept
them.

Every run starts with a `StartEvent` and finishes when a step returns a
`StopEvent`. Custom events subclass `Event` and carry typed data between
steps, which makes the data flow explicit and inspectable.

Steps are `async` and receive the workflow `Context`, which provides a
key-value store for state that does not belong in events. Running a
workflow returns a handler; `handler.stream_events()` yields every event
as it flows through the pipeline, which is how you observe a run in real
time.
