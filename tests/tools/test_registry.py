from tools.registry import ToolResult, ToolRegistry


def test_tool_result_fields():
    r = ToolResult(tool_name="web_search", output="found it", success=True)
    assert r.success is True
    assert r.tool_name == "web_search"
    assert r.output == "found it"
    assert r.error is None


def test_tool_result_failure():
    r = ToolResult(tool_name="web_search", output="", success=False, error="timeout")
    assert r.success is False
    assert r.error == "timeout"


def test_registry_register_and_get():
    reg = ToolRegistry.__new__(ToolRegistry)
    reg._tools = {}

    async def dummy_tool(query: str) -> ToolResult:
        return ToolResult(tool_name="dummy", output=query, success=True)

    schema = {"type": "function", "function": {"name": "dummy", "parameters": {}}}
    reg.register(schema, dummy_tool)

    tools = reg.get_groq_tools()
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "dummy"


def test_registry_unknown_tool_returns_error():
    import asyncio

    reg = ToolRegistry.__new__(ToolRegistry)
    reg._tools = {}

    result = asyncio.run(reg.execute("nonexistent", {}))
    assert result.success is False
    assert "Unknown tool" in result.error
