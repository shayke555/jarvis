from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from brain.agent_loop import AgentLoop
from brain.context_manager import ContextManager
from brain import task_brain
from config.settings import settings

logger = logging.getLogger(__name__)

_context_manager: ContextManager | None = None
_agent_loop: AgentLoop | None = None
_stop_event: asyncio.Event | None = None


def set_context_manager(cm: ContextManager) -> None:
    global _context_manager
    _context_manager = cm


def set_agent_loop(agent: AgentLoop) -> None:
    global _agent_loop
    _agent_loop = agent


def _get_context_manager() -> ContextManager:
    if _context_manager is None:
        raise RuntimeError("ContextManager not initialized. Call set_context_manager() first.")
    return _context_manager


def _is_authorized(update: Update) -> bool:
    return str(update.effective_user.id) == settings.telegram_owner_chat_id


async def _reject_unauthorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Unauthorized")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else "unknown"
    logger.info("Received /start — user_id=%s", uid)
    if not _is_authorized(update):
        logger.warning("Unauthorized user: %s", uid)
        await _reject_unauthorized(update, context)
        return
    await update.message.reply_text("JARVIS online. Send a message.")


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return

    cm = _get_context_manager()
    status = cm.get_status()

    total_memories: int = status.get("total_memories", 0)
    open_tasks: list = status.get("open_tasks", [])
    recent_prefs: dict = status.get("recent_preferences", {})

    prefs_text = (
        "\n".join(f"  - {k}: {v}" for k, v in recent_prefs.items())
        if recent_prefs
        else "  (none)"
    )
    text = (
        f"JARVIS Status\n"
        f"Memory entries: {total_memories}\n"
        f"Open tasks: {len(open_tasks)}\n"
        f"Recent preferences:\n{prefs_text}"
    )
    await update.message.reply_text(text)


async def handle_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return
    await update.message.reply_text(
        "Morning briefing on demand — coming in Phase C (connectors not yet available). "
        "Use /status for now."
    )


async def handle_remember(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return

    raw: str = update.message.text or ""
    parts = raw.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await update.message.reply_text("Usage: /remember <text>")
        return

    fact = parts[1].strip()
    cm = _get_context_manager()
    cm.remember(fact)
    await update.message.reply_text(f"Stored: {fact}")


_SUMMARY_PROMPT = (
    "You are JARVIS helping Shay prepare for exams. Summarize the following course "
    "material in Hebrew: extract (1) key topics, (2) important definitions/concepts, "
    "and (3) 3-5 likely exam questions with short model answers. Be concise and structured.\n\n"
    "--- MATERIAL ---\n{text}\n--- END MATERIAL ---"
)


async def handle_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return

    raw: str = update.message.text or ""
    parts = raw.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await update.message.reply_text("Usage: /summarize <path to PDF/DOCX/TXT/MD>")
        return

    path = parts[1].strip()
    await update.message.reply_text(f"📖 קורא את {path}...")

    from tools.document_reader import read_document_tool
    doc_result = await read_document_tool(path=path)
    if not doc_result.success:
        await update.message.reply_text(f"❌ לא הצלחתי לקרוא את הקובץ: {doc_result.error}")
        return

    cm = _get_context_manager()
    try:
        summary = await cm.llm.chat(
            [{"role": "user", "content": _SUMMARY_PROMPT.format(text=doc_result.output)}],
            context_tokens=len(doc_result.output) // 4,
        )
    except Exception as e:
        logger.error("Summarization failed for %s: %s", path, e, exc_info=True)
        await update.message.reply_text("❌ שגיאה ביצירת הסיכום. נסה שוב.")
        return

    await update.message.reply_text(summary or "לא הצלחתי להפיק סיכום מהחומר הזה.")


async def handle_organize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return

    raw: str = update.message.text or ""
    parts = raw.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].strip():
        await update.message.reply_text(
            "Usage: /organize <folder> [by_type|by_date|by_keyword]\n"
            "(מצב dry-run בלבד — JARVIS עדיין לא יכול להזיז קבצים בפועל)"
        )
        return

    folder = parts[1].strip()
    strategy = parts[2].strip() if len(parts) > 2 and parts[2].strip() else "by_type"

    from tools.organizer import organize_files_tool
    result = await organize_files_tool(folder=folder, strategy=strategy)
    if not result.success:
        await update.message.reply_text(f"❌ {result.error}")
        return

    await update.message.reply_text(result.output)


