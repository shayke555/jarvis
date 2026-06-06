import pytest
from unittest.mock import patch, AsyncMock
from tools.search import web_search_tool, WEB_SEARCH_SCHEMA, search_web, should_search


def test_search_schema_valid():
    assert WEB_SEARCH_SCHEMA["function"]["name"] == "web_search"
    props = WEB_SEARCH_SCHEMA["function"]["parameters"]["properties"]
    assert "query" in props
    assert "max_results" in props


@pytest.mark.asyncio
async def test_search_returns_tool_result_ddg():
    with patch("tools.search._ddg_search", new_callable=AsyncMock, return_value="result from ddg"):
        result = await web_search_tool(query="test query")
    assert result.success is True
    assert result.tool_name == "web_search"
    assert "result from ddg" in result.output


@pytest.mark.asyncio
async def test_search_uses_tavily_when_key_set(monkeypatch):
    monkeypatch.setattr("tools.search.settings.tavily_api_key", "fake-key")
    with patch("tools.search._tavily_search", new_callable=AsyncMock, return_value="tavily result"):
        result = await web_search_tool(query="test")
    assert result.success is True
    assert "tavily result" in result.output


@pytest.mark.asyncio
async def test_search_falls_back_to_ddg_when_no_tavily(monkeypatch):
    monkeypatch.setattr("tools.search.settings.tavily_api_key", "")
    with patch("tools.search._ddg_search", new_callable=AsyncMock, return_value="ddg fallback"):
        result = await web_search_tool(query="test")
    assert result.success is True
    assert "ddg fallback" in result.output


@pytest.mark.asyncio
async def test_search_returns_failure_when_all_engines_fail(monkeypatch):
    monkeypatch.setattr("tools.search.settings.tavily_api_key", "")
    monkeypatch.setattr("tools.search.settings.brave_search_api_key", "")
    with patch("tools.search._ddg_search", new_callable=AsyncMock, side_effect=Exception("network error")):
        result = await web_search_tool(query="test")
    assert result.success is False
    assert result.error is not None


def test_should_search_detects_triggers():
    assert should_search("חפש מחיר ביטקוין") is True
    assert should_search("מה זה asyncio") is True
    assert should_search("תודה רבה") is False


@pytest.mark.asyncio
async def test_search_web_legacy_wrapper():
    with patch("tools.search._ddg_search", new_callable=AsyncMock, return_value="legacy result"):
        output = await search_web("test query")
    assert "legacy result" in output
