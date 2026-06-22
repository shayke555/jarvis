from __future__ import annotations

import logging
from pathlib import Path

from tools.path_guard import safe_path as _safe_path
from tools.registry import ToolResult

logger = logging.getLogger(__name__)

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "Read the contents of a local file. "
            "Use when asked to read, analyze, or summarize a document or code file."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path"},
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return (default 4000)",
                    "default": 4000,
                },
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a local file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write to"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
}

LIST_DIR_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_dir",
        "description": "List files and directories at a given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list"},
            },
            "required": ["path"],
        },
    },
}


async def read_file_tool(path: str, max_chars: int = 4000) -> ToolResult:
    try:
        p = _safe_path(path)
        if p is None:
            return ToolResult(tool_name="read_file", output="", success=False,
                              error="Path rejected: outside allowed directory or contains traversal.")
        if not p.exists():
            return ToolResult(tool_name="read_file", output="", success=False,
                              error=f"File not found: {path}")
        content = p.read_text(encoding="utf-8", errors="replace")[:max_chars]
        return ToolResult(tool_name="read_file", output=f"[{path}]\n{content}", success=True)
    except Exception as e:
        return ToolResult(tool_name="read_file", output="", success=False, error=str(e))


async def write_file_tool(path: str, content: str) -> ToolResult:
    try:
        p = _safe_path(path)
        if p is None:
            return ToolResult(tool_name="write_file", output="", success=False,
                              error="Path rejected: outside allowed directory or contains traversal.")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(tool_name="write_file", output=f"Written {len(content)} chars to {path}",
                          success=True)
    except Exception as e:
        return ToolResult(tool_name="write_file", output="", success=False, error=str(e))


async def list_dir_tool(path: str) -> ToolResult:
    try:
        p = Path(path)
        if not p.is_dir():
            return ToolResult(
                tool_name="list_dir", output="", success=False,
                error=f"Not a directory: {path}",
            )
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
        lines = [f"{'📁' if e.is_dir() else '📄'} {e.name}" for e in entries[:50]]
        return ToolResult(tool_name="list_dir", output="\n".join(lines), success=True)
    except Exception as e:
        return ToolResult(tool_name="list_dir", output="", success=False, error=str(e))
