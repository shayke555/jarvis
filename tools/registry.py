from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

ToolFunc = Callable[..., Coroutine[Any, Any, "ToolResult"]]


@dataclass
class ToolResult:
    tool_name: str
    output: str
    success: bool
    error: str | None = None


class ToolRegistry:
    """Single source of truth for all JARVIS agent tools.

    Each tool has a Groq-compatible function schema + async implementation.
    Tools are registered lazily so the registry can be imported before all
    tool modules exist.
    """

    def __init__(self) -> None:
        self._tools: dict[str, tuple[dict, ToolFunc]] = {}
        self._register_defaults()

    def register(self, schema: dict, func: ToolFunc) -> None:
        name = schema["function"]["name"]
        self._tools[name] = (schema, func)
        logger.debug("Registered tool: %s", name)

    def get_groq_tools(self) -> list[dict]:
        return [schema for schema, _ in self._tools.values()]

    async def execute(self, tool_name: str, args: dict) -> ToolResult:
        if tool_name not in self._tools:
            return ToolResult(
                tool_name=tool_name,
                output="",
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
        _, func = self._tools[tool_name]
        try:
            return await func(**args)
        except Exception as e:
            logger.error("Tool %s raised: %s", tool_name, e)
            return ToolResult(tool_name=tool_name, output="", success=False, error=str(e))

    def _register_defaults(self) -> None:
        """Import and register built-in tools. Each import is guarded so
        the registry stays importable even before tool files are created."""
        try:
            from tools.search import web_search_tool, WEB_SEARCH_SCHEMA
            self.register(WEB_SEARCH_SCHEMA, web_search_tool)
        except ImportError:
            logger.debug("tools.search not ready — skipping")

        try:
            from tools.files import read_file_tool, READ_FILE_SCHEMA
            from tools.files import list_dir_tool, LIST_DIR_SCHEMA
            from tools.files import write_file_tool, WRITE_FILE_SCHEMA
            self.register(READ_FILE_SCHEMA, read_file_tool)
            self.register(LIST_DIR_SCHEMA, list_dir_tool)
            self.register(WRITE_FILE_SCHEMA, write_file_tool)
        except ImportError:
            logger.debug("tools.files not ready — skipping")

        try:
            from tools.code_runner import run_python_tool, RUN_PYTHON_SCHEMA
            self.register(RUN_PYTHON_SCHEMA, run_python_tool)
        except ImportError:
            logger.debug("tools.code_runner not ready — skipping")

        try:
            from tools.browser import browse_url_tool, BROWSE_URL_SCHEMA
            self.register(BROWSE_URL_SCHEMA, browse_url_tool)
        except ImportError:
            logger.debug("tools.browser not ready — skipping")

        try:
            from tools.semantic_search import semantic_search_tool, EXA_SEARCH_SCHEMA
            self.register(EXA_SEARCH_SCHEMA, semantic_search_tool)
        except ImportError:
            logger.debug("tools.semantic_search not ready — skipping")

        try:
            from tools.n8n_trigger import trigger_workflow_tool, N8N_TRIGGER_SCHEMA
            self.register(N8N_TRIGGER_SCHEMA, trigger_workflow_tool)
        except ImportError:
            logger.debug("tools.n8n_trigger not ready — skipping")

        try:
            from tools.graph_query import graph_query_tool, GRAPH_QUERY_SCHEMA
            self.register(GRAPH_QUERY_SCHEMA, graph_query_tool)
        except ImportError:
            logger.debug("tools.graph_query not ready — skipping")
