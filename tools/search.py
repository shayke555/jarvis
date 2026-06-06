from __future__ import annotations

import asyncio
import logging

import httpx
from duckduckgo_search import DDGS

from config.settings import settings
from tools.registry import ToolResult

logger = logging.getLogger(__name__)

WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information, news, prices, or facts. "
            "Use when the user asks about something that may have changed recently."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in English or Hebrew",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (1-5). Default: 3",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
}


async def _tavily_search(query: str, max_results: int = 3) -> str:
    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post("https://api.tavily.com/search", json=payload)
        resp.raise_for_status()
        data = resp.json()

    lines = []
    if data.get("answer"):
        lines.append(f"📌 {data['answer']}")
    for r in data.get("results", []):
        lines.append(f"• {r['title']}: {r['content'][:200]}")
    return "\n".join(lines) if lines else "No results found."


async def _ddg_search(query: str, max_results: int = 3) -> str:
    def _sync() -> list[dict]:
        return list(DDGS().text(query, max_results=max_results))

    results = await asyncio.to_thread(_sync)
    if not results:
        return "No results found."
    return "\n".join(f"• {r['title']}: {r['body']}" for r in results)


async def _brave_search(query: str, max_results: int = 3) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": max_results},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": settings.brave_search_api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results = data.get("web", {}).get("results", [])
    if not results:
        return "No results found."
    return "\n".join(f"• {r['title']}: {r['description'][:200]}" for r in results)


async def web_search_tool(query: str, max_results: int = 3) -> ToolResult:
    """Tavily → DDG → Brave fallback chain."""
    engines: list[tuple[str, object]] = []
    if settings.tavily_api_key:
        engines.append(("Tavily", _tavily_search))
    engines.append(("DuckDuckGo", _ddg_search))
    if settings.brave_search_api_key:
        engines.append(("Brave", _brave_search))

    last_error = "No engines available"
    for name, func in engines:
        try:
            output = await func(query, max_results)
            logger.info("Search via %s: %s", name, query[:50])
            return ToolResult(tool_name="web_search", output=output, success=True)
        except Exception as e:
            logger.warning("%s failed: %s", name, e)
            last_error = str(e)

    return ToolResult(tool_name="web_search", output="", success=False, error=last_error)


def should_search(text: str) -> bool:
    triggers = ["חפש", "search", "מה זה", "מי זה", "what is", "who is", "find me"]
    return any(t in text.lower() for t in triggers)


async def search_web(query: str, max_results: int = 3) -> str:
    """Legacy wrapper — returns string, not ToolResult."""
    result = await web_search_tool(query, max_results)
    return result.output if result.success else "Search unavailable."
