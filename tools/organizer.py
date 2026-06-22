"""Phase 6 — proposes a file-organization plan for a local folder.

DRY-RUN ONLY for now: produces a proposed rename/move plan and never touches
the filesystem. Filesystem mutation rides on Phase 2's approval gate
(_RISKY_TOOLS in agents/agent_loop.py) once that lands — until then this tool
is intentionally read-only-by-design, matching CLAUDE.md's "no silent
failures" + "surgical changes only" rules (we don't ship a half-built
mutation path).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from tools.path_guard import safe_path
from tools.registry import ToolResult

logger = logging.getLogger(__name__)

_VALID_STRATEGIES = {"by_type", "by_date", "by_keyword"}
_MAX_FILES_SCANNED = 500

ORGANIZE_FILES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "organize_files",
        "description": (
            "Propose a plan for organizing files in a local folder — groups by type, "
            "modification date, or filename keyword. DRY-RUN ONLY: returns a proposed "
            "plan of moves, does not touch the filesystem. Use when asked to organize, "
            "tidy up, sort, or clean up a folder of documents/downloads/notes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Path to the folder to organize"},
                "strategy": {
                    "type": "string",
                    "enum": sorted(_VALID_STRATEGIES),
                    "description": "How to group files (default: by_type)",
                    "default": "by_type",
                },
            },
            "required": ["folder"],
        },
    },
}


def _group_key(path: Path, strategy: str) -> str:
    if strategy == "by_type":
        suffix = path.suffix.lower().lstrip(".")
        return suffix or "no_extension"
    if strategy == "by_date":
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return mtime.strftime("%Y-%m")
    if strategy == "by_keyword":
        # First whitespace/underscore/dash-delimited token of the stem, lowercased
        stem = path.stem.lower()
        for sep in (" ", "_", "-"):
            if sep in stem:
                return stem.split(sep)[0]
        return stem
    raise ValueError(f"Unknown strategy: {strategy}")


def build_plan(folder: Path, strategy: str) -> dict[str, list[str]]:
    """Scan `folder` (non-recursive) and group files by `strategy`.

    Returns {target_subfolder_name: [filenames]}. Raises ValueError on bad strategy —
    callers translate that into a ToolResult error (mirrors document_reader.extract_text).
    """
    if strategy not in _VALID_STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy} (supported: {sorted(_VALID_STRATEGIES)})")

    plan: dict[str, list[str]] = defaultdict(list)
    files = [p for p in folder.iterdir() if p.is_file()]
    for path in files[:_MAX_FILES_SCANNED]:
        plan[_group_key(path, strategy)].append(path.name)
    return dict(plan)


def _format_plan(folder: Path, strategy: str, plan: dict[str, list[str]], total_files: int = 0) -> str:
    if not plan:
        return f"[{folder}] No files found to organize (strategy: {strategy})."

    lines = [
        f"📋 Proposed organization plan for {folder} (strategy: {strategy}) — DRY RUN, nothing moved yet:",
        "",
    ]
    if total_files > _MAX_FILES_SCANNED:
        lines.append(
            f"⚠️ Folder has {total_files} files — only scanned the first {_MAX_FILES_SCANNED}. "
            f"Plan below is INCOMPLETE; {total_files - _MAX_FILES_SCANNED} files are not represented."
        )
        lines.append("")
    for group, filenames in sorted(plan.items()):
        lines.append(f"  📁 {group}/  ({len(filenames)} file{'s' if len(filenames) != 1 else ''})")
        for name in filenames[:10]:
            lines.append(f"      - {name} → {group}/{name}")
        if len(filenames) > 10:
            lines.append(f"      ... and {len(filenames) - 10} more")
    lines.append("")
    lines.append(
        "⚠️ This is a proposal only — JARVIS cannot move files yet (approval gate not built). "
        "Review the plan; nothing on disk has changed."
    )
    return "\n".join(lines)


async def organize_files_tool(folder: str, strategy: str = "by_type") -> ToolResult:
    try:
        if strategy not in _VALID_STRATEGIES:
            return ToolResult(tool_name="organize_files", output="", success=False,
                              error=f"Unknown strategy: {strategy} (supported: {sorted(_VALID_STRATEGIES)})")

        p = safe_path(folder)
        if p is None:
            return ToolResult(tool_name="organize_files", output="", success=False,
                              error="Path rejected: outside allowed directory or contains traversal.")
        if not p.exists():
            return ToolResult(tool_name="organize_files", output="", success=False,
                              error=f"Folder not found: {folder}")
        if not p.is_dir():
            return ToolResult(tool_name="organize_files", output="", success=False,
                              error=f"Not a directory: {folder}")

        total_files = sum(1 for entry in p.iterdir() if entry.is_file())
        plan = build_plan(p, strategy)
        return ToolResult(tool_name="organize_files",
                          output=_format_plan(p, strategy, plan, total_files=total_files), success=True)
    except Exception as e:
        logger.error("organize_files failed for %s: %s", folder, e, exc_info=True)
        return ToolResult(tool_name="organize_files", output="", success=False,
                          error=f"Failed to build organization plan for {folder} (see logs for details).")
