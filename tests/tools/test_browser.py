import pytest
from unittest.mock import AsyncMock, patch
from tools.browser import browse_url_tool, BROWSE_URL_SCHEMA


def test_schema_valid():
    assert BROWSE_URL_SCHEMA["function"]["name"] == "browse_url"
    assert "url" in BROWSE_URL_SCHEMA["function"]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_browse_returns_tool_result():
    with patch("tools.browser._fetch_page_text", new_callable=AsyncMock, return_value="page content here"):
        result = await browse_url_tool(url="https://example.com")
    assert result.success is True
    assert result.tool_name == "browse_url"
    assert "page content here" in result.output


@pytest.mark.asyncio
async def test_browse_invalid_url():
    result = await browse_url_tool(url="not-a-url")
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_browse_missing_scheme():
    result = await browse_url_tool(url="example.com")
    assert result.success is False


@pytest.mark.asyncio
async def test_browse_fetch_error():
    with patch("tools.browser._fetch_page_text", new_callable=AsyncMock, side_effect=Exception("connection refused")):
        result = await browse_url_tool(url="https://example.com")
    assert result.success is False
    assert "connection refused" in result.error
