"""Shared path-traversal guard for filesystem-touching tools.

Extracted from tools/files.py so other tools (document_reader, organizer, ...)
can reuse the same safety check via a public name instead of importing a
"private" underscore-prefixed function across modules.
"""
from __future__ import annotations

from pathlib import Path


def safe_path(path: str) -> Path | None:
    """Resolve path and reject traversal attacks (e.g. ../../etc/passwd).

    Returns the resolved Path if it's within settings.projects_base_path
    (when configured) and contains no ".." segments, else None.
    """
    from config.settings import settings
    resolved = Path(path).resolve()
    if ".." in Path(path).parts:
        return None
    base = Path(settings.projects_base_path).resolve() if settings.projects_base_path else None
    if base is not None:
        # is_relative_to does a proper path-segment comparison — naive string
        # startswith would let "C:\Users\shayg\Projects-evil" pass a check
        # against base "C:\Users\shayg\Projects".
        if not resolved.is_relative_to(base):
            return None
    return resolved
