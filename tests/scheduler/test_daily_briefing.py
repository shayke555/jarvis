"""Tests for scheduler/daily_briefing.py — project health integration."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _mock_tasks() -> str:
    return "📋 TASKS\n  • Task A"


def _mock_ledger() -> str:
    return "📈 LEDGERALPHA\n  • Regime: bull"


def _mock_projects() -> str:
    return "🧠 PROJECTS\n  • (no open project tasks)"


def _mock_health() -> str:
    return "🧠 PROJECT STATUS\n  🟢 PROJECT-JARVIS (היום)\n    ✅ Phase D done"


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_build_briefing_includes_project_health() -> None:
    """build_briefing() must contain the PROJECT STATUS section."""
    with (
        patch("scheduler.daily_briefing._build_tasks_section", return_value=_mock_tasks()),
        patch("scheduler.daily_briefing._build_ledger_section", return_value=_mock_ledger()),
        patch("scheduler.daily_briefing._build_projects_section", return_value=_mock_projects()),
        patch("scheduler.daily_briefing._build_project_health_section", return_value=_mock_health()),
    ):
        from scheduler.daily_briefing import build_briefing
        result = await build_briefing()

    assert "PROJECT STATUS" in result
    assert "PROJECT-JARVIS" in result


@pytest.mark.asyncio
async def test_build_briefing_health_after_ledger() -> None:
    """PROJECT STATUS section appears after LEDGERALPHA in the briefing."""
    with (
        patch("scheduler.daily_briefing._build_tasks_section", return_value=_mock_tasks()),
        patch("scheduler.daily_briefing._build_ledger_section", return_value=_mock_ledger()),
        patch("scheduler.daily_briefing._build_projects_section", return_value=_mock_projects()),
        patch("scheduler.daily_briefing._build_project_health_section", return_value=_mock_health()),
    ):
        from scheduler.daily_briefing import build_briefing
        result = await build_briefing()

    ledger_pos = result.index("LEDGERALPHA")
    health_pos = result.index("PROJECT STATUS")
    assert health_pos > ledger_pos


@pytest.mark.asyncio
async def test_build_briefing_health_error_does_not_crash() -> None:
    """If project_health raises, briefing still sends (graceful fallback)."""
    with (
        patch("scheduler.daily_briefing._build_tasks_section", return_value=_mock_tasks()),
        patch("scheduler.daily_briefing._build_ledger_section", return_value=_mock_ledger()),
        patch("scheduler.daily_briefing._build_projects_section", return_value=_mock_projects()),
        patch(
            "scheduler.daily_briefing._build_project_health_section",
            side_effect=Exception("disk error"),
        ),
    ):
        from scheduler.daily_briefing import build_briefing
        result = await build_briefing()

    # Must still return a non-empty string
    assert "בוקר שי" in result


def test_project_health_section_returns_string() -> None:
    """_build_project_health_section() returns a non-empty string."""
    with patch(
        "monitors.project_health.format_project_health",
        return_value="🧠 PROJECT STATUS\n  🟢 X (היום)",
    ):
        from scheduler.daily_briefing import _build_project_health_section
        result = _build_project_health_section()

    assert isinstance(result, str)
    assert len(result) > 0
