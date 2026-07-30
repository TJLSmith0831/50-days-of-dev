"""AgenticRAGWorkflow — RAG with an agent decision point in front of retrieval.

Day 18's workflow retrieved on the raw query, always. This one classifies the
query first (D7): a specific query goes straight down one retrieve→synthesize
path, a vague one gets rewritten and then runs *both* the raw and the rewritten
query so an LLM judge can score them against each other (D1, D10).

Step graph:

    StartEvent(dirname=…) → ingest → StopEvent
    StartEvent(query=…)   → classify → ClassifiedEvent
                                     → rewrite → AnswerRequest ×1 or ×2
                                               → answer → AnsweredEvent ×1 or ×2
                                                        → judge → StopEvent

`ingest` and `classify` both take StartEvent and each returns None on the
other's path — the entry point stays two single-purpose steps instead of one
branching step.
"""

import re
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

DEFAULT_INDEX_DIR = Path(__file__).parent / ".agentic_rag_index"

# Few-shot, and worth the tokens. Given the same criteria as prose with no
# examples, llama3.2 answers VAGUE to nearly everything — including "what is the
# difference between prompt caching and semantic caching?" — while calling "how
# do I make it faster?" specific. With these four examples it gets 7/9 on a hand
# labelled set, and both misses are format slips, not judgment. Asking for a
# one-line reason alongside the verdict is what degraded it; the verdict is the
# decision, so the reason was dropped rather than the accuracy.
CLASSIFY_PROMPT = (
    "Classify a search query as SPECIFIC or VAGUE.\n\n"
    "SPECIFIC: the query names a topic AND what it wants to know about it.\n"
    "VAGUE: the query is missing one of those — no topic, or a topic with no "
    "question about it.\n\n"
    "Examples:\n"
    "Query: What is the difference between dense retrieval and reranking?\n"
    "Answer: SPECIFIC\n\n"
    "Query: tell me about evaluation\n"
    "Answer: VAGUE\n\n"
    "Query: Why does a small local model make a bad LLM judge?\n"
    "Answer: SPECIFIC\n\n"
    "Query: how do I make it faster?\n"
    "Answer: VAGUE\n\n"
    "Query: {query}\n"
    "Answer:"
)

REWRITE_PROMPT = (
    "Rewrite this vague search query so a document retrieval system returns "
    "better results. Make it specific and self-contained, keep the user's "
    "evident intent, and use terminology the documents would use. The "
    "documents cover: caching, agent memory, evaluation, retrieval, and "
    "local vs hosted model deployment.\n\n"
    "Vague query: {query}\n\n"
    "Reply with the rewritten query only — no preamble, no quotes."
)

ANSWER_PROMPT = (
    "Answer the question based only on the context below. If the context does "
    'not contain enough information, say "I don\'t know based on the provided '
    'context."\n\nContext: {context}\n\nQuestion: {query}\n\nAnswer concisely.'
)

# The judge never sees which path produced the answer, or that there is more
# than one — it scores against the user's original question only (D9).
JUDGE_PROMPT = (
    "Score how well the answer addresses the question, on a 1-5 scale.\n\n"
    "1 = does not address the question or is wrong\n"
    "2 = barely relevant, mostly misses the point\n"
    "3 = partially answers it, notable gaps\n"
    "4 = answers it well, minor gaps\n"
    "5 = fully and precisely answers it\n\n"
    "Question: {question}\n\nAnswer: {answer}\n\n"
    "Reply with the single digit only."
)


class ClassifiedEvent(Event):
    """The agent's verdict on whether the query needs rewriting."""

    is_vague: bool


class RewrittenEvent(Event):
    """The rewritten query — only emitted when classify said vague."""

    rewritten: str


class AnswerRequest(Event):
    """One retrieve→synthesize path to run. Fanned out 1× or 2× by `rewrite`."""

    path: str  # "raw" | "rewritten"
    query: str


class AnsweredEvent(Event):
    """A finished answer from one path, awaiting judgment."""

    path: str
    query: str
    answer: str
    nodes: list[NodeWithScore]


def _parse_score(raw: str) -> int:
    """Pull a 1-5 score out of a judge reply.

    qwen3 is a thinking model and prefixes its reply with a <think> block that
    is full of digits, so that gets stripped before the first digit is taken.
    """
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    match = re.search(r"[1-5]", cleaned)
    if not match:
        raise ValueError(f"judge did not return a 1-5 score: {raw!r}")
    return int(match.group())


def _parse_verdict(raw: str) -> bool:
    """True if the classifier said VAGUE.

    llama3.2 mostly answers with the bare word, but sometimes prefixes it
    ("Based on the criteria, this is SPECIFIC"), so the whole reply is scanned
    and the *last* verdict word wins — that's the conclusion, not the setup.
    Anything unparseable is treated as specific, which costs one answer instead
    of three and never fabricates a comparison out of a failed classification.
    """
    hits = re.findall(r"VAGUE|SPECIFIC", raw.upper())
    return bool(hits) and hits[-1] == "VAGUE"


