"""Tests for monitors/github_trending.py — TDD RED phase."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from monitors.github_trending import RepoInfo, fetch_trending, format_trending_digest


# ── fixtures ──────────────────────────────────────────────────────────────────

def _fake_repo(name: str = "owner/repo", stars: int = 500) -> dict:
    return {
        "full_name": name,
        "description": f"A cool {name} project",
        "stargazers_count": stars,
        "html_url": f"https://github.com/{name}",
        "pushed_at": "2026-05-18T10:00:00Z",
    }


def _fake_api_response(repos: list[dict]) -> dict:
    return {"total_count": len(repos), "items": repos}


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_trending_returns_repo_list() -> None:
    """fetch_trending() returns a list of RepoInfo on success."""
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fake_api_response([
        _fake_repo("anthropics/claude-code", 3200),
        _fake_repo("mendableai/firecrawl", 1100),
    ])

    with patch("monitors.github_trending.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        results = await fetch_trending(days_back=7)

    assert isinstance(results, list)
    assert len(results) >= 1
    assert all(isinstance(r, RepoInfo) for r in results)


@pytest.mark.asyncio
async def test_fetch_trending_repo_fields_populated() -> None:
    """RepoInfo has name, stars, url, description."""
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = _fake_api_response([
        _fake_repo("anthropics/claude-code", 3200),
    ])

    with patch("monitors.github_trending.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        results = await fetch_trending(days_back=7)

    repo = results[0]
    assert repo.name == "anthropics/claude-code"
    assert repo.stars == 3200
    assert "github.com" in repo.url
    assert isinstance(repo.description, str)


@pytest.mark.asyncio
async def test_fetch_trending_handles_api_error_gracefully() -> None:
    """fetch_trending() returns empty list on API error — no crash."""
    with patch("monitors.github_trending.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("network error"))
        mock_client_cls.return_value = mock_client

        results = await fetch_trending(days_back=7)

    assert results == []


@pytest.mark.asyncio
async def test_fetch_trending_handles_non_200() -> None:
    """fetch_trending() returns empty list on non-200 response."""
    fake_response = MagicMock()
    fake_response.status_code = 403
    fake_response.json.return_value = {"message": "rate limited"}

    with patch("monitors.github_trending.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        results = await fetch_trending(days_back=7)

    assert results == []


def test_format_digest_returns_nonempty_string() -> None:
    """format_trending_digest() returns non-empty string from repo list."""
    repos = [
        RepoInfo(
            name="anthropics/claude-code",
            description="CLI for Claude",
            stars=3200,
            url="https://github.com/anthropics/claude-code",
            topic="AI Agents + Claude",
        )
    ]
    result = format_trending_digest(repos)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "claude-code" in result


def test_format_digest_empty_list() -> None:
    """format_trending_digest([]) returns a fallback string, not empty/crash."""
    result = format_trending_digest([])
    assert isinstance(result, str)
    assert len(result) > 0
