"""Weekly learning digest — Sunday 08:00. GitHub trending + growth-loop recap."""
from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

from monitors.github_trending import fetch_trending, format_trending_digest
from scheduler.daily_briefing import send_telegram_message

logger = logging.getLogger(__name__)

GROWTH_LOG = Path.home() / ".claude/skills/growth-loop/log.md"


def _read_recent_growth(n: int = 3, log_path: Path | None = None) -> str:
    """Parse last N dated entries from growth-loop log.md."""
    path = log_path or GROWTH_LOG
    if not path.exists():
        return "(growth log not found)"

    text = path.read_text(encoding="utf-8", errors="replace")
    # Split on ## YYYY-MM-DD headers
    entries = re.split(r"(?=^## \d{4}-\d{2}-\d{2})", text, flags=re.MULTILINE)
    dated = [e.strip() for e in entries if re.match(r"^## \d{4}-\d{2}-\d{2}", e.strip())]

    if not dated:
        return "(no growth entries found)"

    recent = list(reversed(dated[-n:]))
    lines = ["📖 מה למדת השבוע:"]
    for entry in recent:
        # First line is the ## DATE — PROJECT header
        header_line = entry.splitlines()[0].lstrip("# ").strip()
        lines.append(f"  • {header_line}")

    return "\n".join(lines)


async def weekly_learning_job() -> None:
    """Sunday 08:00 — send weekly learning digest to Telegram."""
    logger.info("Running weekly learning job")
    try:
        repos = await fetch_trending(days_back=7)
        trending_text = format_trending_digest(repos)
    except Exception as e:
        logger.error("GitHub trending failed: %s", e)
        trending_text = "🔥 GitHub this week: (unavailable)"

    try:
        growth_text = _read_recent_growth(3)
    except Exception as e:
        logger.error("Growth log read failed: %s", e)
        growth_text = "(growth log unavailable)"

    msg = f"📚 שבועי — למידה + ריפוס\n\n{trending_text}\n\n{growth_text}"
    await send_telegram_message(msg)

    # Refresh knowledge graph with any code changes from the past week
    _run_graphify_update()


def _run_graphify_update() -> None:
    """Run `graphify . --update --no-viz` to sync graph with latest code changes."""
    jarvis_root = Path(__file__).parent.parent
    proc = None
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "graphify.cli", ".", "--update", "--no-viz"],
            cwd=jarvis_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(timeout=120)
        if proc.returncode == 0:
            logger.info("graphify --update completed: %s", stdout.strip()[-200:])
        else:
            logger.warning("graphify --update exited %d: %s", proc.returncode, stderr[:300])
    except FileNotFoundError:
        logger.warning("graphify CLI not found — skipping graph update")
    except subprocess.TimeoutExpired:
        if proc is not None:
            proc.kill()
            proc.communicate()
        logger.warning("graphify --update timed out after 120s — process killed")
