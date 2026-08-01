"""The system under test: answer a CUAD clause question, or say it isn't there.

One LLM call per case. `gpt-4.1-mini` reads the retrieved chunks and either
extracts the clause text or reports that the contract does not contain it.
"""

import os

from openai import OpenAI
from pydantic import BaseModel, Field

MODEL = "gpt-4.1-mini"

# Says what the task is; deliberately says nothing the evals then check.
#
# The line is worth stating because the previous build got it wrong: its prompt
# told the model to "cite only numbers that appear in the snapshot" and to stay
# "at most 60 words" while two of its evals graded exactly those two things, so
# both scored 1.00 on all 20 cases and could not have done otherwise.
#
# Extraction is the task, so asking for the clause text is fair. What is NOT
# here: any instruction that the answer must appear verbatim in the excerpts
# (`citation_fidelity` grades that), and any instruction to prefer abstaining
# when unsure (`abstention` grades that). Add either and the metric measures
# this file instead of the model.
SYSTEM = """You review commercial contracts. You are given excerpts from one
contract and a question about a category of clause.

If the contract contains such a clause, set found=true and put the relevant
clause text in `answer`, and list the excerpt ids you used in `chunk_ids`.
If it does not contain such a clause, set found=false and leave `answer` empty."""

NO_RAG_SYSTEM = """You review commercial contracts. You are asked about a category
of clause in a specific named contract.

If the contract contains such a clause, set found=true and put the relevant
clause text in `answer`. If it does not, set found=false and leave `answer` empty."""


class ClauseAnswer(BaseModel):
    found: bool = Field(description="Whether the contract contains this clause")
    answer: str = Field(description="The clause text, or empty if not found")
    chunk_ids: list[str] = Field(description="Ids of excerpts used")


def answer(question: str, contract: str, chunks: list, client: OpenAI) -> ClauseAnswer:
    """With chunks, this is RAG. With `chunks=[]` it is the ablation — same
    model, same question, no retrieved text — and the gap between them is the
    only thing that shows whether retrieval is doing any work."""
    if chunks:
        excerpts = "\n\n".join(f"[{c.chunk_id}]\n{c.text}" for c in chunks)
        user = (
            f"Contract: {contract}\n\nExcerpts:\n{excerpts}\n\nQuestion: {question}"
        )
        system = SYSTEM
    else:
        user = f"Contract: {contract}\n\nQuestion: {question}"
        system = NO_RAG_SYSTEM

    completion = client.chat.completions.parse(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=ClauseAnswer,
    )
    return completion.choices[0].message.parsed


def client() -> OpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Put it in day-20-rag-evals/.env "
            "(see .env.example)."
        )
    return OpenAI()
