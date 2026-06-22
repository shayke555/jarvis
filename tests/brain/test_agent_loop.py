import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from brain.agent_loop import AgentLoop
from tools.registry import ToolRegistry, ToolResult


def _make_loop(llm_responses: list, tool_result: ToolResult | None = None) -> AgentLoop:
    """Build an AgentLoop with mocked LLM and registry."""
    loop = AgentLoop.__new__(AgentLoop)
    loop._llm = MagicMock()
    loop._llm.chat_with_tools = AsyncMock(side_effect=llm_responses)

    loop._registry = MagicMock()
    loop._registry.get_groq_tools = MagicMock(return_value=[])
    if tool_result:
        loop._registry.execute = AsyncMock(return_value=tool_result)

    return loop


@pytest.mark.asyncio
async def test_agent_answers_directly_without_tools():
    loop = _make_loop(llm_responses=["direct answer"])
    result = await loop.run(messages=[{"role": "user", "content": "מה שלומך?"}])
    assert result == "direct answer"


@pytest.mark.asyncio
async def test_agent_retries_via_plain_chat_when_tool_response_is_empty():
    """chat_with_tools can return '' when the model picks no tool and has nothing
    to say in tools-mode — must not surface a blank reply, retry via plain chat."""
    loop = _make_loop(llm_responses=[""])
    loop._llm.chat = AsyncMock(return_value="a real answer from plain chat")

    result = await loop.run(messages=[{"role": "user", "content": "מה שלומך?"}])

    assert result == "a real answer from plain chat"
    loop._llm.chat.assert_called_once()


@pytest.mark.asyncio
async def test_agent_uses_tool_then_answers():
    tool_call_response = {
        "tool_calls": [{
            "id": "call_1",
            "function": {"name": "web_search", "arguments": json.dumps({"query": "bitcoin price"})}
        }]
    }
    loop = _make_loop(
        llm_responses=[tool_call_response, "Bitcoin is $50k"],
        tool_result=ToolResult(tool_name="web_search", output="BTC: $50,000", success=True),
    )
    result = await loop.run(messages=[{"role": "user", "content": "מחיר ביטקוין?"}])
    assert result == "Bitcoin is $50k"
    loop._registry.execute.assert_called_once_with("web_search", {"query": "bitcoin price"})


@pytest.mark.asyncio
async def test_agent_handles_tool_failure_gracefully():
    tool_call_response = {
        "tool_calls": [{
            "id": "call_1",
            "function": {"name": "web_search", "arguments": json.dumps({"query": "test"})}
        }]
    }
    loop = _make_loop(
        llm_responses=[tool_call_response, "I couldn't find that"],
        tool_result=ToolResult(tool_name="web_search", output="", success=False, error="timeout"),
    )
    result = await loop.run(messages=[{"role": "user", "content": "חפש משהו"}])
    assert result == "I couldn't find that"


@pytest.mark.asyncio
async def test_agent_stops_at_max_rounds():
    """LLM always returns tool_calls — loop must stop after _MAX_TOOL_ROUNDS."""
    always_tool = {
        "tool_calls": [{
            "id": "call_x",
            "function": {"name": "web_search", "arguments": json.dumps({"query": "loop"})}
        }]
    }
    loop = _make_loop(
        llm_responses=[always_tool] * 10,
        tool_result=ToolResult(tool_name="web_search", output="result", success=True),
    )
    result = await loop.run(messages=[{"role": "user", "content": "test"}])
    assert "מגבלת" in result or "limit" in result.lower()
