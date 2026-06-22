# JARVIS — Architecture
_Updated: 2026-06-22_

> קרא קובץ זה בתחילת כל סשן לפני שנוגעים בקוד.

---

## מה זה JARVIS

Personal AI agent הרץ לצמיתות על מחשב של שי. מדבר דרך טלגרם ודשבורד Streamlit. אין עלות — 100% Groq free tier + local tools.

---

## Entry Points

| נקודת כניסה | פקודה | תפקיד |
|-------------|-------|--------|
| `bot.py` | `python bot.py` | Telegram bot + scheduler |
| `dashboard.py` | `streamlit run dashboard.py` | Streamlit multi-project UI |

---

## Data Flow מלא

```
משתמש (טלגרם)
    ↓ הודעה / פקודה
interfaces/telegram_bot.py
    ├── CommandHandlers: /start /status /brief /remember
    │                   /summarize /organize /jobs /signals
    ├── handle_text() → AgentLoop.run()
    │       ↓
    │   brain/agent_loop.py (ReAct loop)
    │       ├── LLMRouter.chat_with_tools()  ← Groq function-calling
    │       ├── ToolRegistry.execute(tool_name, args)
    │       │       ├── [RISKY → request_approval() → InlineKeyboard ✅/❌]
    │       │       └── [SAFE  → execute directly]
    │       └── returns str answer
    │
    ├── handle_voice() → Groq Whisper STT → handle_text
    └── handle_approval_callback() → resolves asyncio.Future

brain/context_manager.py
    ├── _build_system_prompt()
    │       ├── sqlite.get_all_blocks("human")    ← dynamic facts about Shay
    │       ├── sqlite.get_all_blocks("persona")  ← JARVIS personality
    │       ├── sqlite.get_all_blocks("project")  ← active project context
    │       └── chroma.search_memories()          ← episodic memory
    └── after chat: block_updater.maybe_update_human_block()
                        ↓ LLM extracts facts (confidence > 0.8)
                        ↓ dedup + upsert to SQLite memory_blocks
```

---

## Module Map

### `brain/`
| קובץ | תפקיד |
|------|--------|
| `agent_loop.py` | ReAct loop — LLM → tool → observe → answer. Max 5 rounds. |
| `llm_router.py` | Routes: Groq (default, fast) / Gemini (context > 50K tokens). Temperature 0.7. |
| `context_manager.py` | Builds system prompt from memory blocks + episodic ChromaDB. |
| `task_brain.py` | SQLite task management per project + streak counter. |
| `memory/sqlite_store.py` | SQLite CRUD: messages, tasks, preferences, **memory_blocks**. |
| `memory/block_updater.py` | Post-chat fact extraction (LLM call, confidence ≥ 0.8, dedup). |
| `memory/chroma_store.py` | ChromaDB semantic search over episodic memories. |

### `tools/`
| קובץ | tool name | סוג | מסוכן? |
|------|-----------|-----|--------|
| `search.py` | `web_search` | HTTP | ❌ |
| `files.py` | `read_file`, `list_dir` | FS read | ❌ |
| `files.py` | `write_file` | FS write | ✅ RISKY |
| `document_reader.py` | `read_document` | PDF/DOCX/TXT extract | ❌ |
| `organizer.py` | `organize_files` | dry-run plan only | ✅ RISKY |
| `code_runner.py` | `run_python` | subprocess exec | ✅ RISKY |
| `browser.py` | `browse_url` | HTTP scrape | ❌ |
| `graph_query.py` | `graph_query` | local JSON read | ❌ |
| `path_guard.py` | — | shared safe_path() | — |

> **RISKY tools** = require user approval via Telegram InlineKeyboard before execution.
> Gated by `settings.approval_gate_enabled` (default: True).

### `connectors/`
| קובץ | מה עושה |
|------|---------|
| `ledger_bridge.py` | Reads `PROJECT-SANTIMENT/engine/signals/*.json` — algo trading signals |
| `cv_bridge.py` | Reads `PROJECT-CV-PRIVTE` SQLite — job applications + pipeline |
| `gmail_bridge.py` | IMAP scan → Groq email classification |
| `registry.py` | Connector registry pattern |

### `monitors/`
| קובץ | מה עושה |
|------|---------|
| `project_health.py` | Scans `context.md` per project → staleness emoji 🟢🟡🔴. `detect_stuck_projects()` → stale + open next_step. |
| `github_trending.py` | GitHub API trending repos |

### `scheduler/`
| קובץ | מתי רץ | מה עושה |
|------|--------|---------|
| `daily_briefing.py` | 07:30 daily | Telegram: tasks + signals + health |
| `proactive_nudge.py` | 09:00 daily | אם פרויקט תקוע ≥5 ימים → שולח nudge (1/day cap) |
| `weekly_learning.py` | ראשון 08:00 | graphify --update + skills digest |

### `config/`
```
settings.py         ← כל ה-keys נטענים מ-.env דרך pydantic-settings
.env                ← secrets (never commit — gitignored)
.env.example        ← template ללא ערכים אמיתיים
shay_context.yaml   ← legacy, הוחלף ע"י memory blocks (נשמר כ-reference)
```

---

## Memory Architecture

```
ChromaDB (chroma_db/)
└── episodic memory: זיכרונות שיחה, facts שנשמרו ידנית (/remember)

SQLite (jarvis.db)
├── messages         ← היסטוריית שיחות
├── tasks            ← tasks per project
├── preferences      ← key/value pairs (incl. last_nudge_date)
└── memory_blocks    ← Letta-style dynamic memory
        ├── block_type=human   ← facts about Shay (auto-updated)
        ├── block_type=persona ← JARVIS personality spec
        └── block_type=project ← active project context
```

---

## Security Model

| מנגנון | פרטים |
|--------|--------|
| **Authorization** | `_is_authorized(update)` — רק `TELEGRAM_OWNER_CHAT_ID` מקבל תגובה |
| **Approval Gate** | RISKY_TOOLS = {run_python, write_file, organize_files} → InlineKeyboard ✅/❌ → asyncio.Future (timeout 60s → reject) |
| **Path Guard** | `tools/path_guard.safe_path()` — `is_relative_to(PROJECTS_BASE_PATH)` + reject `..` segments |
| **Secrets** | `.env` gitignored, pydantic-settings maps env vars, never hardcoded |
| **LLM injection** | Document content enters user-role only (not system prompt) — safe by design |

---

## Key Settings (.env)

```
GROQ_API_KEY=...
GEMINI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_OWNER_CHAT_ID=...
PROJECTS_BASE_PATH=C:\Users\shayg\Projects
CV_PROJECT_PATH=C:\Users\shayg\Projects\PROJECT-CV-PRIVTE
APPROVAL_GATE_ENABLED=true
APPROVAL_GATE_TIMEOUT_SECONDS=60
```

---

## Tests

```
pytest tests/ -v        # 174 tests, all green (2026-06-22)

tests/
├── brain/              # agent_loop, context_manager, memory blocks, block_updater, approval_gate
├── connectors/         # ledger_bridge, cv_bridge
├── interfaces/         # telegram commands (summarize, organize, jobs, signals)
├── monitors/           # project_health, proactive_nudge
├── scheduler/          # (future)
└── tools/              # search, files, document_reader, organizer, registry, browser, graph_query
```

---

## How to Run

```bash
cd C:\Users\shayg\Projects\PROJECT-JARVIS
python bot.py                    # Telegram bot + scheduler
streamlit run dashboard.py       # Dashboard (localhost:8501)
python -m pytest tests/ -v       # Test suite
```
