"""Verify GitHub MCP connection before integrating into the graph."""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from agent.mcp_client import call_github_tool, get_github_mcp_tools_async
from config import GITHUB_REPO


async def main():
    # 1. 列出可用 tools
    tools = await get_github_mcp_tools_async()
    print(f"Loaded {len(tools)} GitHub MCP tools:")
    for t in tools:
        print(f"  - {t.name}: {t.description[:80]}...")

    owner, repo = GITHUB_REPO.split("/")

    # 2. 測 search_code
    print("\n--- search_code ---")
    code_result = await call_github_tool(
        "search_code",
        {
            "query": f"repo:{owner}/{repo} login",
            "perPage": 3,
        },
    )
    print(code_result[:500])

    # 3. 測 search_issues
    print("\n--- search_issues ---")
    issues_result = await call_github_tool(
        "search_issues",
        {
            "query": f"repo:{owner}/{repo} is:issue login",
            "perPage": 3,
        },
    )
    print(issues_result[:500])


if __name__ == "__main__":
    asyncio.run(main())