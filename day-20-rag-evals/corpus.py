"""CUAD as a retrieval corpus: real contracts, chunked, embedded, searched.

CUAD (Contract Understanding Atticus Dataset, Hendrycks et al., NeurIPS 2021,
CC BY 4.0) is 510 real commercial contracts with 13k+ clause spans annotated by
lawyers across 41 categories. Two properties make it the right corpus for an
eval day, and both are things the previous version of Day 20 did not have:

  the answer already exists   — a gold character span, located by a human, in a
                                document. Not a forecast, not a base rate. Token
                                overlap against it is decidable arithmetic.
  absence is labelled too     — `is_impossible` marks the questions where the
                                lawyers looked and the clause genuinely is not
                                in that contract. That is the ground truth for
                                abstention, which is the hard half of RAG and is
                                almost never measurable.

Retrieval is scoped to the contract the question is about, which is how a real
contract-review tool works ("in THIS agreement, is there a cap on liability?").
The interesting failure is not cross-contract confusion, it is that top-k always
returns k chunks whether or not the clause exists — see evals.abstention.
"""

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import hf_hub_download
from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"
TOP_K = 6
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200
CACHE = Path(__file__).parent / ".cuad_cache.json"

REPO, CUAD_FILE = "theatticusproject/cuad", "CUAD_v1/CUAD_v1.json"

# Five of CUAD's 41 categories, chosen for having BOTH plentiful positives and
# plentiful negatives across the 510 contracts (measured: License Grant 255/255,
# Cap On Liability 275/235, Audit Rights 214/296, Termination For Convenience
# 183/327, Exclusivity 180/330). A category that is 390/120 would make the
# abstention metric a formality; these keep both halves of the task real.
CATEGORIES = [
    "License Grant",
    "Cap On Liability",
    "Audit Rights",
    "Termination For Convenience",
    "Exclusivity",
]
N_CONTRACTS = 50

# Contracts under this are stubs (CUAD's shortest is 645 chars); over it, a
# single agreement would dominate the embedding budget. Median CUAD contract is
# ~33k chars, so this band keeps almost all of them.
MIN_CHARS, MAX_CHARS = 8_000, 60_000


@dataclass
class Chunk:
    chunk_id: str
    contract: str
    start: int  # character offset into the contract, for gold-span overlap
    text: str


@dataclass
class Case:
    """One question with lawyer-labelled ground truth."""

    case_id: str
    contract: str
    category: str
    question: str
    gold_answers: list[str]  # empty when the clause is absent
    gold_spans: list[tuple[int, int]]  # (start, end) char offsets
    impossible: bool


def _chunk(contract: str, text: str) -> list[Chunk]:
    """Fixed-width overlapping windows, snapped to a newline where one is close.

    Overlap is not decoration: a cap-on-liability clause split across a boundary
    is unretrievable by either half, and CUAD's gold spans run to several hundred
    characters. The snap keeps chunks from starting mid-sentence, which reads
    badly in the REPL and embeds slightly worse.
    """
    chunks, start, i = [], 0, 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):
            nl = text.rfind("\n", start + CHUNK_CHARS // 2, end)
            if nl != -1:
                end = nl
        chunks.append(Chunk(f"{contract}#{i}", contract, start, text[start:end]))
        i += 1
        if end >= len(text):
            break
        start = max(start + 1, end - CHUNK_OVERLAP)
    return chunks


def load_cuad() -> tuple[list[Chunk], list[Case]]:
    """Download CUAD, take a deterministic sample, chunk it, build the cases.

    Deterministic on purpose — contracts are taken in sorted-title order, not
    sampled randomly, so a rerun scores the same set and a recorded demo stays
    true. This mirrors the hardcoded case list the previous build used.
    """
    path = hf_hub_download(REPO, CUAD_FILE, repo_type="dataset")
    data = json.load(open(path))["data"]

    picked = []
    for entry in sorted(data, key=lambda e: e["title"]):
        text = entry["paragraphs"][0]["context"]
        if MIN_CHARS <= len(text) <= MAX_CHARS:
            picked.append(entry)
        if len(picked) == N_CONTRACTS:
            break

    chunks, cases = [], []
    for entry in picked:
        title = entry["title"]
        para = entry["paragraphs"][0]
        chunks += _chunk(title, para["context"])
        for qa in para["qas"]:
            category = qa["id"].split("__")[-1]
            if category not in CATEGORIES:
                continue
            cases.append(
                Case(
                    case_id=qa["id"],
                    contract=title,
                    category=category,
                    question=qa["question"],
                    gold_answers=[a["text"] for a in qa["answers"]],
                    gold_spans=[
                        (a["answer_start"], a["answer_start"] + len(a["text"]))
                        for a in qa["answers"]
                    ],
                    impossible=qa["is_impossible"],
                )
            )
    return chunks, cases


def short_question(case: Case) -> str:
    """CUAD questions are boilerplate-wrapped: `Highlight the parts (if any) of
    this contract related to "X" that should be reviewed by a lawyer. Details: Y`.

    The wrapper is identical on all 41 categories, so it is pure noise in an
    embedding — every question would look alike. Strip to the category and its
    description, which is what actually distinguishes them.
    """
    m = re.search(r'related to "([^"]+)"', case.question)
    topic = m.group(1) if m else case.category
    detail = case.question.split("Details:", 1)[-1].strip() if "Details:" in case.question else ""
    return f"{topic}. {detail}".strip()


def _embed(texts: list[str], client: OpenAI) -> list[list[float]]:
    out = []
    for i in range(0, len(texts), 256):  # the API caps inputs per request
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts[i : i + 256])
        out.extend(d.embedding for d in resp.data)
    return out


class Corpus:
    def __init__(self, chunks: list[Chunk], vectors: list[list[float]]):
        self.chunks, self.vectors = chunks, vectors
        self.norms = [math.sqrt(sum(x * x for x in v)) for v in vectors]
        self.by_contract: dict[str, list[int]] = {}
        for i, c in enumerate(chunks):
            self.by_contract.setdefault(c.contract, []).append(i)

    @classmethod
    def build(cls, chunks: list[Chunk], client: OpenAI) -> "Corpus":
        """Cached on disk keyed by the chunking parameters and the chunk count —
        change either and the cache misses instead of silently serving vectors
        that no longer line up with the chunks."""
        key = f"v1|{EMBED_MODEL}|{CHUNK_CHARS}|{CHUNK_OVERLAP}|{len(chunks)}"
        if CACHE.exists():
            blob = json.loads(CACHE.read_text())
            if blob.get("key") == key:
                return cls(chunks, blob["vectors"])
        vectors = _embed([c.text for c in chunks], client)
        CACHE.write_text(json.dumps({"key": key, "vectors": vectors}))
        return cls(chunks, vectors)

    def search(
        self, query: str, contract: str, client: OpenAI, k: int = TOP_K
    ) -> list[Chunk]:
        """Top-k by cosine, scoped to one contract.

        Note what this cannot do: return fewer than k. If the contract has no
        cap-on-liability clause, this still hands back the six chunks that look
        most like one — indemnity, warranty disclaimers, limitation language.
        Top-k has no way to say "nothing here". That is not a bug to fix here,
        it is the thing `evals.abstention` exists to measure.
        """
        qv = _embed([query], client)[0]
        qn = math.sqrt(sum(x * x for x in qv))
        idx = self.by_contract.get(contract, [])
        scored = sorted(
            idx,
            key=lambda i: sum(a * b for a, b in zip(qv, self.vectors[i]))
            / (qn * self.norms[i]),
            reverse=True,
        )
        return [self.chunks[i] for i in scored[:k]]
