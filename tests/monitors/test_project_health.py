"""Tests for monitors/project_health.py — TDD RED phase."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from monitors.project_health import (
    ProjectStatus,
    format_project_health,
    scan_projects,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def projects_root(tmp_path: Path) -> Path:
    return tmp_path / "Projects"


def _make_project(root: Path, name: str, content: str, mtime_days_ago: float = 0) -> Path:
    """Create a fake project directory with context.md."""
    proj = root / name
    proj.mkdir(parents=True)
    ctx = proj / "context.md"
    ctx.write_text(content, encoding="utf-8")
    if mtime_days_ago:
        ts = time.time() - mtime_days_ago * 86400
        import os
        os.utime(ctx, (ts, ts))
    return proj


_FRESH_CONTEXT = """\
# Project Context — ALPHA
_Updated: 2026-05-18_

## Status
Active

## Last Completed
- Phase D done — 49 tests passing

## Next Step
- Build monitors layer

## Blockers
- none
"""

_STALE_CONTEXT = """\
# Project Context — BETA
_Updated: 2026-05-12_

## Status
Paused

## Last Completed
- LangGraph refactor complete

## Next Step
- Interview mock loop

## Blockers
- Need API key
"""

_MINIMAL_CONTEXT = """\
# Project Context — GAMMA
_Updated: 2026-05-17_

## Status
Active
"""


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_scan_finds_projects_with_context_md(projects_root: Path) -> None:
    _make_project(projects_root, "ALPHA", _FRESH_CONTEXT)
    _make_project(projects_root, "BETA", _STALE_CONTEXT, mtime_days_ago=6)
    # project with no context.md — should be ignored
    no_ctx = projects_root / "GAMMA"
    no_ctx.mkdir()

    results = scan_projects(projects_root)
    names = [r.name for r in results]
    assert "ALPHA" in names
    assert "BETA" in names
    assert "GAMMA" not in names


def test_parse_last_completed_section(projects_root: Path) -> None:
    _make_project(projects_root, "ALPHA", _FRESH_CONTEXT)
    results = scan_projects(projects_root)
    alpha = next(r for r in results if r.name == "ALPHA")
    assert "Phase D done" in alpha.last_completed


def test_parse_next_step_section(projects_root: Path) -> None:
    _make_project(projects_root, "ALPHA", _FRESH_CONTEXT)
    results = scan_projects(projects_root)
    alpha = next(r for r in results if r.name == "ALPHA")
    assert "monitors" in alpha.next_step.lower()


def test_staleness_flag_green(projects_root: Path) -> None:
    _make_project(projects_root, "ALPHA", _FRESH_CONTEXT, mtime_days_ago=0)
    results = scan_projects(projects_root)
    alpha = next(r for r in results if r.name == "ALPHA")
    assert alpha.staleness_days <= 1
    assert alpha.staleness_emoji == "🟢"


def test_staleness_flag_yellow(projects_root: Path) -> None:
    _make_project(projects_root, "ALPHA", _FRESH_CONTEXT, mtime_days_ago=3)
    results = scan_projects(projects_root)
    alpha = next(r for r in results if r.name == "ALPHA")
    assert alpha.staleness_emoji == "🟡"


def test_staleness_flag_red(projects_root: Path) -> None:
    _make_project(projects_root, "BETA", _STALE_CONTEXT, mtime_days_ago=6)
    results = scan_projects(projects_root)
    beta = next(r for r in results if r.name == "BETA")
    assert beta.staleness_emoji == "🔴"


def test_format_returns_nonempty_string(projects_root: Path) -> None:
    _make_project(projects_root, "ALPHA", _FRESH_CONTEXT)
    result = format_project_health(projects_root)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "ALPHA" in result


def test_format_includes_emoji_indicators(projects_root: Path) -> None:
    _make_project(projects_root, "FRESH", _FRESH_CONTEXT, mtime_days_ago=0)
    _make_project(projects_root, "OLD", _STALE_CONTEXT, mtime_days_ago=6)
    result = format_project_health(projects_root)
    assert "🟢" in result
    assert "🔴" in result


def test_missing_sections_handled_gracefully(projects_root: Path) -> None:
    _make_project(projects_root, "GAMMA", _MINIMAL_CONTEXT)
    results = scan_projects(projects_root)
    gamma = next(r for r in results if r.name == "GAMMA")
    # Should not raise — missing sections return empty string
    assert gamma.last_completed == ""
    assert gamma.next_step == ""
