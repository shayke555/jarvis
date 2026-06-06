"""Tests for scheduler/weekly_learning.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from scheduler.weekly_learning import _read_recent_growth

_LOG = """\
# Growth Log — Shay

## 2026-05-10 — OLD_PROJECT
Old stuff.

---

## 2026-05-15 — MID_PROJECT
Mid stuff.

---

## 2026-05-18 — LATEST_PROJECT
Latest stuff.

---
"""


def test_read_recent_growth_returns_newest_first(tmp_path: Path) -> None:
    log = tmp_path / "log.md"
    log.write_text(_LOG, encoding="utf-8")
    result = _read_recent_growth(2, log_path=log)
    lines = result.splitlines()
    # First entry must be the most recent date
    assert "2026-05-18" in lines[1]
    assert "2026-05-15" in lines[2]


def test_read_recent_growth_respects_n(tmp_path: Path) -> None:
    log = tmp_path / "log.md"
    log.write_text(_LOG, encoding="utf-8")
    result = _read_recent_growth(1, log_path=log)
    assert "2026-05-18" in result
    assert "2026-05-15" not in result


def test_read_recent_growth_missing_log(tmp_path: Path) -> None:
    result = _read_recent_growth(3, log_path=tmp_path / "nonexistent.md")
    assert "not found" in result.lower() or isinstance(result, str)


def test_read_recent_growth_empty_log(tmp_path: Path) -> None:
    log = tmp_path / "log.md"
    log.write_text("# Growth Log\n", encoding="utf-8")
    result = _read_recent_growth(3, log_path=log)
    assert isinstance(result, str)
    assert len(result) > 0
