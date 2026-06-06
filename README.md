# JARVIS — Personal AI Agent

An autonomous AI agent that runs continuously, monitors your projects, reads your emails, tracks trading signals, and delivers a morning briefing — all via Telegram.

Built with Python, async LangGraph-style agent loop, Groq + Gemini LLM routing, and a Streamlit dashboard.

---

## What It Does

| Feature | Description |
|---------|-------------|
| **Morning Briefing** | Daily Telegram summary: emails, tasks, trading signals, GitHub trends |
| **Gmail Monitor** | IMAP scan → AI classifies emails into job/lead/money/action/noise |
| **LedgerAlpha Bridge** | Reads trading signals from an algo trading system, surfaces alerts |
| **Agent Loop** | ReAct-style loop: LLM → tool calls → observe → respond |
| **Task Brain** | Persistent task management per project, with streak tracking |
| **GitHub Trending** | Daily digest of trending repos in your tech stack |
| **Streamlit Dashboard** | Real-time project health, tasks, signals, and agent chat |

---

## Architecture

```
bot.py (entry point)
├── brain/
│   ├── agent_loop.py       ← ReAct loop: think → tool → observe
│   ├── llm_router.py       ← Routes between Groq (fast) and Gemini (long context)
│   ├── context_manager.py  ← System prompt + memory injection
│   └── task_brain.py       ← SQLite-backed task management
├── connectors/
│   ├── gmail_bridge.py     ← IMAP scan + Groq email classification
│   ├── ledger_bridge.py    ← Reads signals/*.json from trading system
│   └── registry.py         ← Connector registry pattern
├── tools/
│   ├── search.py           ← Tavily / Brave Search fallback chain
│   ├── files.py            ← Safe file read/write with path guard
│   ├── browser.py          ← Headless browsing
│   └── graph_query.py      ← Query project knowledge graphs
├── monitors/
│   ├── github_trending.py  ← GitHub API trending repos
│   └── project_health.py   ← Staleness detection per project
├── scheduler/
│   ├── daily_briefing.py   ← APScheduler: 07:30 morning briefing
│   └── weekly_learning.py  ← Weekly skill review
├── interfaces/
│   └── telegram_bot.py     ← python-telegram-bot v20 async handlers
└── dashboard.py            ← Streamlit multi-project dashboard
```

---

## Stack

- **LLM**: Groq (llama-3.3-70b) + Gemini 2.0 Flash (long-context fallback)
- **Agent**: Custom async ReAct loop (tool calling via Groq function-calling API)
- **Memory**: ChromaDB (semantic) + SQLite (structured)
- **Bot**: python-telegram-bot v20 (async)
- **Dashboard**: Streamlit
- **Scheduler**: APScheduler
- **Settings**: pydantic-settings (env-file based)

---

## Setup

```bash
# 1. Clone and install
git clone https://github.com/shayke555/jarvis.git
cd jarvis
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in your API keys (Groq, Gemini, Telegram, etc.)

# 3. Run
python bot.py          # Full agent + Telegram bot
streamlit run dashboard.py   # Dashboard only
```

---

## Key Design Decisions

**LLM Routing** — Groq handles most requests (fast, cheap). Gemini takes over for long-context tasks (>50k tokens) or document analysis. Rate limit errors auto-fallback to Gemini.

**Email Classification** — Single batched Groq call per scan (not per email). Email bodies wrapped in `<email_body>` tags to mitigate prompt injection.

**Path Safety** — File tools validate against `PROJECTS_BASE_PATH` from env. Rejects `..` traversal attempts before the LLM can be jailbroken into reading sensitive files.

**Connector Registry** — All data connectors register via `registry.py`. The scheduler calls connectors by name, not by import — makes adding new sources (Slack, Calendar, etc.) a one-file change.

---

## Project Status

| Phase | Status |
|-------|--------|
| A — Core brain + Telegram | ✅ Done |
| B — Voice + Windows startup | ✅ Done |
| C — Gmail + LedgerAlpha bridge | ✅ Done |
| D — Agent tools (search, files, browser, graph query) | ✅ Done |
| E — Dashboard v2 + task brain | ✅ Done |
| F — Agent-based project monitoring | 🔄 In progress |

---

## Requirements

See [requirements.txt](requirements.txt). Key dependencies:

```
groq
google-genai
python-telegram-bot>=20
streamlit
apscheduler
chromadb
pydantic-settings
httpx
```
