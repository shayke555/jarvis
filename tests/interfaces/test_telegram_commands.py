"""Tests for the Phase 6 Telegram commands /summarize and /organize.

Mirrors the project's existing mocking style (MagicMock/AsyncMock for
ContextManager + Update), avoiding any real Telegram/network/LLM calls.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tools.registry import ToolResult

import interfaces.telegram_bot as telegram_bot
from interfaces.telegram_bot import handle_summarize, handle_organize, set_context_manager


OWNER_ID = "12345"


def _make_update(text: str, user_id: str = OWNER_ID):
    update = MagicMock()
    update.effective_user.id = int(user_id)
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture(autouse=True)
def _patch_authorized():
    with patch("interfaces.telegram_bot.settings") as mock_settings:
        mock_settings.telegram_owner_chat_id = OWNER_ID
        yield mock_settings


@pytest.fixture
def cm():
    mock_cm = MagicMock()
    mock_cm.llm.chat = AsyncMock(return_value="📌 נושאים: אלגוריתמים\n❓ שאלה לדוגמה: מה זה מיון מהיר?")
    set_context_manager(mock_cm)
    yield mock_cm
    set_context_manager(None)


# --- /summarize ---------------------------------------------------------

@pytest.mark.asyncio
async def test_summarize_rejects_unauthorized_user():
    update = _make_update("/summarize notes.pdf", user_id="99999")
    await handle_summarize(update, MagicMock())
    update.message.reply_text.assert_called_once_with("Unauthorized")


@pytest.mark.asyncio
async def test_summarize_requires_path_argument(cm):
    update = _make_update("/summarize")
    await handle_summarize(update, MagicMock())
    update.message.reply_text.assert_called_once()
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_summarize_reports_extraction_failure(cm):
    update = _make_update("/summarize missing.pdf")
    bad_result = ToolResult(tool_name="read_document", output="", success=False, error="File not found: missing.pdf")
    with patch("tools.document_reader.read_document_tool", new_callable=AsyncMock, return_value=bad_result):
        await handle_summarize(update, MagicMock())

    final_call = update.message.reply_text.call_args_list[-1][0][0]
    assert "לא הצלחתי לקרוא" in final_call
    assert "File not found" in final_call
    cm.llm.chat.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_success_calls_llm_and_replies_with_summary(cm):
    update = _make_update("/summarize lecture.pdf")
    good_result = ToolResult(tool_name="read_document", output="[lecture.pdf]\nLecture on sorting algorithms", success=True)
    with patch("tools.document_reader.read_document_tool", new_callable=AsyncMock, return_value=good_result):
        await handle_summarize(update, MagicMock())

    cm.llm.chat.assert_called_once()
    prompt = cm.llm.chat.call_args[0][0][0]["content"]
    assert "Lecture on sorting algorithms" in prompt

    final_call = update.message.reply_text.call_args_list[-1][0][0]
    assert "אלגוריתמים" in final_call


@pytest.mark.asyncio
async def test_summarize_handles_llm_failure_gracefully(cm):
    update = _make_update("/summarize lecture.pdf")
    good_result = ToolResult(tool_name="read_document", output="[lecture.pdf]\ntext", success=True)
    cm.llm.chat = AsyncMock(side_effect=Exception("groq down"))
    with patch("tools.document_reader.read_document_tool", new_callable=AsyncMock, return_value=good_result):
        await handle_summarize(update, MagicMock())

    final_call = update.message.reply_text.call_args_list[-1][0][0]
    assert "שגיאה" in final_call


# --- /organize -----------------------------------------------------------

@pytest.mark.asyncio
async def test_organize_rejects_unauthorized_user():
    update = _make_update("/organize C:/notes", user_id="99999")
    await handle_organize(update, MagicMock())
    update.message.reply_text.assert_called_once_with("Unauthorized")


@pytest.mark.asyncio
async def test_organize_requires_folder_argument(cm):
    update = _make_update("/organize")
    await handle_organize(update, MagicMock())
    assert "Usage" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_organize_defaults_to_by_type_strategy(cm):
    update = _make_update("/organize C:/notes")
    plan_result = ToolResult(tool_name="organize_files", output="📋 plan here", success=True)
    with patch("tools.organizer.organize_files_tool", new_callable=AsyncMock, return_value=plan_result) as mock_tool:
        await handle_organize(update, MagicMock())

    mock_tool.assert_called_once_with(folder="C:/notes", strategy="by_type")
    update.message.reply_text.assert_called_once_with("📋 plan here")


@pytest.mark.asyncio
async def test_organize_passes_explicit_strategy(cm):
    update = _make_update("/organize C:/notes by_keyword")
    plan_result = ToolResult(tool_name="organize_files", output="📋 plan here", success=True)
    with patch("tools.organizer.organize_files_tool", new_callable=AsyncMock, return_value=plan_result) as mock_tool:
        await handle_organize(update, MagicMock())

    mock_tool.assert_called_once_with(folder="C:/notes", strategy="by_keyword")


@pytest.mark.asyncio
async def test_organize_reports_tool_error(cm):
    update = _make_update("/organize C:/missing")
    bad_result = ToolResult(tool_name="organize_files", output="", success=False, error="Folder not found: C:/missing")
    with patch("tools.organizer.organize_files_tool", new_callable=AsyncMock, return_value=bad_result):
        await handle_organize(update, MagicMock())

    final_call = update.message.reply_text.call_args[0][0]
    assert "Folder not found" in final_call
