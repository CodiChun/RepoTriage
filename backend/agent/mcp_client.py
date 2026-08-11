"""GitHub MCP client for RepoTriage."""

import asyncio
from functools import lru_cache
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from config import GITHUB_TOKEN

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/readonly"


def _build_client() -> MultiServerMCPClient:
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN is not set")

    return MultiServerMCPClient(
        {
            "github": {
                "transport": "http",
                "url": GITHUB_MCP_URL,
                "headers": {
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "X-MCP-Toolsets": "repos,issues,search",
                    "X-MCP-Readonly": "true",
                },
            }
        }
    )


async def get_github_mcp_tools_async():
    client = _build_client()
    return await client.get_tools()


def get_github_mcp_tools():
    """Sync wrapper — LangGraph nodes 目前是 sync 的."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(get_github_mcp_tools_async())
    raise RuntimeError(
        "get_github_mcp_tools() cannot be called from async code. "
        "Use `await get_github_mcp_tools_async()` instead."
    )


async def call_github_tool(tool_name: str, args: dict[str, Any]) -> str:
    """直接呼叫單一 MCP tool（不經 ReAct agent）."""
    tools = await get_github_mcp_tools_async()
    tool_map = {t.name: t for t in tools}

    if tool_name not in tool_map:
        available = ", ".join(sorted(tool_map.keys()))
        raise ValueError(f"Tool '{tool_name}' not found. Available: {available}")

    result = await tool_map[tool_name].ainvoke(args)
    return str(result)


def call_github_tool_sync(tool_name: str, args: dict[str, Any]) -> str:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(call_github_tool(tool_name, args))
    raise RuntimeError(
        "call_github_tool_sync() cannot be called from async code. "
        "Use `await call_github_tool()` instead."
    )