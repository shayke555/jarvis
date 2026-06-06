import pytest
from tools.code_runner import run_python_tool, RUN_PYTHON_SCHEMA


def test_schema_valid():
    assert RUN_PYTHON_SCHEMA["function"]["name"] == "run_python"
    assert "code" in RUN_PYTHON_SCHEMA["function"]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_run_simple_code():
    result = await run_python_tool(code="print('hello from jarvis')")
    assert result.success is True
    assert "hello from jarvis" in result.output


@pytest.mark.asyncio
async def test_run_arithmetic():
    result = await run_python_tool(code="print(2 + 2)")
    assert result.success is True
    assert "4" in result.output


@pytest.mark.asyncio
async def test_run_code_with_error():
    result = await run_python_tool(code="raise ValueError('test error')")
    assert result.success is False
    assert result.error is not None
    assert "ValueError" in result.error


@pytest.mark.asyncio
async def test_run_code_timeout():
    result = await run_python_tool(code="import time; time.sleep(60)", timeout=1)
    assert result.success is False
    assert result.error is not None
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_run_code_no_output():
    result = await run_python_tool(code="x = 1 + 1")
    assert result.success is True
    assert result.output  # should return "(no output)" or similar
