import asyncio
import tempfile
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query


async def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        options = ClaudeAgentOptions(
            cwd=directory,
            allowed_tools=["Bash", "Read"],
            max_turns=5,
        )
        async for message in query(
            prompt="Run `ls` in the current temporary directory, then report that the query completed.",
            options=options,
        ):
            if isinstance(message, ResultMessage):
                print("SDK query completed")
                print(f"error={message.is_error}")
                print(f"turns={message.num_turns}")
                return
    print("SDK query ended without a result message")


if __name__ == "__main__":
    asyncio.run(main())
