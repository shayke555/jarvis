# Phase D — פקודות מוכנות לClaudeCode
_העתק-הדבק ישירות ל-Claude Code ב-VS Code_

---

## D1 — הוסף API Keys לconfig

```
Read config/settings.py and .env.example.

Add these new API key settings to config/settings.py under the existing keys:
- TAVILY_API_KEY: str = ""           # https://app.tavily.com
- BRAVE_SEARCH_API_KEY: str = ""     # https://brave.com/search/api/
- EXA_API_KEY: str = ""              # https://exa.ai
- N8N_WEBHOOK_BASE_URL: str = ""     # e.g. http://localhost:5678/webhook

Also add them as empty placeholders to .env.example (not .env).

Follow the exact same pattern as existing keys in the file.
Confirm changes.
```

---

## D2 — צור tools/registry.py

```
Create tools/registry.py with:

1. A ToolResult dataclass:
   - success: bool
   - output: str
   - error: str | None = None
   - tool_name: str = ""

2. A ToolRegistry class:
   - __init__: initializes empty dict of registered tools
   - register(name: str, func: callable, description: str): adds tool
   - execute(name: str, **kwargs) -> ToolResult: runs tool safely, catches all exceptions
   - list_tools() -> list[dict]: returns [{name, description}] for all registered tools

Use Python dataclasses. No external dependencies.
Add a module docstring explaining this is the central tool dispatcher for JARVIS agent loop.
Write to tools/registry.py.
Then write a test in tests/test_registry.py that:
- Creates a registry
- Registers a dummy tool
- Executes it successfully
- Tests error handling when tool raises exception
Run pytest tests/test_registry.py -v and confirm it passes.
```

---

## D3 — שדרג tools/search.py

```
Read the current tools/search.py.
Read config/settings.py to understand available API keys.

Upgrade search.py to implement a fallback chain:
1. Try Tavily (if TAVILY_API_KEY is set) — returns structured results
2. Fallback: DuckDuckGo (always available, no key needed)
3. Fallback: Brave Search (if BRAVE_SEARCH_API_KEY is set)

Create a function: search_web(query: str, max_results: int = 5) -> ToolResult
- Returns ToolResult with formatted search results as output
- Logs which provider was used
- Never crashes silently — always returns ToolResult with success=False + error message on failure

Register this function in ToolRegistry when the module loads.
Follow error-handler skill: all exceptions logged + raised properly.
Add tests in tests/test_search.py for the fallback logic.
Run tests and confirm.
```

---

## D4 — צור tools/files.py

```
Create tools/files.py with these functions, each returning ToolResult:

1. read_file(path: str) -> ToolResult
   - Reads file content as text
   - Validates path exists and is within allowed directories
   - Allowed: PROJECT-JARVIS directory and its subdirectories only

2. write_file(path: str, content: str) -> ToolResult
   - Writes content to file
   - Creates parent directories if needed
   - NEVER writes to .env or settings files

3. list_files(directory: str, pattern: str = "*") -> ToolResult
   - Lists files matching pattern
   - Returns formatted list

Add module-level ALLOWED_DIRS list = [PROJECT-JARVIS root].
Register all three functions in ToolRegistry.
Write tests in tests/test_files.py.
```

---

## D7 — agent_loop.py (אחרי D2-D6 מוכנים)

```
Read context.md and docs/superpowers/plans/2026-05-10-jarvis-agent-tools.md first.

Create agents/agent_loop.py implementing a ReAct loop:

1. JarvisAgent class:
   - __init__(registry: ToolRegistry, llm_router, memory_store)
   - run(user_message: str, session_id: str) -> str
     - Saves user message to ChromaDB memory
     - Builds system prompt with: tool list, recent memory, shay_context
     - Sends to LLM with available tools
     - Parses tool calls from LLM response
     - Executes tools via registry
     - Loops until final response (max 5 iterations)
     - Returns final answer string

2. The system prompt must include:
   - Shay's context (from config/shay_context.yaml)
   - List of available tools and their descriptions
   - Last 3 relevant memories from ChromaDB
   - Today's date and time

3. Tool call format: LLM should output JSON blocks like:
   {"tool": "search_web", "args": {"query": "...", "max_results": 3}}

Wire up with existing: brain/chroma_store.py + brain/sqlite_store.py + config/llm_router.py

Write one integration test that runs the agent with a mock LLM.
```

---

## כדי להתחיל — הדבק זה ל-Claude Code:

```
I'm working on PROJECT-JARVIS Phase D (Agent Tool System).
Read CLAUDE.md and context.md first to understand the project.
Then implement Task D2: create tools/registry.py exactly as described in docs/PHASE_D_COMMANDS.md under section "D2".
Follow all engineering principles in CLAUDE.md. 
Run tests before finishing.
```
