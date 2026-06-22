"""Phase 4 — Proactive nudge: sends a Telegram alert when a project is stuck.

Runs once per day via APScheduler (registered in bot.py alongside daily_briefing).
Daily cap: max 1 nudge per day — stored in SQLite preferences as 'last_nudge_date'.
Uses memory blocks (human_block) for personalized context.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Callable, Coroutine, Any

from brain.context_manager import ContextManager

logger = logging.getLogger(__name__)

_NUDGE_DATE_KEY = "last_nudge_date"
SendFn = Callable[[str], Coroutine[Any, Any, None]]


async def proactive_nudge_job(cm: ContextManager, send_fn: SendFn) -> None:
    """Check for stuck projects and send one nudge if threshold crossed today.

    Skips silently if:
    - A nudge was already sent today (daily cap)
    - No projects are stuck
    - Any error occurs (never crashes the scheduler)
    """
    try:
        from monitors.project_health import detect_stuck_projects
        stuck = detect_stuck_projects(threshold_days=5)
        if not stuck:
            return

        today = date.today().isoformat()
        last_nudge = cm.sqlite.get_preference(_NUDGE_DATE_KEY)
        if last_nudge == today:
            logger.debug("Nudge already sent today — skipping")
            return

        message = _build_nudge_message(cm, stuck)
        await send_fn(message)
        cm.sqlite.set_preference(_NUDGE_DATE_KEY, today)
        logger.info("Proactive nudge sent: %d stuck projects", len(stuck))
    except Exception as e:
        logger.error("proactive_nudge_job failed (non-fatal): %s", e, exc_info=True)


def _build_nudge_message(cm: ContextManager, stuck: list[dict]) -> str:
    lines = ["🔔 JARVIS — עדכון יזום\n"]

    for item in stuck[:3]:  # cap at 3 to avoid message spam
        project = item["project"]
        days = item["days_stale"]
        next_step = item["next_step"]
        urgent = item.get("urgent_tasks", [])

        lines.append(f"🔴 {project} — לא עודכן {days} ימים")
        lines.append(f"   ▶️ הבא: {next_step}")
        if urgent:
            lines.append(f"   ⚡ {len(urgent)} משימות דחופות פתוחות")

    if len(stuck) > 3:
        lines.append(f"\n...ועוד {len(stuck) - 3} פרויקטים תקועים נוספים")

    lines.append("\nרוצה להמשיך עכשיו? שלח הודעה ל-JARVIS.")
    return "\n".join(lines)
