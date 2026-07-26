"""Agent Memory Recall — compare a stateless baseline against a Mem0-backed agent.

Each of 3 fact/question pairs is tested in two lanes:
- no-memory: each turn is an independent Ollama chat call with no prior context.
- memory-backed: seed + filler turns are stored in a local Mem0 instance, then
  retrieved before the recall question.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import ollama
from mem0 import Memory

MODEL = "mistral:latest"
EMBEDDER = "nomic-embed-text:latest"
BASE_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
CHROMA_PATH = Path("chroma_db")
DEFAULT_SYSTEM = "You are a helpful assistant. Answer concisely."


@dataclass
class Pair:
    seed: str
    fillers: list[str]
    question: str
    keyword: str
    user_id: str


PAIRS: list[Pair] = [
    Pair(
        seed="My favorite programming language is Rust.",
        fillers=[
            "What is the weather like today?",
            "Tell me a short joke.",
            "What is 7 multiplied by 8?",
        ],
        question="What is my favorite programming language?",
        keyword="rust",
        user_id="pair-1",
    ),
    Pair(
        seed="I grew up in Kyoto, Japan.",
        fillers=[
            "Who won the FIFA World Cup in 2022?",
            "Explain photosynthesis in one sentence.",
            "What is the capital of France?",
        ],
        question="Where did I grow up?",
        keyword="kyoto",
        user_id="pair-2",
    ),
    Pair(
        seed="My dog's name is Pixel.",
        fillers=[
            "Convert 10 USD to EUR.",
            "What is the speed of light?",
            "Recommend a good science fiction book.",
        ],
        question="What is my dog's name?",
        keyword="pixel",
        user_id="pair-3",
    ),
]


def reset_chroma() -> None:
    """Remove stale local Chroma data so each run starts fresh."""
    shutil.rmtree(CHROMA_PATH, ignore_errors=True)
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)


def build_memory() -> Memory:
    """Create a local Mem0 instance backed by Ollama + Chroma."""
    config = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": MODEL,
                "ollama_base_url": BASE_URL,
                "temperature": 0.1,
                "max_tokens": 2000,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": EMBEDDER,
                "ollama_base_url": BASE_URL,
                "embedding_dims": 768,
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "memories",
                "path": str(CHROMA_PATH),
            },
        },
    }
    return Memory.from_config(config)


def chat(system: str, user: str) -> str:
    """Issue a single-turn, fresh-session Ollama chat call."""
    client = ollama.Client(host=BASE_URL)
    response = client.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.message.content or ""


def truncate(text: str, max_len: int = 60) -> str:
    """Return a snippet of text for the report."""
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def grade(answer: str, keyword: str) -> str:
    return "Pass" if keyword.lower() in answer.lower() else "Fail"


def say(line: str) -> None:
    """Emit a progress line. Unbuffered so the terminal capture stays live."""
    print(line, flush=True)


def no_memory_lane(pair: Pair) -> tuple[str, str]:
    """Run seed, fillers, and recall as independent fresh-session calls."""
    say(f"\n[{pair.user_id}] no-memory lane")
    for index, turn in enumerate([pair.seed, *pair.fillers]):
        chat(DEFAULT_SYSTEM, turn)
        label = "seed" if index == 0 else "filler"
        say(f"  {label:<7} {truncate(turn, 50):<52} (fresh session, nothing kept)")
    say(f"  ask     {pair.question}")
    answer = chat(DEFAULT_SYSTEM, pair.question)
    verdict = grade(answer, pair.keyword)
    say(f"  {verdict:<7} {truncate(answer, 60)}")
    return verdict, answer


def memory_backed_lane(pair: Pair, memory: Memory) -> tuple[str, str]:
    """Store every turn in Mem0, retrieve before the recall question."""
    say(f"\n[{pair.user_id}] memory-backed lane")
    for index, turn in enumerate([pair.seed, *pair.fillers]):
        response = chat(DEFAULT_SYSTEM, turn)
        label = "seed" if index == 0 else "filler"
        # Persist both sides of the turn under the pair's isolated user_id.
        memory.add(
            messages=[
                {"role": "user", "content": turn},
                {"role": "assistant", "content": response},
            ],
            user_id=pair.user_id,
        )
        say(f"  {label:<7} {truncate(turn, 50):<52} -> stored in Mem0 + Chroma")

    # Retrieve relevant memories scoped to this pair.
    say(f"  ask     {pair.question}")
    results = memory.search(
        query=pair.question,
        filters={"user_id": pair.user_id},
        top_k=3,
    )
    # search() returns {"results": [...]}; the bare-list form needs the isinstance
    # check first — results.get(...) raises AttributeError on a list before any
    # default is reached, so the fallback it was written for could never run.
    memories = results["results"] if isinstance(results, dict) else results
    memory_texts = [m.get("memory", m.get("text", "")) for m in memories]
    memory_block = "\n".join(f"- {t}" for t in memory_texts if t)
    system = DEFAULT_SYSTEM
    if memory_block:
        system = f"{DEFAULT_SYSTEM}\n\nRelevant memories for this user:\n{memory_block}"
    say(f"  recall  {len(memory_texts)} memories retrieved")
    for text in memory_texts:
        if text:
            say(f"          - {truncate(text, 60)}")
    answer = chat(system, pair.question)
    verdict = grade(answer, pair.keyword)
    say(f"  {verdict:<7} {truncate(answer, 60)}")
    return verdict, answer


def print_report(rows: list[tuple[str, str, str, str, str, str]]) -> None:
    """Print the pass/fail table and totals row."""
    print(
        f"\n{'Pair':<10} {'No-Mem':<8} {'No-Mem Answer':<45} {'Mem':<8} {'Mem Answer':<45}"
    )
    print("-" * 120)
    no_mem_passes = 0
    mem_passes = 0
    for pair_id, no_mem_grade, no_mem_answer, mem_grade, mem_answer, _ in rows:
        # Truncate to the column width, or the answer overflows and shears the table.
        print(
            f"{pair_id:<10} {no_mem_grade:<8} {truncate(no_mem_answer, 45):<45} "
            f"{mem_grade:<8} {truncate(mem_answer, 45):<45}"
        )
        if no_mem_grade == "Pass":
            no_mem_passes += 1
        if mem_grade == "Pass":
            mem_passes += 1
    print("-" * 120)
    print(f"{'Totals':<10} {no_mem_passes:<8} {'':<45} {mem_passes:<8}")


def self_check() -> None:
    """Assert the pure report logic. Runs without Ollama: `uv run main.py --self-check`."""
    assert truncate("x" * 80, 45) == "x" * 42 + "...", "truncate must not exceed its width"
    assert len(truncate("x" * 80, 45)) == 45, "an over-wide answer would shear the table"
    assert truncate("short", 45) == "short"
    assert grade("Your favorite is Rust.", "rust") == "Pass"
    assert grade("I have no preferences.", "rust") == "Fail"
    print("self-check OK")


def main() -> None:
    say(f"agent memory recall — {len(PAIRS)} pairs x 2 lanes")
    say(f"local stack: ollama {MODEL} + {EMBEDDER} + chroma  (no API key)")
    reset_chroma()
    memory = build_memory()

    rows: list[tuple[str, str, str, str, str, str]] = []
    for pair in PAIRS:
        no_mem_grade, no_mem_answer = no_memory_lane(pair)
        mem_grade, mem_answer = memory_backed_lane(pair, memory)
        rows.append(
            (pair.user_id, no_mem_grade, no_mem_answer, mem_grade, mem_answer, pair.keyword)
        )

    print_report(rows)


if __name__ == "__main__":
    import sys

    if "--self-check" in sys.argv:
        self_check()
    else:
        main()