def _route_task_command(text: str) -> str | None:
    """
    Detect task-related commands and handle directly (no LLM call).
    Returns reply string if handled, None to fall through to LLM.
    """
    lower = text.strip().lower()

    if any(p in lower for p in ["מה יש לי", "משימות", "tasks", "מה עכשיו"]):
        return task_brain.format_tasks_message()

    if lower.startswith("סיימתי ") or lower.startswith("done "):
        parts = text.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[1].strip().isdigit():
            task_id = int(parts[1].strip())
            result = task_brain.mark_done(task_id)
            if result["status"] == "ok":
                return f"✅ משימה {task_id} סומנה כבוצעת."
            return f"שגיאה: {result['error']}"

    if lower.startswith("הוסף ") and " ל-" in lower:
        rest = text[len("הוסף "):].strip()
        if " ל-" in rest:
            description, area = rest.rsplit(" ל-", 1)
            area = area.strip().lower()
            description = description.strip()
            result = task_brain.add_task(area, description)
            if result["status"] == "ok":
                return f"✅ נוסף: {description} [{area}]"
            return f"שגיאה: {result['error']}"

    return None


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return

    user_message: str = update.message.text or ""

    task_reply = _route_task_command(user_message)
    if task_reply is not None:
        await update.message.reply_text(task_reply)
        return

    cm = _get_context_manager()

    if _agent_loop is not None:
        messages = cm.build_messages(user_message)

        async def _notify(tool_info: str) -> None:
            await update.message.reply_text(tool_info)

        response = await _agent_loop.run(messages=messages, on_tool_call=_notify)
        cm.sqlite.add_message("telegram", "user", user_message)
        cm.sqlite.add_message("telegram", "assistant", response)
    else:
        response = await cm.chat(user_message, interface="telegram")

    await update.message.reply_text(response)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("No audio received.")
        return

    try:
        file = await context.bot.get_file(voice.file_id)
        ogg_bytes = bytes(await file.download_as_bytearray())

        from voice.stt import transcribe_ogg
        text = await transcribe_ogg(ogg_bytes)

        if not text.strip():
            await update.message.reply_text("לא הצלחתי לתמלל. נסה שוב.")
            return

        cm = _get_context_manager()
        response = await cm.chat(text, interface="telegram_voice")
        await update.message.reply_text(f"🎙 {text}\n\n{response}")

    except Exception as e:
        logger.error("Voice handler error: %s", e, exc_info=True)
        await update.message.reply_text("שגיאה בעיבוד הודעת הקול. נסה שוב.")


def setup_telegram(app: FastAPI, cm: ContextManager) -> None:
    set_context_manager(cm)
    app.state.context_manager = cm
    logger.info("Telegram setup complete.")


async def run_telegram_bot() -> None:
    global _stop_event
    _stop_event = asyncio.Event()

    application: Application = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .build()
    )

    async def _debug_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id if update.effective_user else "?"
        msg = update.message.text if update.message else "(no message)"
        logger.info("UPDATE RECEIVED — user_id=%s msg=%r", uid, msg[:80])

    application.add_handler(MessageHandler(filters.ALL, _debug_all), group=-1)
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("status", handle_status))
    application.add_handler(CommandHandler("brief", handle_brief))
    application.add_handler(CommandHandler("remember", handle_remember))
    application.add_handler(CommandHandler("summarize", handle_summarize))
    application.add_handler(CommandHandler("organize", handle_organize))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=False)
    logger.info("Telegram bot polling started.")

    try:
        await _stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Telegram bot stopped cleanly.")


async def stop_telegram_bot() -> None:
    if _stop_event:
        _stop_event.set()
