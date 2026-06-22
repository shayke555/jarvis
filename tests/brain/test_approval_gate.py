"""Tests for Phase 2 — Approval Gate in AgentLoop.

Verifies: risky tools trigger gate, non-risky bypass, approve/reject paths,
feature-flag disable, and None callback (non-Telegram callers).
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from brain.agent_loop import AgentLoop, _RISKY_TOOLS
from tools.registry import ToolResult


def _make_loop(llm_responses: list, tool_result: ToolResult | None = None) -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop._llm = MagicMock()
    loop._llm.chat_with_tools = AsyncMock(side_effect=llm_responses)
    loop._llm.chat = AsyncMock(return_value="fallback answer")

    loop._registry = MagicMock()
    loop._registry.get_groq_tools = MagicMock(return_value=[])
    if tool_result:
        loop._registry.execute = AsyncMock(return_value=tool_result)
    return loop


def _tool_call_response(tool_name: str, args: dict) -> dict:
    return {
        "tool_calls": [{
            "id": "call_1",
            "function": {"name": tool_name, "arguments": json.dumps(args)},
        }]
    }


# --- Risky tool set ---

def test_risky_tools_set_contains_expected():
    assert "run_python" in _RISKY_TOOLS
    assert "write_file" in _RISKY_TOOLS
    assert "execute_file_organization" in _RISKY_TOOLS


def test_non_risky_tool_not_in_set():
    assert "web_search" not in _RISKY_TOOLS
    assert "read_file" not in _RISKY_TOOLS


# --- Approval gate triggered for risky tools ---

@pytest.mark.asyncio
async def test_risky_tool_approved_executes():
    loop = _make_loop(
        llm_responses=[_tool_call_response("run_python", {"code": "print(1)"}), "done"],
        tool_result=ToolResult(tool_name="run_python", output="1", success=True),
    )
    approval_cb = AsyncMock(return_value=True)

    with patch("brain.agent_loop.settings") as mock_settings:
        mock_settings.approval_gate_enabled = True
        result = await loop.run(
            messages=[{"role": "user", "content": "run code"}],
            on_approval_request=approval_cb,
        )

    approval_cb.assert_called_once_with("run_python", {"code": "print(1)"})
    loop._registry.execute.assert_called_once()
    assert result == "done"


@pytest.mark.asyncio
async def test_risky_tool_rejected_skips_execution():
    loop = _make_loop(
        llm_responses=[_tool_call_response("write_file", {"path": "/tmp/x.txt", "content": "hi"}), "ok, skipped"],
        tool_result=ToolResult(tool_name="write_file", output="written", success=True),
    )
    approval_cb = AsyncMock(return_value=False)

    with patch("brain.agent_loop.settings") as mock_settings:
        mock_settings.approval_gate_enabled = True
        result = await loop.run(
            messages=[{"role": "user", "content": "write file"}],
            on_approval_request=approval_cb,
        )

    approval_cb.assert_called_once()
    loop._registry.execute.assert_not_called()
    assert result == "ok, skipped"


@pytest.mark.asyncio
async def test_non_risky_tool_bypasses_gate():
    loop = _make_loop(
        llm_responses=[_tool_call_response("web_search", {"query": "test"}), "found it"],
        tool_result=ToolResult(tool_name="web_search", output="results", success=True),
    )
    approval_cb = AsyncMock(return_value=True)

    with patch("brain.agent_loop.settings") as mock_settings:
        mock_settings.approval_gate_enabled = True
        await loop.run(
            messages=[{"role": "user", "content": "search"}],
            on_approval_request=approval_cb,
        )

    approval_cb.assert_not_called()
    loop._registry.execute.assert_called_once()


# --- Feature flag disabled ---

@pytest.mark.asyncio
async def test_gate_disabled_risky_tool_executes_without_asking():
    loop = _make_loop(
        llm_responses=[_tool_call_response("run_python", {"code": "print(1)"}), "done"],
        tool_result=ToolResult(tool_name="run_python", output="1", success=True),
    )
    approval_cb = AsyncMock(return_value=True)

    with patch("brain.agent_loop.settings") as mock_settings:
        mock_settings.approval_gate_enabled = False
        await loop.run(
            messages=[{"role": "user", "content": "run"}],
            on_approval_request=approval_cb,
        )

    approval_cb.assert_not_called()
    loop._registry.execute.assert_called_once()


# --- No callback (non-Telegram / programmatic callers) ---

@pytest.mark.asyncio
async def test_no_callback_risky_tool_executes_directly():
    """When on_approval_request is None (e.g. tests, scripts), risky tools run without blocking."""
    loop = _make_loop(
        llm_responses=[_tool_call_response("run_python", {"code": "1+1"}), "2"],
        tool_result=ToolResult(tool_name="run_python", output="2", success=True),
    )

    with patch("brain.agent_loop.settings") as mock_settings:
        mock_settings.approval_gate_enabled = True
        result = await loop.run(
            messages=[{"role": "user", "content": "calc"}],
            on_approval_request=None,
        )

    loop._registry.execute.assert_called_once()
    assert result == "2"


# --- Rejected message appears in tool history ---

@pytest.mark.asyncio
async def test_rejected_tool_appends_rejection_message():
    """After rejection the loop must continue (not crash) and LLM sees rejection."""
    loop = _make_loop(
        llm_responses=[
            _tool_call_response("execute_file_organization", {"folder": "/tmp"}),
            "No problem, I won't organize.",
        ],
        tool_result=ToolResult(tool_name="execute_file_organization", output="plan", success=True),
    )
    approval_cb = AsyncMock(return_value=False)

    with patch("brain.agent_loop.settings") as mock_settings:
        mock_settings.approval_gate_enabled = True
        result = await loop.run(
            messages=[{"role": "user", "content": "organize /tmp"}],
            on_approval_request=approval_cb,
        )

    assert "won't organize" in result
    loop._registry.execute.assert_not_called()
