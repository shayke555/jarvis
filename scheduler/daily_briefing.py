import logging

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from brain.context_manager import ContextManager
from brain import task_brain
from connectors import registry
from config.settings import settings

logger = logging.getLogger(__name__)

_context_manager: ContextManager | None = None


def set_context_manager(cm: ContextManager) -> None:
    global _context_manager
    _context_manager = cm


async def send_telegram_message(text: str) -> None:
    # H1: token never logged — kept in variable, not in any logged string
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": settings.telegram_shay_chat_id, "text": text}
    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            if not resp.is_success:
                logger.error("Telegram delivery failed %s", resp.status_code)
    except Exception as e:
        logger.error("Telegram send failed: %s", e)


def _build_tasks_section() -> str:
    return task_brain.format_tasks_message()


def _build_ledger_section() -> str:
    result = registry.execute("ledger")
    if result["status"] == "error":
        return "📈 LEDGERALPHA: unavailable"
    d = result["data"]
    regime = d.get("regime", "unknown")
    top = d.get("top_signal")
    signal_line = (
        f"{top.get('ticker', '?')} {top.get('score', '?')} {top.get('direction', '?')}"
        if top
        else "no signals"
    )
    return f"📈 LEDGERALPHA\n  • Regime: {regime}\n  • Top signal: {signal_line}"


def _build_projects_section() -> str:
    result = task_brain.get_tasks(area="projects")
    lines = ["🧠 PROJECTS"]
    if result["status"] == "ok" and result["data"]["tasks"]:
        for t in result["data"]["tasks"][:3]:
            due = f" — {t['due_date']}" if t.get("due_date") else ""
            lines.append(f"  • {t['description']}{due}")
    else:
        lines.append("  • (no open project tasks)")
    return "\n".join(lines)


def _build_gmail_section() -> str:
    from connectors.gmail_bridge import format_gmail_section
    result = registry.execute("gmail")
    if result["status"] == "error":
        return ""  # silent skip — no Gmail creds or IMAP failure
    return format_gmail_section(result["data"])


def _build_project_health_section() -> str:
    from monitors.project_health import format_project_health
    return format_project_health()


async def build_briefing() -> str:
    tasks_section = _build_tasks_section()
    ledger_section = _build_ledger_section()
    projects_section = _build_projects_section()
    try:
        health_section = _build_project_health_section()
    except Exception as e:
        logger.error("Project health section failed: %s", e)
        health_section = ""
    try:
        gmail_section = _build_gmail_section()
    except Exception as e:
        logger.error("Gmail section failed: %s", e)
        gmail_section = ""

    parts = [
        "🌅 בוקר שי.\n",
        tasks_section,
        ledger_section,
    ]
    if gmail_section:
        parts.append(gmail_section)
    if health_section:
        parts.append(health_section)
    parts.append(projects_section)
    return "\n\n".join(parts)


async def morning_briefing_job() -> None:
    logger.info("Running morning briefing job")
    briefing = await build_briefing()
    await send_telegram_message(briefing)


def create_scheduler(cm: ContextManager) -> AsyncIOScheduler:
    set_context_manager(cm)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        morning_briefing_job,
        "cron",
        hour=settings.briefing_hour,
        minute=settings.briefing_minute,
        id="morning_briefing",
    )
    return scheduler