class AgenticRAGWorkflow(Workflow):
    def __init__(
        self,
        llm: BaseLLM,
        judge_llm: BaseLLM,
        embed_model: BaseEmbedding,
        index_dir: Path = DEFAULT_INDEX_DIR,
        similarity_top_k: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm = llm
        # A larger model than self.llm: the judge is the day's measuring
        # instrument, and a small one flattens every answer to the same
        # score (D8a).
        self.judge_llm = judge_llm
        self.embed_model = embed_model
        self.index_dir = Path(index_dir)
        self.similarity_top_k = similarity_top_k
        # Two steps per query need the index, and a vague query runs two
        # retrievals — reloading it from disk each time is pure waste.
        self._index: VectorStoreIndex | None = None

    def _load_index(self) -> VectorStoreIndex:
        if self._index is None:
            if not self.index_dir.is_dir():
                raise ValueError(
                    f"No index at {self.index_dir} — run `ingest <dir>` first."
                )
            storage_context = StorageContext.from_defaults(
                persist_dir=str(self.index_dir)
            )
            self._index = load_index_from_storage(
                storage_context, embed_model=self.embed_model
            )
        return self._index

    @step
    async def ingest(self, ctx: Context, ev: StartEvent) -> StopEvent | None:
        dirname = ev.get("dirname")
        if not dirname:
            return None  # query path — `classify` picks it up instead
        path = Path(dirname)
        if not path.is_dir():
            raise ValueError(f"Not a directory: {dirname}")
        documents = SimpleDirectoryReader(str(path), required_exts=[".md"]).load_data()
        if not documents:
            raise ValueError(f"No markdown files found in: {dirname}")
        index = VectorStoreIndex.from_documents(documents, embed_model=self.embed_model)
        index.storage_context.persist(persist_dir=str(self.index_dir))
        self._index = index
        return StopEvent(
            result={
                "documents": len(documents),
                "nodes": len(index.storage_context.docstore.docs),
                "persisted_to": str(self.index_dir),
            }
        )

    @step
    async def classify(self, ctx: Context, ev: StartEvent) -> ClassifiedEvent | None:
        query = ev.get("query")
        if not query:
            # Neither field set: no step would run, and the workflow would sit
            # there until the 45s timeout instead of saying what was wrong.
            if not ev.get("dirname"):
                raise ValueError("StartEvent needs either `dirname` or `query`.")
            return None  # ingest path — `ingest` picks it up instead
        # Fail here rather than after the classify call has been paid for.
        self._load_index()
        await ctx.store.set("query", query)
        response = str(await self.llm.acomplete(CLASSIFY_PROMPT.format(query=query)))
        classified = ClassifiedEvent(is_vague=_parse_verdict(response))
        ctx.write_event_to_stream(classified)
        return classified

    @step
    async def rewrite(self, ctx: Context, ev: ClassifiedEvent) -> AnswerRequest | None:
        query = await ctx.store.get("query")
        if not ev.is_vague:
            # Already specific — one path, one score, nothing to compare (D7).
            await ctx.store.set("expected_answers", 1)
            return AnswerRequest(path="raw", query=query)

        response = await self.llm.acomplete(REWRITE_PROMPT.format(query=query))
        rewritten = str(response).strip().strip('"')
        ctx.write_event_to_stream(RewrittenEvent(rewritten=rewritten))
        await ctx.store.set("rewritten", rewritten)
        await ctx.store.set("expected_answers", 2)
        # Both run against the same index, so the only difference between the
        # two answers is the query text — which is the comparison (D1).
        ctx.send_event(AnswerRequest(path="raw", query=query))
        ctx.send_event(AnswerRequest(path="rewritten", query=rewritten))
        return None

    # num_workers=1, deliberately. At 2 the raw and rewritten paths embed their
    # queries at the same time on one shared HuggingFaceEmbedding, and torch
    # intermittently spins forever instead of returning — two cores pinned, no
    # Ollama traffic, no timeout. Serial costs nothing real: Ollama runs one
    # llama3.2 generation at a time regardless of how many callers are waiting.
    @step(num_workers=1)
    async def answer(self, ctx: Context, ev: AnswerRequest) -> AnsweredEvent:
        retriever = self._load_index().as_retriever(
            similarity_top_k=self.similarity_top_k
        )
        nodes = await retriever.aretrieve(ev.query)
        context_str = "\n\n".join(node.get_content() for node in nodes)
        response = await self.llm.acomplete(
            ANSWER_PROMPT.format(context=context_str, query=ev.query)
        )
        answered = AnsweredEvent(
            path=ev.path,
            query=ev.query,
            answer=str(response).strip(),
            nodes=nodes,
        )
        ctx.write_event_to_stream(answered)
        return answered

    @step
    async def judge(self, ctx: Context, ev: AnsweredEvent) -> StopEvent | None:
        expected = await ctx.store.get("expected_answers")
        collected = ctx.collect_events(ev, [AnsweredEvent] * expected)
        if collected is None:
            return None

        question = await ctx.store.get("query")
        scored = {}
        for answered in collected:
            assert isinstance(answered, AnsweredEvent)
            verdict = await self.judge_llm.acomplete(
                JUDGE_PROMPT.format(question=question, answer=answered.answer)
            )
            scored[answered.path] = {
                "query": answered.query,
                "answer": answered.answer,
                "nodes": answered.nodes,
                "score": _parse_score(str(verdict)),
            }
        return StopEvent(
            result={
                "question": question,
                "skipped_rewrite": expected == 1,
                "rewritten": await ctx.store.get("rewritten", default=None),
                "paths": scored,
            }
        )
