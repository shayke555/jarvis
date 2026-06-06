from __future__ import annotations

import logging
import re

from tools.registry import ToolResult

logger = logging.getLogger(__name__)

BROWSE_URL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "browse_url",
        "description": (
            "Open a URL in a headless browser and return the page text. "
            "Use when you need to read a specific webpage or article. "
            "Better than web_search when you already have the URL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL (must start with http:// or https://)",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters of page text to return (default: 3000)",
                    "default": 3000,
                },
            },
            "required": ["url"],
        },
    },
}

_URL_RE = re.compile(r"^https?://")


async def _fetch_page_text(url: str, max_chars: int = 3000) -> str:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            await page.evaluate(
                "document.querySelectorAll('script,style,nav,header,footer,aside,iframe')"
                ".forEach(e => e.remove())"
            )
            text = await page.inner_text("body")
            return " ".join(text.split())[:max_chars]
        finally:
            await browser.close()


async def browse_url_tool(url: str, max_chars: int = 3000) -> ToolResult:
    if not _URL_RE.match(url):
        return ToolResult(
            tool_name="browse_url", output="", success=False,
            error="Invalid URL: must start with http:// or https://",
        )
    try:
        text = await _fetch_page_text(url, max_chars)
        return ToolResult(tool_name="browse_url", output=f"[{url}]\n{text}", success=True)
    except Exception as e:
        logger.error("browse_url failed for %s: %s", url, e)
        return ToolResult(tool_name="browse_url", output="", success=False, error=str(e))
