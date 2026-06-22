"""Tests for /gmail Telegram command."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from interfaces.telegram_bot import handle_gmail

OWNER_ID = "12345"


def _make_update(user_id: str = OWNER_ID):
    update = MagicMock()
    update.effective_user.id = int(user_id)
    update.message.text = "/gmail"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture(autouse=True)
def _patch_auth():
    with patch("interfaces.telegram_bot.settings") as mock:
        mock.telegram_owner_chat_id = OWNER_ID
        mock.gmail_email = "shay@gmail.com"
        mock.gmail_app_password = "app-pass-123"
        yield mock


@pytest.mark.asyncio
async def test_gmail_rejects_unauthorized():
    update = _make_update(user_id="99999")
    await handle_gmail(update, MagicMock())
    update.message.reply_text.assert_called_once_with("Unauthorized")


@pytest.mark.asyncio
async def test_gmail_missing_credentials_shows_setup_instructions(_patch_auth):
    _patch_auth.gmail_app_password = ""
    _patch_auth.gmail_email = ""
    update = _make_update()
    await handle_gmail(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "GMAIL_APP_PASSWORD" in reply
    assert "GMAIL_EMAIL" in reply


@pytest.mark.asyncio
async def test_gmail_shows_classified_emails():
    update = _make_update()
    ok_result = {
        "status": "ok",
        "data": {
            "job": [{"company": "Google", "status": "applied"}],
            "money": [],
            "action": [],
            "lead": [],
            "total_scanned": 5,
        },
        "error": None,
    }
    with patch("interfaces.telegram_bot.fetch_gmail_summary", return_value=ok_result), \
         patch("interfaces.telegram_bot.format_gmail_section", return_value="📧 1 חדש"):
        await handle_gmail(update, MagicMock())

    calls = [c[0][0] for c in update.message.reply_text.call_args_list]
    assert any("1 חדש" in c for c in calls)


@pytest.mark.asyncio
async def test_gmail_handles_imap_error():
    update = _make_update()
    error_result = {"status": "error", "data": None, "error": "IMAP connection failed"}
    with patch("interfaces.telegram_bot.fetch_gmail_summary", return_value=error_result):
        await handle_gmail(update, MagicMock())

    reply = update.message.reply_text.call_args_list[-1][0][0]
    assert "IMAP connection failed" in reply


@pytest.mark.asyncio
async def test_gmail_no_new_emails():
    update = _make_update()
    ok_result = {"status": "ok", "data": None, "error": None}
    with patch("interfaces.telegram_bot.fetch_gmail_summary", return_value=ok_result):
        await handle_gmail(update, MagicMock())

    reply = update.message.reply_text.call_args_list[-1][0][0]
    assert "אין" in reply or "no" in reply.lower()
