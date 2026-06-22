from __future__ import annotations

import json
import logging
from typing import Callable, Coroutine, Any

from brain.llm_router import LLMRouter
from config.settings import settings
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 5

# Tools that mutate the filesystem or execute arbitrary code — require explicit
# user approval before running (when approval_gate_enabled=True).
_RISKY_TOOLS = {"run_python", "write_file", "execute_file_organization"}

ApprovalCallback = Callable[[str, dict], Coroutine[Any, Any, bool]]


class AgentLoop:
    """ReAct loop: LLM decides → tool executes → LLM reflects → answer.

    Runs up to _MAX_TOOL_ROUNDS tool calls before forcing a final answer.
    Risky tools (run_python, write_file, organize_files) require explicit
    approval via on_approval_request before executing.
    """

    def __init__(self, llm: LLMRouter, registry: ToolRegistry) -> None:
        self._llm = llm
        self._registry = registry

    async def run(
        self,
        messages: list[dict],
        context_tokens: int = 0,
        on_tool_call: Callable[[str], Coroutine[Any, Any, None]] | None = None,
        on_approval_request: ApprovalCallback | None = None,
    ) -> str:
        """Run until LLM returns a text answer or max rounds hit.

        on_approval_request: called before any risky tool — returns True (approved)
        or False (rejected). If None, risky tools execute without confirmation
        (e.g. programmatic callers, tests).
        """
        working = list(messages)
        tools = self._registry.get_groq_tools()

        for round_num in range(_MAX_TOOL_ROUNDS):
            response = await self._llm.chat_with_tools(
                messages=working,
                tools=tools,
                context_tokens=context_tokens,
            )

            if isinstance(response, str):
                if response.strip():
                    return response
                logger.warning("LLM returned empty content with no tool calls — retrying without forced tools.")
                return await self._llm.chat(working, context_tokens=context_tokens)

            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                return "אני לא יודע כיצד לענות על זה."

            # Append assistant decision
            working.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function", "function": tc["function"]}
                    for tc in tool_calls
                ],
            })

            # Execute tools, append results
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}

                logger.info("Tool call round %d: %s(%s)", round_num + 1, tool_name, args)

                # Approval gate — ask before running risky tools
                if (
                    tool_name in _RISKY_TOOLS
                    and settings.approval_gate_enabled
                    and on_approval_request is not None
                ):
                    approved = await on_approval_request(tool_name, args)
                    if not approved:
                        logger.info("User rejected tool: %s", tool_name)
                        working.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": "User rejected execution.",
                        })
                        continue

                if on_tool_call:
                    await on_tool_call(f"🔧 {tool_name}...")

                result = await self._registry.execute(tool_name, args)
                working.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result.output if result.success else f"Error: {result.error}",
                })

        logger.warning("Agent loop hit max rounds (%d)", _MAX_TOOL_ROUNDS)
        return "הגעתי למגבלת הפעולות. נסה לנסח את הבקשה בצורה פשוטה יותר."
