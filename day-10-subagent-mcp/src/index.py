"""Entry point that runs the subagent MCP server over stdio."""

from server import mcp


if __name__ == "__main__":
    mcp.run(transport="stdio")
