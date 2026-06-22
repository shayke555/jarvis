import os
import time

import pytest
from tools.organizer import (
    organize_files_tool,
    build_plan,
    ORGANIZE_FILES_SCHEMA,
)


def test_schema_valid():
    assert ORGANIZE_FILES_SCHEMA["function"]["name"] == "organize_files"
    assert "folder" in ORGANIZE_FILES_SCHEMA["function"]["parameters"]["properties"]


def _touch(path, name, content="x"):
    p = path / name
    p.write_text(content)
    return p


@pytest.mark.asyncio
async def test_organize_by_type_groups_correctly(tmp_path):
    _touch(tmp_path, "notes.txt")
    _touch(tmp_path, "essay.txt")
    _touch(tmp_path, "photo.jpg")

    result = await organize_files_tool(folder=str(tmp_path), strategy="by_type")

    assert result.success is True
    assert "DRY RUN" in result.output
    assert "txt/" in result.output
    assert "jpg/" in result.output
    assert "notes.txt" in result.output
    # Nothing on disk should have moved
    assert os.path.exists(tmp_path / "notes.txt")
    assert os.path.exists(tmp_path / "photo.jpg")


@pytest.mark.asyncio
async def test_organize_by_keyword_groups_by_first_token(tmp_path):
    _touch(tmp_path, "algorithms_lecture1.pdf")
    _touch(tmp_path, "algorithms_lecture2.pdf")
    _touch(tmp_path, "databases_intro.pdf")

    result = await organize_files_tool(folder=str(tmp_path), strategy="by_keyword")

    assert result.success is True
    assert "algorithms/" in result.output
    assert "databases/" in result.output


@pytest.mark.asyncio
async def test_organize_by_date_groups_by_year_month(tmp_path):
    _touch(tmp_path, "recent.txt")

    result = await organize_files_tool(folder=str(tmp_path), strategy="by_date")

    assert result.success is True
    current_month = time.strftime("%Y-%m")
    assert current_month in result.output


@pytest.mark.asyncio
async def test_organize_empty_folder(tmp_path):
    result = await organize_files_tool(folder=str(tmp_path), strategy="by_type")
    assert result.success is True
    assert "No files found" in result.output


@pytest.mark.asyncio
async def test_organize_missing_folder():
    result = await organize_files_tool(folder="/nonexistent/folder/path")
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_organize_path_is_a_file_not_a_directory(tmp_path):
    f = _touch(tmp_path, "file.txt")
    result = await organize_files_tool(folder=str(f))
    assert result.success is False
    assert "Not a directory" in result.error


@pytest.mark.asyncio
async def test_organize_rejects_unknown_strategy(tmp_path):
    result = await organize_files_tool(folder=str(tmp_path), strategy="by_vibes")
    assert result.success is False
    assert "Unknown strategy" in result.error


@pytest.mark.asyncio
async def test_organize_never_touches_filesystem(tmp_path):
    """Critical safety property: dry-run mode must never move/rename/delete files."""
    names = ["a.txt", "b.pdf", "c.jpg"]
    for n in names:
        _touch(tmp_path, n)
    before = sorted(os.listdir(tmp_path))

    await organize_files_tool(folder=str(tmp_path), strategy="by_type")

    after = sorted(os.listdir(tmp_path))
    assert before == after


def test_build_plan_raises_on_unknown_strategy(tmp_path):
    _touch(tmp_path, "x.txt")
    with pytest.raises(ValueError):
        build_plan(tmp_path, "by_vibes")


@pytest.mark.asyncio
async def test_organize_warns_when_truncated(tmp_path, monkeypatch):
    """When a folder exceeds _MAX_FILES_SCANNED, the plan must say so explicitly —
    silently dropping files would be a footgun once the approval gate ships."""
    import tools.organizer as organizer_module
    monkeypatch.setattr(organizer_module, "_MAX_FILES_SCANNED", 2)
    for n in ["a.txt", "b.txt", "c.txt", "d.txt"]:
        _touch(tmp_path, n)

    result = await organize_files_tool(folder=str(tmp_path), strategy="by_type")

    assert result.success is True
    assert "INCOMPLETE" in result.output
    assert "4 files" in result.output
    assert "first 2" in result.output


def test_build_plan_groups_by_type(tmp_path):
    _touch(tmp_path, "a.txt")
    _touch(tmp_path, "b.txt")
    _touch(tmp_path, "c.pdf")

    plan = build_plan(tmp_path, "by_type")

    assert sorted(plan["txt"]) == ["a.txt", "b.txt"]
    assert plan["pdf"] == ["c.pdf"]
