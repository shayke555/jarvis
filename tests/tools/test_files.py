import os
import tempfile

import pytest
from tools.files import (
    read_file_tool,
    write_file_tool,
    list_dir_tool,
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
    LIST_DIR_SCHEMA,
)


def test_schemas_valid():
    assert READ_FILE_SCHEMA["function"]["name"] == "read_file"
    assert WRITE_FILE_SCHEMA["function"]["name"] == "write_file"
    assert LIST_DIR_SCHEMA["function"]["name"] == "list_dir"


@pytest.mark.asyncio
async def test_read_existing_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("hello jarvis")
        path = f.name
    try:
        result = await read_file_tool(path=path)
        assert result.success is True
        assert "hello jarvis" in result.output
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_read_missing_file():
    result = await read_file_tool(path="/nonexistent/path/file.txt")
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_read_respects_max_chars():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("A" * 1000)
        path = f.name
    try:
        result = await read_file_tool(path=path, max_chars=10)
        assert result.success is True
        # output = "[path]\ncontent" — content must be <= 10 chars
        content_part = result.output.split("\n", 1)[1] if "\n" in result.output else result.output
        assert len(content_part) <= 10
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_write_then_read(tmp_path):
    path = str(tmp_path / "test.txt")
    write_result = await write_file_tool(path=path, content="written by jarvis")
    assert write_result.success is True

    read_result = await read_file_tool(path=path)
    assert read_result.success is True
    assert "written by jarvis" in read_result.output


@pytest.mark.asyncio
async def test_list_dir_returns_files():
    result = await list_dir_tool(path=".")
    assert result.success is True
    assert "bot.py" in result.output


@pytest.mark.asyncio
async def test_list_dir_not_a_directory():
    result = await list_dir_tool(path="/nonexistent/dir")
    assert result.success is False
