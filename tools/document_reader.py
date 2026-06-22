"""Phase 6 — extracts plain text from PDF/DOCX/TXT/MD documents so JARVIS can
read, summarize, and reason about local files (course notes, CVs, contracts...).

Read-only. No approval gate needed (mirrors read_file_tool's safety model —
reuses the same path-traversal guard).
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from tools.path_guard import safe_path as _safe_path
from tools.registry import ToolResult

logger = logging.getLogger(__name__)

_SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20MB — guards against decompression-bomb-style DoS
_EXTRACTION_TIMEOUT_SECONDS = 30

READ_DOCUMENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_document",
        "description": (
            "Extract plain text from a local document — supports PDF, DOCX, TXT, and MD. "
            "Use when asked to read, summarize, or analyze a course PDF, Word doc, CV, or notes file. "
            "Prefer this over read_file for .pdf/.docx files (read_file cannot parse binary formats)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative path to the document"},
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters of extracted text to return (default 8000)",
                    "default": 8000,
                },
            },
            "required": ["path"],
        },
    },
}


def extract_text(path: Path) -> str:
    """Dispatch to the right extractor based on file suffix. Raises on unsupported formats —
    callers (the tool wrapper) translate that into a ToolResult error."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported document format: {suffix} (supported: {sorted(_SUPPORTED_SUFFIXES)})")


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"--- page {i + 1} ---\n{text}")
    return "\n\n".join(pages)


def _extract_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


async def read_document_tool(path: str, max_chars: int = 8000) -> ToolResult:
    try:
        p = _safe_path(path)
        if p is None:
            return ToolResult(tool_name="read_document", output="", success=False,
                              error="Path rejected: outside allowed directory or contains traversal.")
        if not p.exists():
            return ToolResult(tool_name="read_document", output="", success=False,
                              error=f"File not found: {path}")
        if p.suffix.lower() not in _SUPPORTED_SUFFIXES:
            return ToolResult(tool_name="read_document", output="", success=False,
                              error=f"Unsupported format: {p.suffix} (supported: {sorted(_SUPPORTED_SUFFIXES)})")

        size = p.stat().st_size
        if size > _MAX_FILE_BYTES:
            return ToolResult(tool_name="read_document", output="", success=False,
                              error=f"File too large ({size // (1024*1024)}MB > {_MAX_FILE_BYTES // (1024*1024)}MB limit): {path}")

        try:
            text = await asyncio.wait_for(
                asyncio.to_thread(extract_text, p),
                timeout=_EXTRACTION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return ToolResult(tool_name="read_document", output="", success=False,
                              error=f"Extraction timed out after {_EXTRACTION_TIMEOUT_SECONDS}s — file may be malformed or too complex: {path}")

        if not text.strip():
            return ToolResult(tool_name="read_document", output="", success=False,
                              error=f"No extractable text found in {path} (scanned image PDF? empty doc?)")

        truncated = text[:max_chars]
        return ToolResult(tool_name="read_document", output=f"[{path}]\n{truncated}", success=True)
    except ValueError as e:
        return ToolResult(tool_name="read_document", output="", success=False, error=str(e))
    except Exception as e:
        logger.error("read_document failed for %s: %s", path, e, exc_info=True)
        return ToolResult(tool_name="read_document", output="", success=False,
                          error=f"Failed to extract text from {path} (see logs for details).")
