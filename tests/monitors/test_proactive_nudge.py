"""Tests for Phase 4 — proactive nudge + detect_stuck_projects."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from monitors.project_health import detect_stuck_projects
from scheduler.proactive_nudge import proactive_nudge_job, _NUDGE_DATE_KEY


# --- detect_stuck_projects ---

def _make_ctx(tmp_path: Path, name: str, next_step: str, mtime_days_ago: int) -> Path:
    import time
    proj = tmp_path / name
    proj.mkdir()
    ctx = proj / "context.md"
    ctx.write_text(f"## Next Step\n- {next_step}\n\n## Last Completed\n- something\n")
    old_mtime = time.time() - mtime_days_ago * 86400
    import os
    os.utime(ctx, (old_mtime, old_mtime))
    return proj


def test_detect_stuck_returns_stale_projects_with_next_step(tmp_path):
    _make_ctx(tmp_path, "PROJECT-A", "fix auth bug", mtime_days_ago=10)
    _make_ctx(tmp_path, "PROJECT-B", "deploy to prod", mtime_days_ago=2)

    stuck = detect_stuck_projects(threshold_days=5, projects_base=tmp_path)

    names = [s["project"] for s in stuck]
    assert "PROJECT-A" in names
    assert "PROJECT-B" not in names


def test_detect_stuck_excludes_projects_without_next_step(tmp_path):
    proj = tmp_path / "IDLE"
    proj.mkdir()
    ctx = proj / "context.md"
    ctx.write_text("## Last Completed\n- done\n")
    import time, os
    old = time.time() - 10 * 86400
    os.utime(ctx, (old, old))

    stuck = detect_stuck_projects(threshold_days=5, projects_base=tmp_path)
    assert not any(s["project"] == "IDLE" for s in stuck)


def test_detect_stuck_threshold_respected(tmp_path):
    _make_ctx(tmp_path, "PROJECT-X", "write tests", mtime_days_ago=3)
    stuck = detect_stuck_projects(threshold_days=5, projects_base=tmp_path)
    assert not stuck

    stuck2 = detect_stuck_projects(threshold_days=2, projects_base=tmp_path)
    assert any(s["project"] == "PROJECT-X" for s in stuck2)


# --- proactive_nudge_job ---

def _make_cm(last_nudge: str | None = None):
    cm = MagicMock()
    cm.sqlite.get_preference = MagicMock(return_value=last_nudge)
    cm.sqlite.set_preference = MagicMock()
    return cm


@pytest.mark.asyncio
async def test_nudge_sends_when_stuck_and_no_prior_nudge_today():
    cm = _make_cm(last_nudge=None)
    send_fn = AsyncMock()
    stuck = [{"project": "PROJECT-A", "days_stale": 8, "next_step": "do X", "urgent_tasks": []}]

    with patch("monitors.project_health.detect_stuck_projects", return_value=stuck):
        await proactive_nudge_job(cm, send_fn)

    send_fn.assert_called_once()
    assert "PROJECT-A" in send_fn.call_args[0][0]
    cm.sqlite.set_preference.assert_called_once()


@pytest.mark.asyncio
async def test_nudge_skips_when_already_sent_today():
    from datetime import date
    cm = _make_cm(last_nudge=date.today().isoformat())
    send_fn = AsyncMock()
    stuck = [{"project": "PROJECT-A", "days_stale": 8, "next_step": "do X", "urgent_tasks": []}]

    with patch("monitors.project_health.detect_stuck_projects", return_value=stuck):
        await proactive_nudge_job(cm, send_fn)

    send_fn.assert_not_called()


@pytest.mark.asyncio
async def test_nudge_skips_when_no_stuck_projects():
    cm = _make_cm()
    send_fn = AsyncMock()

    with patch("monitors.project_health.detect_stuck_projects", return_value=[]):
        await proactive_nudge_job(cm, send_fn)

    send_fn.assert_not_called()
    cm.sqlite.set_preference.assert_not_called()


@pytest.mark.asyncio
async def test_nudge_does_not_crash_on_error():
    cm = _make_cm()
    send_fn = AsyncMock(side_effect=Exception("network down"))

    with patch("monitors.project_health.detect_stuck_projects",
               return_value=[{"project": "X", "days_stale": 6, "next_step": "y", "urgent_tasks": []}]):
        await proactive_nudge_job(cm, send_fn)  # must not raise
