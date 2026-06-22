import os
import tempfile
from unittest.mock import patch

import pytest
from tools.document_reader import (
    read_document_tool,
    extract_text,
    READ_DOCUMENT_SCHEMA,
)


def test_schema_valid():
    assert READ_DOCUMENT_SCHEMA["function"]["name"] == "read_document"
    assert "path" in READ_DOCUMENT_SCHEMA["function"]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_read_txt_document():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("exam notes: chapter 1 covers algorithms")
        path = f.name
    try:
        result = await read_document_tool(path=path)
        assert result.success is True
        assert "chapter 1 covers algorithms" in result.output
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_read_md_document():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Notes\n\nSome markdown content")
        path = f.name
    try:
        result = await read_document_tool(path=path)
        assert result.success is True
        assert "Some markdown content" in result.output
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_read_docx_document(tmp_path):
    from docx import Document
    doc = Document()
    doc.add_paragraph("This is a CV summary paragraph.")
    path = str(tmp_path / "cv.docx")
    doc.save(path)

    result = await read_document_tool(path=path)
    assert result.success is True
    assert "This is a CV summary paragraph." in result.output


@pytest.mark.asyncio
async def test_read_pdf_document(tmp_path):
    path = str(tmp_path / "course.pdf")
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4 fake content")

    with patch("tools.document_reader._extract_pdf", return_value="--- page 1 ---\nLecture notes on graphs"):
        result = await read_document_tool(path=path)

    assert result.success is True
    assert "Lecture notes on graphs" in result.output


@pytest.mark.asyncio
async def test_read_missing_file():
    result = await read_document_tool(path="/nonexistent/path/notes.pdf")
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_read_unsupported_format(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("a,b,c\n1,2,3")

    result = await read_document_tool(path=str(path))
    assert result.success is False
    assert "Unsupported format" in result.error


@pytest.mark.asyncio
async def test_read_empty_extraction_reports_error(tmp_path):
    path = tmp_path / "blank.txt"
    path.write_text("   \n   ")

    result = await read_document_tool(path=str(path))
    assert result.success is False
    assert "No extractable text" in result.error


@pytest.mark.asyncio
async def test_read_respects_max_chars():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("B" * 1000)
        path = f.name
    try:
        result = await read_document_tool(path=path, max_chars=10)
        assert result.success is True
        content_part = result.output.split("\n", 1)[1] if "\n" in result.output else result.output
        assert len(content_part) <= 10
    finally:
        os.unlink(path)


def test_extract_text_raises_on_unsupported_suffix(tmp_path):
    path = tmp_path / "weird.xyz"
    path.write_text("data")
    with pytest.raises(ValueError):
        extract_text(path)
