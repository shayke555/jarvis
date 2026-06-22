"""Project health monitor — scans context.md across all projects."""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

from config.settings import settings


@dataclass(frozen=True)
class ProjectStatus:
    name: str
    last_completed: str
    next_step: str
    staleness_days: int
    staleness_emoji: str


def _parse_section(text: str, section: str) -> str:
    """Extract first bullet from a ## section, or empty string."""
    pattern = rf"## {re.escape(section)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return ""
    block = match.group(1).strip()
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            return line[2:].strip()
        if line and not line.startswith("#"):
            return line
    return ""


def _staleness_emoji(days: int) -> str:
    if days <= 1:
        return "🟢"
    if days <= 3:
        return "🟡"
    return "🔴"


def scan_projects(projects_base: Path | None = None) -> list[ProjectStatus]:
    """Return health status for every project that has a context.md."""
    base = projects_base or Path(settings.projects_base_path)
    results: list[ProjectStatus] = []
    now = time.time()

    base_resolved = base.resolve()
    for ctx_path in sorted(base.glob("*/context.md")):
        # H2: reject symlinks that escape the projects root (NTFS junctions)
        if base_resolved not in ctx_path.resolve().parents:
            continue
        proj_name = ctx_path.parent.name
        mtime = ctx_path.stat().st_mtime  # stat before read — narrower TOCTOU window
        text = ctx_path.read_text(encoding="utf-8", errors="replace")
        days = int((now - mtime) / 86400)

        results.append(ProjectStatus(
            name=proj_name,
            last_completed=_parse_section(text, "Last Completed"),
            next_step=_parse_section(text, "Next Step"),
            staleness_days=days,
            staleness_emoji=_staleness_emoji(days),
        ))

    return sorted(results, key=lambda p: p.staleness_days, reverse=True)


def detect_stuck_projects(
    threshold_days: int = 5,
    projects_base: Path | None = None,
) -> list[dict]:
    """Return projects that are stale AND have known pending work.

    A project is "stuck" when context.md hasn't been touched for threshold_days
    AND its Next Step section is non-empty. Cross-references task_brain for
    urgent/high tasks when available.

    Returns list of {project, days_stale, next_step, urgent_tasks}.
    """
    from brain import task_brain

    statuses = scan_projects(projects_base)
    stuck = []

    for p in statuses:
        if p.staleness_days < threshold_days:
            continue
        if not p.next_step:
            continue

        try:
            all_tasks = task_brain.get_tasks()
            project_tasks = [
                t for t in all_tasks
                if t.get("area", "").lower() in p.name.lower()
                and t.get("status", "") != "done"
                and t.get("priority", "").lower() in ("high", "urgent", "critical")
            ]
        except Exception as e:
            logger.warning("task_brain unavailable for %s: %s", p.name, e)
            project_tasks = []

        stuck.append({
            "project": p.name,
            "days_stale": p.staleness_days,
            "next_step": p.next_step,
            "urgent_tasks": project_tasks,
        })

    return stuck


def format_project_health(projects_base: Path | None = None) -> str:
    """Format project health for Telegram — compact, emoji-coded."""
    statuses = scan_projects(projects_base)
    if not statuses:
        return "🧠 PROJECT STATUS\n  (no projects found)"

    lines = ["🧠 PROJECT STATUS"]
    for p in statuses:
        age = f"היום" if p.staleness_days == 0 else f"{p.staleness_days} ימים"
        if p.staleness_days == 1:
            age = "אתמול"
        header = f"  {p.staleness_emoji} {p.name} ({age})"
        lines.append(header)
        if p.last_completed:
            lines.append(f"    ✅ {p.last_completed}")
        if p.next_step:
            lines.append(f"    ▶️ {p.next_step}")
        if p.staleness_days >= 4:
            lines.append(f"    ⚠️ לא עודכן {p.staleness_days} ימים")

    return "\n".join(lines)
