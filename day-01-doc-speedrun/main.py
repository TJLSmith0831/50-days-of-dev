"""Doc Speedrun — answer questions about documents with LangChain + local Ollama, timed.

Drag and drop any PDF or .docx into the terminal to add it to the store.
Type 'nuke' to clear the store. Type 'exit' to quit.
"""

import time
import os
import re
import shutil
import warnings
from dotenv import load_dotenv
from operator import itemgetter

# langchain-community is sunset with no functional replacement yet for these
# loaders/FAISS (see https://github.com/langchain-ai/langchain-community/issues/674) —
# filter must be set before the first import from the package fires it.
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*langchain-community.*")

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.status import Status
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("faiss").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

load_dotenv()

# Documents are added at runtime via the 'add <file path>' command in the interactive loop.

INDEX_DIR = ".faiss_index"  # where FAISS writes its index files
SPLITTER_PARAMS = {"chunk_size": 1200, "chunk_overlap": 200}


def inspect_retrieval(store: FAISS, questions: list[str], k: int = 4):
    """
    Print the top-k chunks retrieved for each question — no LLM involved.

    :param store: The FAISS index to retrieve from.
    :param questions: The questions to retrieve chunks for.
    :param k: The number of chunks to retrieve for each question.
    """
    retriever = store.as_retriever(search_kwargs={"k": k})
    for q in questions:
        docs = retriever.invoke(q)
        print(f"\n=== {q} ===")
        for i, doc in enumerate(docs):
            preview = doc.page_content[:150].replace("\n", " ")
            print(f"  [{i}] {preview}...")


def build_chat_chain():
    """
    Build a simple chat chain with no retrieval — used when no documents are loaded.

    :return: A chain that passes user input directly to the LLM.
    """
    prompt = ChatPromptTemplate.from_template(
        "You are a helpful conversational assistant. "
        "Answer the user's message naturally and concisely.\n\n"
        "User: {input}"
    )
    llm = ChatOllama(model="llama3.2")
    chain = prompt | llm | StrOutputParser()
    return chain


def build_chain(store: FAISS):
    """
    Build a chain that answers questions about documents in the store.

    :param store: The FAISS vector store to retrieve from.
    :return: A chain that answers questions about documents in the store.
    """
    retriever = store.as_retriever(search_kwargs={"k": 4})

    # Give the LLM strict instructions to only use the provided context
    # If the context doesn't contain enough information, say "I don't know"
    prompt = ChatPromptTemplate.from_template(
        "Answer the question based only on the context below. "
        "If the input is a greeting or casual remark (not a question about the document), respond naturally and briefly as a conversational assistant. "
        "Otherwise, answer the question based only on the context below. "
        "If the context does not contain enough information to answer, "
        'say "I don\'t know based on the provided context."\n\n'
        "Context: {context}\n\nQuestion: {input}"
        "Be concise and direct."
    )

    llm = ChatOllama(model="llama3.2")

    chain = (
        {"context": itemgetter("input") | retriever, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def main():
    console = Console()
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Load existing store from disk if one exists, otherwise start empty.
    store = (
        FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
        if os.path.exists(INDEX_DIR)
        else None
    )

    chain = build_chain(store) if store else build_chat_chain()

    mode = "doc Q&A" if store else "chat"
    console.print(
        f"[bold green]Doc Speedrun[/bold green]  [dim]mode: {mode}[/dim]\n"
        "  [cyan]add <file path>[/cyan]  — drag & drop a PDF or .docx to add it\n"
        "  [cyan]nuke[/cyan]            — clear the document store\n"
        "  [cyan]exit[/cyan]            — quit"
    )

    timings = []
    overall_start = time.perf_counter()
    while True:
        try:
            user_input = input("\n❯ ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() in {"exit", "quit"}:
            break

        # --- add command ---
        if user_input.lower().startswith("add "):
            raw_path = user_input[4:].strip()
            if len(raw_path) >= 2 and raw_path[0] == raw_path[-1] and raw_path[0] in "'\"":
                raw_path = raw_path[1:-1]
            # Terminal drag-and-drop backslash-escapes spaces/specials (e.g. `\ `, `\~`)
            # even when the path is also quoted — undo that before checking the path.
            file_path = re.sub(r"\\(.)", r"\1", raw_path).strip()
            if not os.path.exists(file_path):
                console.print(f"[red]File not found: {file_path}[/red]")
                continue

            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".pdf":
                loader = PyPDFLoader(file_path)
            elif ext == ".docx":
                loader = Docx2txtLoader(file_path)
            else:
                console.print(f"[red]Unsupported file type: {ext}[/red]")
                continue

            with Status("[bold cyan]Adding document...[/bold cyan]", spinner="dots"):
                pages = loader.load()
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=SPLITTER_PARAMS["chunk_size"],
                    chunk_overlap=SPLITTER_PARAMS["chunk_overlap"],
                )
                chunks = splitter.split_documents(pages)
                if store:
                    store.add_documents(chunks)
                else:
                    store = FAISS.from_documents(chunks, embeddings)
                store.save_local(INDEX_DIR)
                chain = build_chain(store)

            console.print(
                f"[green]Added {os.path.basename(file_path)} ({len(chunks)} chunks)[/green]"
            )
            continue

        # --- nuke command ---
        if user_input.lower() == "nuke":
            shutil.rmtree(INDEX_DIR, ignore_errors=True)
            store = None
            chain = build_chat_chain()
            console.print("[bold red]Store nuked. Switched to chat mode.[/bold red]")
            continue

        # --- question ---
        q = user_input
        q_start = time.perf_counter()
        answer = ""
        with Status("[bold cyan]Thinking…[/bold cyan]", spinner="dots"):
            for chunk in chain.stream({"input": q}):
                answer += chunk
        q_elapsed = time.perf_counter() - q_start
        timings.append((q, q_elapsed))

        console.print(
            Panel(
                answer,
                title=f"[bold cyan]Q: {q}[/bold cyan]",
                subtitle=f"[dim]{q_elapsed:.2f}s[/dim]",
                border_style="cyan",
            )
        )

    total = time.perf_counter() - overall_start

    table = Table(title="Per-Question Latency", show_header=True)
    table.add_column("Question", style="white")
    table.add_column("Time", justify="right", style="yellow")
    for q, elapsed in timings:
        table.add_row(q, f"{elapsed:.2f}s")
    table.add_row("[bold]Total[/bold]", f"[bold]{total:.2f}s[/bold]")
    console.print(table)


if __name__ == "__main__":
    main()
