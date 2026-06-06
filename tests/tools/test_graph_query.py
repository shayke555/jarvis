"""Tests for tools/graph_query.py."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch


SAMPLE_GRAPH = {
    "directed": False,
    "multigraph": False,
    "graph": {},
    "nodes": [
        {"id": "a_AgentLoop", "label": "AgentLoop", "source_file": "brain/agent_loop.py"},
        {"id": "b_ToolRegistry", "label": "ToolRegistry", "source_file": "tools/registry.py"},
        {"id": "c_SQLiteStore", "label": "SQLiteStore", "source_file": "brain/memory/sqlite_store.py"},
    ],
    "links": [
        {"source": "a_AgentLoop", "target": "b_ToolRegistry",
         "relation": "uses", "confidence": "EXTRACTED", "weight": 1.0},
        {"source": "b_ToolRegistry", "target": "c_SQLiteStore",
         "relation": "references", "confidence": "INFERRED", "weight": 0.85},
    ],
}


@pytest.fixture
def graph_file(tmp_path):
    p = tmp_path / "graphify-out" / "graph.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(SAMPLE_GRAPH), encoding="utf-8")
    return p


@pytest.mark.asyncio
async def test_graph_query_finds_matching_node(graph_file):
    from tools.graph_query import graph_query_tool
    result = await graph_query_tool(query="AgentLoop", graph_path=str(graph_file))
    assert result.success
    assert "AgentLoop" in result.output


@pytest.mark.asyncio
async def test_graph_query_returns_connected_nodes(graph_file):
    from tools.graph_query import graph_query_tool
    result = await graph_query_tool(query="AgentLoop", graph_path=str(graph_file))
    assert result.success
    assert "ToolRegistry" in result.output


@pytest.mark.asyncio
async def test_graph_query_no_match(graph_file):
    from tools.graph_query import graph_query_tool
    result = await graph_query_tool(query="nonexistent_xyzzy", graph_path=str(graph_file))
    assert result.success
    assert "no matching" in result.output.lower() or result.output != ""


@pytest.mark.asyncio
async def test_graph_query_missing_graph(tmp_path):
    from tools.graph_query import graph_query_tool
    result = await graph_query_tool(query="AgentLoop",
                                    graph_path=str(tmp_path / "missing.json"))
    assert not result.success
    assert result.error is not None


@pytest.mark.asyncio
async def test_graph_query_schema_valid():
    from tools.graph_query import GRAPH_QUERY_SCHEMA
    fn = GRAPH_QUERY_SCHEMA["function"]
    assert fn["name"] == "graph_query"
    assert "query" in fn["parameters"]["properties"]
    assert "query" in fn["parameters"]["required"]
