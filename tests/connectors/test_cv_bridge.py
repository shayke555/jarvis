"""Tests for Phase 5 — cv_bridge connector."""
from unittest.mock import MagicMock, patch

from connectors.cv_bridge import fetch_cv_status


def test_cv_bridge_returns_error_when_project_not_found():
    with patch("connectors.cv_bridge._ensure_cv_on_path", return_value=False):
        result = fetch_cv_status()

    assert result["status"] == "error"
    assert result["data"] is None
    assert result["error"] is not None


def test_cv_bridge_returns_ok_with_open_applications():
    mock_apps = [
        {"company": "Google", "role": "SWE", "status": "applied", "date_applied": "2026-06-01"},
        {"company": "Meta", "role": "ML Eng", "status": "interviewing", "date_applied": "2026-06-05"},
    ]
    mock_pipeline = {"total": 2, "by_status": {"applied": 1, "interviewing": 1}}

    with patch("connectors.cv_bridge._ensure_cv_on_path", return_value=True), \
         patch.dict("sys.modules", {"tracker.applications": MagicMock(
             get_by_status=lambda s: [a for a in mock_apps if a["status"] == s],
             get_pipeline_summary=lambda: mock_pipeline,
         )}):
        result = fetch_cv_status()

    assert result["status"] == "ok"
    assert result["data"]["total"] == 2
    assert len(result["data"]["open_applications"]) == 2


def test_cv_bridge_handles_import_error_gracefully():
    with patch("connectors.cv_bridge._ensure_cv_on_path", return_value=True), \
         patch("builtins.__import__", side_effect=ImportError("no module")):
        result = fetch_cv_status()

    assert result["status"] == "error"
    assert "import" in result["error"].lower() or result["error"] is not None


def test_cv_bridge_handles_unexpected_exception():
    with patch("connectors.cv_bridge._ensure_cv_on_path", side_effect=Exception("db locked")):
        result = fetch_cv_status()

    assert result["status"] == "error"
    assert result["data"] is None
