"""Tests for Phase 5 Telegram commands /jobs and /signals."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from interfaces.telegram_bot import handle_jobs, handle_signals

OWNER_ID = "12345"


def _make_update(text: str, user_id: str = OWNER_ID):
    update = MagicMock()
    update.effective_user.id = int(user_id)
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture(autouse=True)
def _patch_settings():
    with patch("interfaces.telegram_bot.settings") as mock:
        mock.telegram_owner_chat_id = OWNER_ID
        yield mock


# --- /jobs ---

@pytest.mark.asyncio
async def test_jobs_rejects_unauthorized():
    update = _make_update("/jobs", user_id="99999")
    await handle_jobs(update, MagicMock())
    update.message.reply_text.assert_called_once_with("Unauthorized")


@pytest.mark.asyncio
async def test_jobs_reports_cv_bridge_error():
    update = _make_update("/jobs")
    error_result = {"status": "error", "data": None, "error": "tracker not found"}
    with patch("connectors.cv_bridge.fetch_cv_status", return_value=error_result):
        await handle_jobs(update, MagicMock())
    assert "לא הצלחתי" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_jobs_shows_no_applications_message():
    update = _make_update("/jobs")
    ok_result = {"status": "ok", "data": {"open_applications": [], "total": 0, "pipeline_summary": {}}, "error": None}
    with patch("connectors.cv_bridge.fetch_cv_status", return_value=ok_result):
        await handle_jobs(update, MagicMock())
    assert "אין מועמדויות" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_jobs_shows_open_applications():
    update = _make_update("/jobs")
    apps = [{"company": "Google", "role": "SWE", "status": "applied", "date_applied": "2026-06-01"}]
    ok_result = {"status": "ok", "data": {"open_applications": apps, "total": 1, "pipeline_summary": {}}, "error": None}
    with patch("connectors.cv_bridge.fetch_cv_status", return_value=ok_result):
        await handle_jobs(update, MagicMock())
    assert "Google" in update.message.reply_text.call_args[0][0]


# --- /signals ---

@pytest.mark.asyncio
async def test_signals_rejects_unauthorized():
    update = _make_update("/signals", user_id="99999")
    await handle_signals(update, MagicMock())
    update.message.reply_text.assert_called_once_with("Unauthorized")


@pytest.mark.asyncio
async def test_signals_reports_ledger_error():
    update = _make_update("/signals")
    with patch("connectors.ledger_bridge.fetch_ledger_signals",
               return_value={"status": "error", "data": None, "error": "file not found"}):
        await handle_signals(update, MagicMock())
    assert "לא זמין" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_signals_shows_regime_and_top_signal():
    update = _make_update("/signals")
    signals = [{"ticker": "AAPL", "score": 0.92, "direction": "long"}]
    data = {
        "regime": "bullish",
        "top_signal": signals[0],
        "all_signals": signals,
        "signal_count": 1,
        "timestamp": "2026-06-01T09:00:00",
    }
    with patch("connectors.ledger_bridge.fetch_ledger_signals",
               return_value={"status": "ok", "data": data, "error": None}):
        await handle_signals(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "BULLISH" in reply  # now uppercased
    assert "AAPL" in reply
