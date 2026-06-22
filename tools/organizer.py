"""Phase 6 — file organization: plan (dry-run) + execute (behind approval gate).

Two tools:
  organize_files            — plan only, read-only, safe to call freely
  execute_file_organization — executes the plan (moves files), RISKY, requires approval
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
        "⚠️ Dry-run — nothing moved yet. "
        "To execute: ask JARVIS to run execute_file_organization with the same folder and strategy."
    )
    return "\n".join(lines)


EXECUTE_FILE_ORGANIZATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_file_organization",
        "description": (
            "Execute a file organization plan — ACTUALLY MOVES files into subfolders. "
            "Always run organize_files first to show the user the plan, then use this tool "
            "only when the user explicitly confirms they want to proceed. Requires approval."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Path to the folder to organize"},
                "strategy": {
                    "type": "string",
                    "enum": sorted(_VALID_STRATEGIES),
                    "description": "How to group files (must match the plan shown to user)",
                    "default": "by_type",
                },
            },
            "required": ["folder"],
        },
    },
}


def execute_plan(folder: Path, plan: dict[str, list[str]]) -> dict[str, list[str]]:
    """Execute the plan: move each file into its target subfolder.

    Returns {group: [moved_filenames]} for successes and logs errors per file.
    Never deletes files — only moves. Creates target subdirectories as needed.
    """
    results: dict[str, list[str]] = {}
    for group, filenames in plan.items():
        target_dir = folder / group
        target_dir.mkdir(exist_ok=True)
        moved = []
        for name in filenames:
            src = folder / name
            dst = target_dir / name
            try:
                if not src.exists():
                    logger.warning("execute_plan: source missing, skipping: %s", src)
                    continue
                if dst.exists():
                    logger.warning("execute_plan: destination exists, skipping: %s", dst)
                    continue
                # Guard against path traversal via crafted group/filename
                if not dst.resolve().is_relative_to(folder.resolve()):
                    logger.error("execute_plan: dst escapes folder — skipping: %s", dst)
                    continue
                src.rename(dst)
                moved.append(name)
            except Exception as e:
                logger.error("execute_plan: failed to move %s → %s: %s", src, dst, e)
        if moved:
            results[group] = moved
    return results


async def execute_file_organization_tool(folder: str, strategy: str = "by_type") -> ToolResult:
    try:
        if strategy not in _VALID_STRATEGIES:
            return ToolResult(tool_name="execute_file_organization", output="", success=False,
                              error=f"Unknown strategy: {strategy}")

        p = safe_path(folder)
        if p is None:
            return ToolResult(tool_name="execute_file_organization", output="", success=False,
                              error="Path rejected: outside allowed directory or contains traversal.")
        if not p.exists() or not p.is_dir():
            return ToolResult(tool_name="execute_file_organization", output="", success=False,
                              error=f"Folder not found: {folder}")

        plan = build_plan(p, strategy)
        if not plan:
            return ToolResult(tool_name="execute_file_organization",
                              output="No files to organize.", success=True)

        results = execute_plan(p, plan)
        total_moved = sum(len(v) for v in results.items())
        lines = [f"✅ Organization complete for {folder} (strategy: {strategy})", ""]
        for group, moved in sorted(results.items()):
            lines.append(f"  📁 {group}/  — {len(moved)} file(s) moved")
        lines.append(f"\nTotal moved: {sum(len(v) for v in results.values())} file(s)")
        return ToolResult(tool_name="execute_file_organization",
                          output="\n".join(lines), success=True)
    except Exception as e:
        logger.error("execute_file_organization failed for %s: %s", folder, e, exc_info=True)
        return ToolResult(tool_name="execute_file_organization", output="", success=False,
                          error=f"Organization failed for {folder} (see logs for details).")


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
