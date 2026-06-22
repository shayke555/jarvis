from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import FastAPI
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from brain.agent_loop import AgentLoop
from brain.context_manager import ContextManager
from brain import task_brain
from config.settings import settings
from connectors.gmail_bridge import fetch_gmail_summary, format_gmail_section

logger = logging.getLogger(__name__)

_context_manager: ContextManager | None = None
_agent_loop: AgentLoop | None = None

# Approval gate: maps request_id → asyncio.Future[bool]
_pending_approvals: dict[str, asyncio.Future[bool]] = {}
_stop_event: asyncio.Event | None = None


def set_context_manager(cm: ContextManager) -> None:
    global _context_manager
    _context_manager = cm


def set_agent_loop(agent: AgentLoop) -> None:
    global _agent_loop
    _agent_loop = agent


async def request_approval(tool_name: str, args: dict) -> bool:
    """Send an inline-keyboard approve/reject prompt to the owner and await their response.

    Returns True if approved, False if rejected or timed out.
    Only callable when a Telegram update is in scope — used as on_approval_request
    callback passed into AgentLoop.run().
    """
    request_id = uuid.uuid4().hex  # 32 chars — eliminates collision risk
    loop = asyncio.get_running_loop()
    future: asyncio.Future[bool] = loop.create_future()
    _pending_approvals[request_id] = future

    # Format args for display — truncate long values
    args_preview = ", ".join(
        f"{k}={str(v)[:40]!r}" for k, v in list(args.items())[:3]
    )
    text = (
        f"⚠️ JARVIS רוצה להריץ כלי מסוכן:\n"
        f"🔧 `{tool_name}({args_preview})`\n\n"
        f"אשר את הפעולה?"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ אשר", callback_data=f"approve:{request_id}"),
            InlineKeyboardButton("❌ דחה", callback_data=f"reject:{request_id}"),
        ]
    ])

    try:
        bot = _get_bot()  # raises RuntimeError if called before run_telegram_bot() completes initialize()
        await bot.send_message(
            chat_id=settings.telegram_owner_chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        approved = await asyncio.wait_for(
            future,
            timeout=settings.approval_gate_timeout_seconds,
        )
        return approved
    except asyncio.TimeoutError:
        logger.warning("Approval gate timed out for %s — defaulting to reject", tool_name)
        return False
    except Exception as e:
        logger.error("Approval gate error for %s: %s", tool_name, e, exc_info=True)
        return False
    finally:
        _pending_approvals.pop(request_id, None)


async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Resolve a pending approval Future when the owner taps ✅ or ❌."""
    query = update.callback_query
    if query is None:
        return

    # Only the owner can approve/reject
    if str(query.from_user.id) != settings.telegram_owner_chat_id:
        await query.answer("Unauthorized")
        return

    data = query.data or ""
    if not (data.startswith("approve:") or data.startswith("reject:")):
        return

    action, request_id = data.split(":", 1)
    approved = action == "approve"

    future = _pending_approvals.get(request_id)
    if future and not future.done():
        future.set_result(approved)
        label = "✅ אושר" if approved else "❌ נדחה"
        original_text = (getattr(query.message, "text", "") or "") if query.message else ""
        await query.edit_message_text(f"{original_text}\n\n{label}".strip())
    else:
        await query.answer("הבקשה כבר טופלה או פגה תוקף.")

    await query.answer()


_bot_ref: Bot | None = None


def _set_bot(bot: Bot) -> None:
    global _bot_ref
    _bot_ref = bot


def _get_bot() -> Bot:
    if _bot_ref is None:
        raise RuntimeError("Bot not initialized — call _set_bot() first.")
    return _bot_ref


def _get_context_manager() -> ContextManager:
    if _context_manager is None:
        raise RuntimeError("ContextManager not initialized. Call set_context_manager() first.")
    return _context_manager


def _is_authorized(update: Update) -> bool:
    if update.effective_user is None:
        return False
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


async def handle_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return

    from connectors.cv_bridge import fetch_cv_status
    result = await asyncio.get_running_loop().run_in_executor(None, fetch_cv_status)

    if result["status"] == "error":
        await update.message.reply_text(f"❌ לא הצלחתי לטעון נתוני קריירה: {result['error']}")
        return

    data = result["data"]
    total = data.get("total", 0)
    apps = data.get("open_applications", [])
    pipeline = data.get("pipeline_summary", {})

    if total == 0:
        await update.message.reply_text("💼 אין מועמדויות פתוחות כרגע.")
        return

    lines = [f"💼 מועמדויות פתוחות ({total}):\n"]
    for app in apps[:10]:
        status = app.get("status", "?")
        company = app.get("company", "?")
        role = app.get("role", "?")
        date_applied = app.get("date_applied", "?")
        lines.append(f"  • {company} — {role} [{status}] ({date_applied})")

    if total > 10:
        lines.append(f"\n  ...ועוד {total - 10} נוספות")

    await update.message.reply_text("\n".join(lines))


async def handle_signals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return

    from connectors.ledger_bridge import fetch_ledger_signals
    result = await asyncio.get_running_loop().run_in_executor(None, fetch_ledger_signals)

    if result["status"] == "error":
        await update.message.reply_text(f"❌ LedgerAlpha לא זמין: {result['error']}")
        return

    data = result["data"]
    regime = data.get("regime", "unknown")
    top = data.get("top_signal")
    timestamp = data.get("timestamp", "")

    lines = [f"📈 LedgerAlpha Signals\n", f"🌡️ Regime: {regime}"]
    if timestamp:
        lines.append(f"🕐 עודכן: {timestamp}")

    if top:
        ticker = top.get("ticker", "?")
        score = top.get("score", "?")
        direction = top.get("direction", "?")
        lines.append(f"\n🏆 איתות מוביל:")
        lines.append(f"  {ticker} — {direction} (score: {score})")
    else:
        lines.append("\nאין איתותים זמינים כרגע.")

    await update.message.reply_text("\n".join(lines))


async def handle_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _reject_unauthorized(update, context)
        return

    if not settings.gmail_app_password or not settings.gmail_email:
        await update.message.reply_text(
            "📧 Gmail לא מוגדר.\n"
            "הוסף ל-.env:\n"
            "  GMAIL_EMAIL=your@gmail.com\n"
            "  GMAIL_APP_PASSWORD=your-app-password\n"
            "(Google App Password — לא הסיסמה הרגילה)"
        )
        return

    await update.message.reply_text("📧 סורק מיילים...")
    result = await asyncio.get_running_loop().run_in_executor(None, fetch_gmail_summary)

    if result["status"] == "error":
        await update.message.reply_text(f"❌ Gmail: {result['error']}")
        return

    data = result["data"]
    if not data:
        await update.message.reply_text("📧 אין מיילים חדשים.")
        return

    summary = format_gmail_section(data)
    await update.message.reply_text(summary)


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

        async def _approve(tool_name: str, args: dict) -> bool:
            return await request_approval(tool_name, args)

        response = await _agent_loop.run(
            messages=messages,
            on_tool_call=_notify,
            on_approval_request=_approve,
        )
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
    application.add_handler(CommandHandler("jobs", handle_jobs))
    application.add_handler(CommandHandler("signals", handle_signals))
    application.add_handler(CommandHandler("gmail", handle_gmail))
    application.add_handler(CallbackQueryHandler(handle_approval_callback, pattern="^(approve|reject):"))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await application.initialize()
    _set_bot(application.bot)
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
