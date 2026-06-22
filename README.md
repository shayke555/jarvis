# JARVIS — Personal AI Agent

Personal AI agent הרץ לצמיתות על Windows. מדבר דרך Telegram ודשבורד Streamlit.
100% חינמי — Groq free tier + local tools.

---

## מסמכים

| קובץ | תפקיד |
|------|--------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | איך הכל עובד — data flow, modules, security |
| [`ROADMAP.md`](ROADMAP.md) | מה הושלם, מה נשאר, החלטות ארכיטקטוניות |
| [`context.md`](context.md) | מצב סשן נוכחי — Next Step + Blockers |
| [`CLAUDE.md`](CLAUDE.md) | הוראות ל-Claude Code |

---

## הפעלה

```bash
python bot.py                    # Telegram bot + scheduler
streamlit run dashboard.py       # Dashboard (localhost:8501)
python -m pytest tests/ -v       # Tests (174 green)
```

## Setup ראשוני

```bash
pip install -r requirements.txt
cp .env.example .env
# מלא API keys ב-.env
python bot.py
```

## פקודות Telegram

| פקודה | תפקיד |
|-------|--------|
| `/start` | JARVIS online |
| `/status` | סטטוס + memory stats |
| `/summarize <path>` | סיכום קובץ PDF/DOCX/TXT |
| `/organize <folder>` | תוכנית ארגון תיקייה (dry-run) |
| `/jobs` | מועמדויות פתוחות מ-PROJECT-CV |
| `/signals` | איתותי LedgerAlpha |
| `/remember <text>` | שמור עובדה בזיכרון |
| כל הודעה חופשית | Agent loop עם tool use |

---

## Stack

- **LLM:** Groq llama-3.3-70b + Gemini 2.0 Flash (fallback)
- **Bot:** python-telegram-bot v20 async
- **Memory:** SQLite memory blocks + ChromaDB semantic
- **Dashboard:** Streamlit
- **Scheduler:** APScheduler
