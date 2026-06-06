"""Graph query tool — lets AgentLoop answer architecture questions from graphify-out/graph.json."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from tools.registry import ToolResult

logger = logging.getLogger(__name__)

_DEFAULT_GRAPH = Path(__file__).parent.parent / "graphify-out" / "graph.json"
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
_MAX_NODES = 20
_MAX_QUERY_LEN = 200


GRAPH_QUERY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "graph_query",
        "description": (
            "Search the JARVIS knowledge graph for architecture, code relationships, "
            "and project structure. Use when asked: 'how does X work', 'what calls Y', "
            "'where is Z defined', or any codebase architecture question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for — component name, concept, or question",
                },
            },
            "required": ["query"],
        },
    },
}


def _load_graph(graph_path: str) -> tuple[dict, dict]:
    """Load graph.json → (nodes_by_id, adjacency list). Raises on error."""
    resolved = Path(graph_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Graph not found: {resolved}")
    data = json.loads(resolved.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    adj: dict[str, list[dict]] = {nid: [] for nid in nodes}
    for link in data.get("links", []):
        src = link.get("source")
        tgt = link.get("target")
        if src in adj and tgt in nodes:
            adj[src].append({"target": tgt, "relation": link.get("relation", ""),
                              "confidence": link.get("confidence", "")})
        if tgt in adj and src in nodes:
            adj[tgt].append({"target": src, "relation": link.get("relation", ""),
                              "confidence": link.get("confidence", "")})
    return nodes, adj


def _bfs(nodes: dict, adj: dict, start_ids: list[str], depth: int = 2) -> set[str]:
    visited = set(start_ids)
    frontier = set(start_ids)
    for _ in range(depth):
        next_f: set[str] = set()
        for nid in frontier:
            for edge in adj.get(nid, []):
                nb = edge["target"]
                if nb not in visited:
                    next_f.add(nb)
        # Cap before update so visited never exceeds _MAX_NODES
        remaining = _MAX_NODES - len(visited)
        next_f = set(list(next_f)[:remaining])
        visited.update(next_f)
        frontier = next_f
        if len(visited) >= _MAX_NODES:
            break
    return visited


def _sanitize_query(query: str) -> str:
    """Strip control characters and truncate — prevents query payload echoed back to agent."""
    clean = "".join(c for c in query if c.isprintable())
    return clean[:_MAX_QUERY_LEN]


def _format_result(nodes: dict, adj: dict, found: set[str], query: str) -> str:
    safe_query = _sanitize_query(query)
    lines = [f"Graph query: '{safe_query}' — {len(found)} relevant nodes\n"]
    for nid in list(found)[:_MAX_NODES]:
        d = nodes[nid]
        label = d.get("label", nid)
        src = d.get("source_file", "")
        edges = adj.get(nid, [])
        conn = ", ".join(
            f"{e['relation']}→{nodes[e['target']].get('label', e['target'])[:20]}"
            for e in edges[:3]
            if e["target"] in found
        )
        lines.append(f"  {label} [{src}]" + (f"\n    connections: {conn}" if conn else ""))
    return "\n".join(lines)


async def graph_query_tool(query: str, graph_path: str | None = None) -> ToolResult:
    # graph_path is not in the LLM schema — only used internally/tests.
    # Default path is always within project root (validated at module load time).
    path = graph_path or str(_DEFAULT_GRAPH)
    try:
        nodes, adj = _load_graph(path)
    except FileNotFoundError as e:
        return ToolResult(tool_name="graph_query", output="", success=False, error=str(e))
    except Exception as e:
        logger.error("graph_query load failed: %s", e)
        return ToolResult(tool_name="graph_query", output="", success=False, error=str(e))

    terms = [t.lower() for t in query.split() if len(t) > 2]
    scored: list[tuple[int, str]] = []
    for nid, ndata in nodes.items():
        label = ndata.get("label", "").lower()
        src = ndata.get("source_file", "").lower()
        score = sum(1 for t in terms if t in label or t in src)
        if score > 0:
            scored.append((score, nid))
    scored.sort(reverse=True)

    if not scored:
        return ToolResult(
            tool_name="graph_query",
            output=f"No matching nodes found for: '{query}'. Try broader terms.",
            success=True,
        )

    start_ids = [nid for _, nid in scored[:3]]
    subgraph = _bfs(nodes, adj, start_ids, depth=2)
    output = _format_result(nodes, adj, subgraph, query)
    return ToolResult(tool_name="graph_query", output=output, success=True)
