"""Disable PROJECTS_BASE_PATH for tool tests.

Tool tests use pytest tmp_path which is outside any real project base.
The path guard is tested separately in tests/tools/test_path_guard.py.
"""
import pytest
from unittest.mock import patch

from config.settings import settings


@pytest.fixture(autouse=True)
def _disable_path_guard():
    """Temporarily clear projects_base_path so safe_path() accepts any path."""
    with patch.object(settings, "projects_base_path", ""):
        yield
