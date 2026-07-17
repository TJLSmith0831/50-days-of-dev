"""Read-only tools for the SDD harness. Schemas auto-generated via @tool."""

from __future__ import annotations

import glob as _glob
import re
import subprocess
from pathlib import Path

from langchain_core.tools import tool

MAX_READ_BYTES = 200_000
MAX_HITS = 100


@tool
def read_file(path: str, max_bytes: int = MAX_READ_BYTES) -> str:
    """Read a text file's contents.

    :param path: Absolute or cwd-relative path
    :param max_bytes: Truncate the file after this many bytes
    """
    p = Path(path).expanduser()
    if not p.exists():
        return f"error: {path} not found"
    if not p.is_file():
        return f"error: {path} is not a file"
    data = p.read_bytes()[:max_bytes]
    text = data.decode("utf-8", errors="replace")
    if p.stat().st_size > max_bytes:
        text += f"\n... [truncated at {max_bytes} bytes]"
    return text


@tool
def glob_files(pattern: str, root: str = ".") -> str:
    """Find files by glob pattern (supports **).

    :param pattern: Glob pattern, e.g. "src/**/*.py"
    :param root: Directory to search from
    """
    base = Path(root).expanduser()
    hits = sorted(str(Path(p)) for p in _glob.glob(str(base / pattern), recursive=True))[:MAX_HITS]
    if not hits:
        return f"no matches for {pattern} under {root}"
    return "\n".join(hits)


@tool
def grep_content(pattern: str, path: str = ".", include: str = "*") -> str:
    """Search file contents for a regex pattern.

    :param pattern: Python regex
    :param path: Root file or directory
    :param include: Filename glob to restrict search (e.g. "*.py")
    """
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"error: bad regex: {e}"
    root = Path(path).expanduser()
    files = [root] if root.is_file() else list(root.rglob(include))
    hits: list[str] = []
    for f in files:
        if not f.is_file():
            continue
        try:
            for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{f}:{i}:{line.strip()[:200]}")
                    if len(hits) >= MAX_HITS:
                        return "\n".join(hits) + f"\n... [stopped at {MAX_HITS} hits]"
        except OSError:
            continue
    return "\n".join(hits) or f"no matches for {pattern!r}"


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web (DuckDuckGo) and return top results.

    :param query: Search query
    :param max_results: Number of results (max 10)
    """
    try:
        from ddgs import DDGS
    except ImportError:
        return "error: ddgs not installed"
    max_results = min(max(1, max_results), 10)
    results = list(DDGS().text(query, max_results=max_results))
    if not results:
        return "no results"
    return "\n\n".join(
        f"{r.get('title','')}\n{r.get('href','')}\n{r.get('body','')[:400]}" for r in results
    )


@tool
def openspec_cli(command_args: str) -> str:
    """Invoke the local `openspec` CLI. Read-only subcommands: list, show, status, validate.

    :param command_args: Args to pass to openspec, e.g. "list" or "show my-change"
    """
    # ponytail: whitelist read-only subcommands — no destructive ops from the model
    allowed = {"list", "show", "status", "validate", "instructions", "help"}
    parts = command_args.split()
    if not parts or parts[0] not in allowed:
        return f"error: only {sorted(allowed)} allowed"
    try:
        out = subprocess.run(
            ["openspec", *parts], capture_output=True, text=True, timeout=30
        )
        return (out.stdout + out.stderr).strip()[:20_000] or "(no output)"
    except FileNotFoundError:
        return "error: openspec CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return "error: openspec timed out"


ALL_TOOLS = [read_file, glob_files, grep_content, web_search, openspec_cli]
