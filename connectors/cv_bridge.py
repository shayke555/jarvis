"""Phase 5 — reads job-application data from PROJECT-CV-PRIVTE.

Zero cost: local SQLite read-only. Mirrors ledger_bridge.py shape exactly.
Never crashes JARVIS — all errors return {status: "error"} with a message.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)


def _cv_paths() -> tuple[Path, Path]:
    base = Path(settings.cv_project_path)
    return base, base / "interview-agent" / "tracker"


def _ensure_cv_on_path() -> bool:
    """Add CV project to sys.path so we can import its tracker module."""
    cv_path, tracker_path = _cv_paths()
    tracker_parent = str(cv_path / "interview-agent")
    if tracker_parent not in sys.path:
        sys.path.insert(0, tracker_parent)
    return tracker_path.exists()


def fetch_cv_status() -> dict:
    """Return open applications and pipeline summary from PROJECT-CV-PRIVTE.

    Returns:
        {status: "ok", data: {open_applications, pipeline_summary, total}, error: None}
        {status: "error", data: None, error: <message>}
    """
    try:
        _, tracker_path = _cv_paths()
        if not _ensure_cv_on_path():
            return {
                "status": "error",
                "data": None,
                "error": f"PROJECT-CV-PRIVTE tracker not found at {tracker_path} (set CV_PROJECT_PATH in .env)",
            }

        from tracker.applications import get_by_status, get_pipeline_summary

        open_apps = get_by_status("applied") + get_by_status("interviewing")
        pipeline = get_pipeline_summary()

        return {
            "status": "ok",
            "data": {
                "open_applications": open_apps,
                "pipeline_summary": pipeline,
                "total": len(open_apps),
            },
            "error": None,
        }
    except ImportError as e:
        logger.warning("cv_bridge: tracker module not importable: %s", e)
        return {"status": "error", "data": None, "error": f"tracker import failed: {e}"}
    except Exception as e:
        logger.error("cv_bridge error: %s", e, exc_info=True)
        return {"status": "error", "data": None, "error": str(e)}
