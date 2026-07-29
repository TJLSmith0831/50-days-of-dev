"""RAGWorkflow — 3-step LlamaIndex Workflow: ingest → retrieve → synthesize.

A single workflow class handles both entry points (D9): the ingest step
branches on StartEvent fields. Given `dirname`, it builds and persists the
index and stops. Given `query`, it loads the persisted index and emits an
IngestedEvent so the run continues through retrieve → synthesize.
"""

from pathlib import Path

from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.base.llms.base import BaseLLM
from llama_index.core.schema import NodeWithScore
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

DEFAULT_INDEX_DIR = Path(__file__).parent / ".workflow_index"

PROMPT_TEMPLATE = (
    "Answer the question based only on the context below. If the context does "
    'not contain enough information, say "I don\'t know based on the provided '
    'context."\n\nContext: {context}\n\nQuestion: {query}\n\nAnswer concisely.'
)


class IngestedEvent(Event):
    """Index is ready for retrieval — emitted on the query path."""

    index: VectorStoreIndex


class RetrievedEvent(Event):
    """Top-k nodes retrieved for the query."""

    nodes: list[NodeWithScore]


class RAGWorkflow(Workflow):
    def __init__(
        self,
        llm: BaseLLM,
        embed_model: BaseEmbedding,
        index_dir: Path = DEFAULT_INDEX_DIR,
        similarity_top_k: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.embed_model = embed_model
        self.index_dir = Path(index_dir)
        self.similarity_top_k = similarity_top_k

    @step
    async def ingest(self, ctx: Context, ev: StartEvent) -> IngestedEvent | StopEvent:
        dirname = ev.get("dirname")
        if dirname:
            path = Path(dirname)
            if not path.is_dir():
                raise ValueError(f"Not a directory: {dirname}")
            documents = SimpleDirectoryReader(
                str(path), required_exts=[".md"]
            ).load_data()
            if not documents:
                raise ValueError(f"No markdown files found in: {dirname}")
            index = VectorStoreIndex.from_documents(
                documents, embed_model=self.embed_model
            )
            index.storage_context.persist(persist_dir=str(self.index_dir))
            return StopEvent(
                result={
                    "documents": len(documents),
                    "nodes": len(index.storage_context.docstore.docs),
                    "persisted_to": str(self.index_dir),
                }
            )

        query = ev.get("query")
        if query:
            if not self.index_dir.is_dir():
                raise ValueError(
                    f"No index at {self.index_dir} — run `ingest <dir>` first."
                )
            storage_context = StorageContext.from_defaults(
                persist_dir=str(self.index_dir)
            )
            index = load_index_from_storage(
                storage_context, embed_model=self.embed_model
            )
            await ctx.store.set("query", query)
            ingested = IngestedEvent(index=index)
            ctx.write_event_to_stream(ingested)
            return ingested

        raise ValueError("StartEvent needs either `dirname` or `query`.")

    @step
    async def retrieve(self, ctx: Context, ev: IngestedEvent) -> RetrievedEvent:
        query = await ctx.store.get("query")
        retriever = ev.index.as_retriever(similarity_top_k=self.similarity_top_k)
        nodes = await retriever.aretrieve(query)
        retrieved = RetrievedEvent(nodes=nodes)
        ctx.write_event_to_stream(retrieved)
        return retrieved

    @step
    async def synthesize(self, ctx: Context, ev: RetrievedEvent) -> StopEvent:
        query = await ctx.store.get("query")
        context_str = "\n\n".join(node.get_content() for node in ev.nodes)
        response = await self.llm.acomplete(
            PROMPT_TEMPLATE.format(context=context_str, query=query)
        )
        return StopEvent(result={"answer": str(response), "nodes": ev.nodes})
