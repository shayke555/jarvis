from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.registry import ToolResult

logger = logging.getLogger(__name__)

RUN_PYTHON_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "Execute Python code and return the output. "
            "Use for calculations, data processing, or any task requiring code execution."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds to wait (default: 10)",
                    "default": 10,
                },
            },
            "required": ["code"],
        },
    },
}

_MAX_OUTPUT = 2000


async def run_python_tool(code: str, timeout: int = 10) -> ToolResult:
    """Execute Python code in an isolated subprocess with timeout."""

    def _run() -> tuple[str, str, int]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name
        try:
            proc = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
            )
            return proc.stdout[:_MAX_OUTPUT], proc.stderr[:_MAX_OUTPUT], proc.returncode
        except subprocess.TimeoutExpired:
            return "", "execution timeout exceeded", -1
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    try:
        stdout, stderr, exit_code = await asyncio.to_thread(_run)

        if exit_code == -1:
            return ToolResult(
                tool_name="run_python", output="", success=False,
                error="execution timeout exceeded",
            )
        if exit_code != 0:
            return ToolResult(
                tool_name="run_python", output=stdout, success=False,
                error=stderr or f"Exit code {exit_code}",
            )
        return ToolResult(
            tool_name="run_python",
            output=stdout.strip() or "(no output)",
            success=True,
        )
    except Exception as e:
        return ToolResult(tool_name="run_python", output="", success=False, error=str(e))
