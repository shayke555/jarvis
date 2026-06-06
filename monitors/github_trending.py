"""GitHub trending monitor — AI Agents/Claude/MCP + Fintech repos, weekly."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

# Each tuple: (label, [topic_keywords]) — each keyword gets its own API call
TOPICS = [
    ("AI Agents + Claude", ["ai-agents", "claude", "mcp"]),
    ("Fintech / Trading", ["algorithmic-trading", "fintech"]),
]

_GITHUB_SEARCH = "https://api.github.com/search/repositories"


@dataclass
class RepoInfo:
    name: str
    description: str
    stars: int
    url: str
    topic: str


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


def _cutoff_date(days_back: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_back)
    return dt.strftime("%Y-%m-%d")


async def fetch_trending(days_back: int = 7) -> list[RepoInfo]:
    """Fetch repos active in last N days across all TOPICS, sorted by stars."""
    cutoff = _cutoff_date(days_back)
    seen: set[str] = set()
    results: list[RepoInfo] = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            for label, keywords in TOPICS:
                for kw in keywords:
                    q = f"topic:{kw} pushed:>{cutoff}"
                    resp = await client.get(
                        _GITHUB_SEARCH,
                        params={"q": q, "sort": "stars", "order": "desc", "per_page": 5},
                        headers=_headers(),
                    )
                    if resp.status_code == 429:
                        retry_after = resp.headers.get("Retry-After", "unknown")
                        logger.warning("GitHub rate limit hit for topic:%s (Retry-After: %s)", kw, retry_after)
                        continue
                    if resp.status_code != 200:
                        logger.warning("GitHub API %s for topic:%s — %s", resp.status_code, kw, resp.text[:200])
                        continue
                    for item in resp.json().get("items", []):
                        # M1: skip items missing required fields
                        name = item.get("full_name")
                        raw_url = item.get("html_url", "")
                        if not name or not raw_url:
                            continue
                        # H3: validate URL is actually a GitHub repo
                        if not raw_url.startswith("https://github.com/"):
                            continue
                        if name in seen:
                            continue
                        seen.add(name)
                        results.append(RepoInfo(
                            name=name,
                            description=item.get("description") or "",
                            stars=item.get("stargazers_count", 0),
                            url=raw_url,
                            topic=label,
                        ))
    except Exception as e:
        logger.error("GitHub trending fetch failed: %s", e)
        return []

    return sorted(results, key=lambda r: r.stars, reverse=True)


def format_trending_digest(repos: list[RepoInfo]) -> str:
    """Format weekly GitHub digest for Telegram."""
    if not repos:
        return "🔥 GitHub this week:\n  (no trending repos found)"

    from itertools import groupby

    lines = ["🔥 GitHub this week:"]
    by_topic = sorted(repos, key=lambda r: r.topic)
    for topic, group in groupby(by_topic, key=lambda r: r.topic):
        lines.append(f"\n  [{topic}]")
        for repo in sorted(group, key=lambda r: r.stars, reverse=True):
            stars_k = f"{repo.stars / 1000:.1f}k" if repo.stars >= 1000 else str(repo.stars)
            desc = repo.description[:60] + "…" if len(repo.description) > 60 else repo.description
            lines.append(f"  • {repo.name} ⭐ {stars_k}")
            if desc:
                lines.append(f"    {desc}")

    return "\n".join(lines)
