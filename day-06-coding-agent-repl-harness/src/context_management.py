"""Token counting and message trimming for the agent's context window."""

from typing import List, Tuple

from langchain_core.messages import BaseMessage, trim_messages

MAX_CONTEXT_TOKENS = 24_000  # qwen3:14b has a 32k window; leaves ~8k for the response


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken, falling back to character-based estimation.

    :param text: Text to count
    :return: Approximate token count
    """
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4


def _msg_tokens(msg: BaseMessage) -> int:
    content = getattr(msg, "content", "") or ""
    if not isinstance(content, str):
        content = str(content)
    return count_tokens(content)


def truncate_messages(
    messages: List[BaseMessage],
    max_tokens: int = MAX_CONTEXT_TOKENS,
) -> Tuple[List[BaseMessage], bool]:
    """Trim oldest messages so total tokens fit under `max_tokens`.

    Delegates to `langchain_core.messages.trim_messages` for linear-time
    trimming and tool-call boundary safety.

    :param messages: Full message list
    :param max_tokens: Maximum context tokens
    :return: (trimmed messages, was_truncated)
    """
    trimmed = trim_messages(
        messages,
        max_tokens=max_tokens,
        token_counter=_msg_tokens,
        strategy="last",
        include_system=True,
        start_on="human",
        allow_partial=False,
    )
    return trimmed, len(trimmed) < len(messages)
