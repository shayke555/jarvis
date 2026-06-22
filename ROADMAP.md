# JARVIS — Roadmap
_Updated: 2026-06-22_

---

## מה הושלם

| Phase | תיאור | תאריך | טסטים |
|-------|--------|-------|-------|
| **A** | Core Brain: FastAPI, Groq/Gemini router, SQLite, ChromaDB | 2026-05-01 | — |
| **B** | Voice: Groq Whisper STT, edge-tts, OpenWakeWord | 2026-05-01 | — |
| **C-0** | TaskBrain + LedgerAlpha bridge + morning briefing v2 | 2026-05-10 | 16 |
| **D** | Agent Tool System: ReAct loop, ToolRegistry, tools/search/files/browser | 2026-05-17 | 49 |
| **E** | Gmail bridge + graph_query_tool + Dashboard v2 | 2026-05-18 | 91 |
| **F+G** | Neural Interface Dashboard (Streamlit), daily briefing live | 2026-05-20 | 96 |
| **Phase 1** | Memory Blocks: dynamic human/persona/project blocks, block_updater (auto fact-extraction) | 2026-06-08 | 148 |
| **Phase 6** | Document Intelligence: document_reader (PDF/DOCX), organizer (dry-run), /summarize /organize | 2026-06-08 | 148 |
| **Phase 2** | Approval Gate: InlineKeyboard ✅/❌ before risky tools, asyncio.Future pattern | 2026-06-22 | 156 |
| **Phase 4** | Proactivity: detect_stuck_projects(), proactive_nudge_job() 09:00 daily | 2026-06-22 | 163 |
| **Phase 5** | Career/Trading bridges: cv_bridge → /jobs, ledger full signals → /signals | 2026-06-22 | 174 |

**גרסה נוכחית: 174 טסטים ירוקים**

---

## נשאר לבנות

### 🔴 עדיפות גבוהה

#### Phase 6 — השלמה: אישור להזזת קבצים
- `organize_files_tool` כרגע dry-run בלבד (לא מזיז קבצים)
- ברגע ש-Phase 2 (Approval Gate) יציב → להפעיל execution path
- **Blocker:** בדוק ש-Phase 2 עובד בפועל דרך טלגרם לפני

#### Gmail Integration (Phase C נדחה)
- `connectors/gmail_bridge.py` קיים אבל לא מחובר לבוט
- לחבר `/gmail` command + יומן AI סיווג מיילים
- **Blocker:** Google App Password צריך הגדרה ב-.env

---

### 🟡 עדיפות בינונית

#### Phase 5 — השלמה: Dashboard tabs
- `dashboard.py` עדיין מציג LedgerAlpha רק כ-widget קטן בOverview
- צריך: טאב "📈 מניות" מלא + טאב "💼 קריירה"
- כרגע `/jobs` ו-`/signals` עובדים בטלגרם — dashboard בלבד חסר

#### Phase 3 — Local-First LLM (Ollama) — **דחוי**
- Groq free tier מספיק לשי כרגע
- מודל מקומי יהיה פחות טוב
- **החלטה:** לחכות עד שיהיה rate-limit אמיתי

---

### 🟢 עדיפות נמוכה / רעיונות עתידיים

#### Instagram Feeder (תוכנית שמורה ב-`docs/superpowers/plans/`)
- Instagram link → yt-dlp → Groq classify → stocks/learning DB
- רלוונטי לחיבור עם LedgerAlpha sentiment

#### Windows Service (NSSM)
- כרגע: Task Scheduler מריץ `bot.py` בסטארטאפ
- NSSM יאפשר restart אוטומטי + service management
- לא דחוף — Task Scheduler עובד

#### Calendar Integration
- חיבור Google Calendar → JARVIS יכול לקרוא פגישות לתוך briefing
- דחוי (n8n יכול לטפל)

---

## החלטות ארכיטקטוניות שנקבעו

| החלטה | סיבה |
|-------|-------|
| Groq בלבד (לא Ollama) | Free tier מספיק, מודל 70B עדיף על מקומי קטן |
| Approval Gate = InlineKeyboard (לא text confirm) | UX — לחיצה אחת, לא להקליד "yes" |
| organizer = dry-run בלבד עד Phase 2 יציב | Safety — לא לסכן קבצים לפני שהגייט הוכח |
| Memory blocks (Letta pattern) > static YAML | הקונטקסט מתעדכן אוטומטית, YAML מיושן |
| PROJECTS_BASE_PATH = C:\Users\shayg\Projects | הגבלת גישה לתיקיית הפרויקטים בלבד |
| 100% free stack | מדיניות קבועה — ללא Tavily/Brave/Exa בתשלום |

---

## הקובץ הזה vs. קבצים אחרים

| קובץ | תפקיד |
|------|--------|
| `ROADMAP.md` (זה) | מה הושלם, מה נשאר, החלטות |
| `ARCHITECTURE.md` | איך הכל עובד — data flow, modules, security |
| `context.md` | מצב סשן — Next Step + Blockers (מתעדכן בסגירת סשן) |
| `STATUS.md` | 5 שורות — bridge ל-Claude Desktop |
| `README.md` | הסבר כללי קצר + setup |
| `CLAUDE.md` | הוראות ל-Claude בלבד |
