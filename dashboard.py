"""JARVIS Mission Control — Neural Interface Dashboard.

Run: streamlit run dashboard.py
"""
from __future__ import annotations

import asyncio
import json
import random
import sys
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import streamlit.components.v1 as components

from dashboard_utils import (
    get_cross_project_summary,
    get_random_skills,
    load_skills_index,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JARVIS · Mission Control",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design system — Neural Interface ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Variables ─────────────────────────────────────────────────── */
:root {
  --void:       #040408;
  --deep:       #07070f;
  --surface:    #0d0d1a;
  --panel:      #111120;
  --border:     rgba(0,255,200,0.10);
  --border-hi:  rgba(0,255,200,0.28);
  --cyan:       #00ffc8;
  --cyan-dim:   rgba(0,255,200,0.55);
  --violet:     #8b5cf6;
  --violet-dim: rgba(139,92,246,0.50);
  --amber:      #fbbf24;
  --coral:      #f87171;
  --mint:       #10b981;
  --text:       #e2e2f0;
  --text-dim:   rgba(200,200,220,0.45);
  --text-mute:  rgba(200,200,220,0.22);
  --mono:       'JetBrains Mono', monospace;
  --sans:       'DM Sans', sans-serif;
  --display:    'Syne', sans-serif;
  --r:          14px;
  --r-sm:       9px;
  --glow-c:     0 0 24px rgba(0,255,200,0.15);
  --glow-v:     0 0 24px rgba(139,92,246,0.18);
}

/* ── Reset / Base ──────────────────────────────────────────────── */
.stApp {
  background: radial-gradient(ellipse 80% 60% at 20% 10%, rgba(0,255,200,0.03) 0%, transparent 60%),
              radial-gradient(ellipse 60% 50% at 80% 80%, rgba(139,92,246,0.04) 0%, transparent 60%),
              var(--void);
  font-family: var(--sans);
  color: var(--text);
}
.block-container { padding-top: 1.2rem !important; max-width: 1440px; }
#MainMenu, footer, header { visibility: hidden; }
* { box-sizing: border-box; }

/* ── Typography ────────────────────────────────────────────────── */
h1,h2,h3 { font-family: var(--display); }
.jarvis-wordmark {
  font-family: var(--display);
  font-weight: 800;
  font-size: 1.9rem;
  letter-spacing: -0.5px;
  background: linear-gradient(100deg, var(--cyan) 0%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
}
.jarvis-sub {
  font-family: var(--mono);
  font-size: 0.68rem;
  color: var(--text-mute);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-top: 3px;
}
.section-label {
  font-family: var(--mono);
  font-size: 0.62rem;
  font-weight: 600;
  color: var(--cyan-dim);
  text-transform: uppercase;
  letter-spacing: 3px;
  margin-bottom: 12px;
}

/* ── Header ────────────────────────────────────────────────────── */
.jarvis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 28px;
  background: linear-gradient(135deg, rgba(0,255,200,0.04) 0%, rgba(139,92,246,0.05) 100%);
  border: 1px solid var(--border);
  border-radius: var(--r);
  margin-bottom: 22px;
  backdrop-filter: blur(20px);
  position: relative;
  overflow: hidden;
}
.jarvis-header::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--cyan-dim), transparent);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.jarvis-clock {
  font-family: var(--mono);
  font-size: 0.82rem;
  color: var(--text-dim);
}

/* ── Streak badge ───────────────────────────────────────────────── */
.streak-badge {
  display: flex;
  align-items: center;
  gap: 7px;
  background: linear-gradient(135deg, rgba(251,191,36,0.12), rgba(251,191,36,0.06));
  border: 1px solid rgba(251,191,36,0.25);
  border-radius: 40px;
  padding: 5px 14px 5px 10px;
  font-family: var(--mono);
  font-size: 0.78rem;
  color: var(--amber);
}
.streak-flame { font-size: 1rem; animation: pulse-flame 2s ease-in-out infinite; }
@keyframes pulse-flame {
  0%,100% { transform: scale(1); }
  50%      { transform: scale(1.15) rotate(-3deg); }
}

/* ── Synaptic pulse (header decoration) ────────────────────────── */
.synapse-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.syn { width:6px; height:6px; border-radius:50%; background: var(--cyan); opacity:0.6;
  animation: syn-pulse 2.4s ease-in-out infinite; }
.syn:nth-child(2) { animation-delay:.4s; background: var(--violet); }
.syn:nth-child(3) { animation-delay:.8s; }
.syn:nth-child(4) { animation-delay:1.2s; background: var(--violet); }
@keyframes syn-pulse { 0%,100%{opacity:.25;transform:scale(.8)} 50%{opacity:1;transform:scale(1.2)} }

/* ── Cards ─────────────────────────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 18px 22px;
  margin-bottom: 14px;
  transition: border-color .2s, box-shadow .2s;
  position: relative;
  overflow: hidden;
}
.card:hover { border-color: var(--border-hi); box-shadow: var(--glow-c); }
.card-red    { border-color: rgba(248,113,113,.35) !important; }
.card-yellow { border-color: rgba(251,191,36,.30) !important; }
.card-green  { border-color: rgba(16,185,129,.30) !important; }
.card-violet { border-color: rgba(139,92,246,.30) !important; }

.card-label {
  font-family: var(--mono);
  font-size: 0.62rem;
  font-weight: 600;
  color: var(--text-mute);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 5px;
}
.card-value {
  font-size: 0.92rem;
  color: var(--text);
  line-height: 1.55;
}
.card-title {
  font-family: var(--display);
  font-size: 0.98rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── Staleness badges ──────────────────────────────────────────── */
.stale-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 9px;
  border-radius: 20px;
  font-family: var(--mono);
  font-size: 0.65rem;
  font-weight: 600;
}
.stale-green  { background: rgba(16,185,129,.12); color: var(--mint); border:1px solid rgba(16,185,129,.25); }
.stale-yellow { background: rgba(251,191,36,.10); color: var(--amber); border:1px solid rgba(251,191,36,.25); }
.stale-red    { background: rgba(248,113,113,.12); color: var(--coral); border:1px solid rgba(248,113,113,.25); }

/* ── Notifications ──────────────────────────────────────────────── */
.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--r-sm);
  margin-bottom: 7px;
  font-size: 0.84rem;
  border: 1px solid transparent;
}
.notif-urgent { background:rgba(248,113,113,.07); border-color:rgba(248,113,113,.18); }
.notif-warn   { background:rgba(251,191,36,.06);  border-color:rgba(251,191,36,.16); }
.notif-info   { background:rgba(0,255,200,.04);   border-color:rgba(0,255,200,.12); }
.notif-icon { font-size: 1rem; line-height: 1.4; flex-shrink: 0; }

/* ── AI cards ───────────────────────────────────────────────────── */
.ai-card {
  background: linear-gradient(135deg, rgba(139,92,246,.07) 0%, rgba(0,255,200,.04) 100%);
  border: 1px solid var(--violet-dim);
  border-radius: var(--r);
  padding: 16px 20px;
  margin-bottom: 12px;
}
.ai-card-label {
  font-family: var(--mono);
  font-size: 0.6rem;
  font-weight: 600;
  color: rgba(139,92,246,.7);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: 8px;
}
.ai-card-text {
  font-size: 0.88rem;
  color: var(--text);
  line-height: 1.65;
}

/* ── Skill cards ─────────────────────────────────────────────────── */
.skill-card {
  background: linear-gradient(135deg, rgba(0,255,200,.04), rgba(139,92,246,.03));
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 14px 18px;
  margin-bottom: 10px;
  transition: border-color .2s, transform .15s;
  cursor: default;
}
.skill-card:hover { border-color: var(--border-hi); transform: translateY(-1px); }
.skill-name {
  font-family: var(--display);
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--cyan);
  margin-bottom: 4px;
}
.skill-slash {
  font-family: var(--mono);
  font-size: 0.68rem;
  color: var(--violet);
  margin-bottom: 6px;
}
.skill-desc {
  font-size: 0.78rem;
  color: var(--text-dim);
  line-height: 1.5;
}

/* ── Priority pills ─────────────────────────────────────────────── */
.p-high   { color:#f87171; font-size:.75rem; font-weight:700; }
.p-medium { color:#fbbf24; font-size:.75rem; font-weight:700; }
.p-low    { color:#10b981; font-size:.75rem; font-weight:700; }

/* ── Context block ──────────────────────────────────────────────── */
.context-block {
  background: rgba(4,4,8,.92);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: var(--r-sm);
  padding: 14px 18px;
  font-family: var(--mono);
  font-size: 0.76rem;
  color: rgba(200,200,220,.65);
  line-height: 1.75;
  max-height: 260px;
  overflow-y: auto;
  white-space: pre-wrap;
}

/* ── Divider ────────────────────────────────────────────────────── */
.glow-div {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-hi), transparent);
  margin: 20px 0;
}

/* ── Regime ─────────────────────────────────────────────────────── */
.regime-bull  { color: var(--mint); }
.regime-bear  { color: var(--coral); }
.regime-neutral { color: var(--text-dim); }

/* ── Streamlit widget overrides ─────────────────────────────────── */
.stButton>button {
  background: rgba(0,255,200,.07);
  border: 1px solid rgba(0,255,200,.22);
  color: var(--cyan);
  border-radius: var(--r-sm);
  font-family: var(--mono);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 14px;
  transition: background .18s, border-color .18s;
}
.stButton>button:hover {
  background: rgba(0,255,200,.14);
  border-color: rgba(0,255,200,.4);
}
.stTextInput>div>div>input {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  color: var(--text);
  font-family: var(--sans);
}
.stSelectbox>div>div {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
}
.stChatMessage { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ── Data loaders ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_projects():
    try:
        from monitors.project_health import scan_projects
        return scan_projects()
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def load_ledger():
    try:
        from connectors.ledger_bridge import fetch_ledger_signals
        return fetch_ledger_signals()
    except Exception as e:
        return {"status": "error", "data": None, "error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def load_trending():
    repos: list = []
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from monitors.github_trending import fetch_trending
            repos.extend(loop.run_until_complete(fetch_trending(days_back=7)))
        finally:
            loop.close()
    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=25)
    return repos


@st.cache_data(ttl=1800, show_spinner=False)
def get_llm_recommendation(project_name: str, context_text: str) -> str:
    if not context_text:
        return ""
    try:
        from config.settings import settings
        if not settings.groq_api_key:
            return "⚠️ GROQ_API_KEY not set"
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": (
                    "אתה JARVIS, העוזר של שי. נתח את ה-context.md ותן המלצה אחת "
                    "ספציפית ומיידית לסשן הבא — 2-3 משפטים, ישיר, עברית. "
                    "התמקד במה שהכי שווה לעשות עכשיו ולמה."
                )},
                {"role": "user", "content": f"פרויקט: {project_name}\n\n{context_text[:2500]}"},
            ],
            max_tokens=220,
            temperature=0.65,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ {type(e).__name__}: recommendation unavailable"


@st.cache_data(ttl=3600, show_spinner=False)
def get_project_summary(project_name: str, context_text: str) -> str:
    if not context_text:
        return ""
    try:
        from config.settings import settings
        if not settings.groq_api_key:
            return ""
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": (
                    "סכם את הפרויקט בדיוק בפורמט הבא (עברית קצרה, כל שדה שורה אחת):\n"
                    "**מה זה:** [משפט אחד]\n"
                    "**Stack:** [טכנולוגיות ראשיות, עד 6 מילים]\n"
                    "**הושלם:** [milestone אחרון]\n"
                    "**הבא:** [המשימה הבאה]"
                )},
                {"role": "user", "content": f"Project: {project_name}\n\n{context_text[:2500]}"},
            ],
            max_tokens=180,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ {type(e).__name__}: summary unavailable"


@st.cache_data(ttl=1800, show_spinner=False)
def cached_cross_project_summary(contexts_key: str, contexts_str: str) -> str:
    """Wrapper with cache key so result refreshes when contexts change."""
    import json as _json
    contexts = _json.loads(contexts_str)
    return get_cross_project_summary(contexts)


def read_context(project_name: str) -> str:
    try:
        from config.settings import settings
        base = Path(settings.projects_base_path)
    except Exception:
        base = Path.home() / "Projects"
    path = base / project_name / "context.md"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def staleness_class(emoji: str) -> str:
    return {"🟢": "stale-green", "🟡": "stale-yellow", "🔴": "stale-red"}.get(emoji, "stale-yellow")


def card_class(emoji: str) -> str:
    return {"🟢": "card-green", "🟡": "card-yellow", "🔴": "card-red"}.get(emoji, "")


def embed_project_graph(project_name: str, height: int = 480) -> None:
    """Embed graphify HTML if exists, else show placeholder with task button."""
    try:
        from config.settings import settings
        base = Path(settings.projects_base_path)
    except Exception:
        base = Path.home() / "Projects"
    graph_html = base / project_name / "graphify-out" / "graph.html"
    if graph_html.exists():
        html_content = graph_html.read_text(encoding="utf-8", errors="replace")
        components.html(html_content, height=height, scrolling=True)
    else:
        st.markdown(f"""
<div class="card" style="text-align:center;padding:36px 20px;">
  <div style="font-size:2.4rem;margin-bottom:10px;opacity:.4;">🧠</div>
  <div style="font-family:var(--mono);font-size:.72rem;color:var(--text-mute);letter-spacing:2px;text-transform:uppercase;">
    אין גרף ידע
  </div>
  <div style="font-size:.78rem;color:var(--text-mute);margin-top:6px;">
    הרץ <code>/graphify</code> בסשן Claude Code
  </div>
</div>""", unsafe_allow_html=True)
        if st.button(f"➕ הוסף משימה: /graphify", key=f"gfy_{project_name}"):
            from brain.task_brain import add_task
            add_task(
                area=project_name,
                description=f"הרץ /graphify ב-{project_name}",
                priority="medium",
            )
            st.success("✓ משימה נוספה")
            st.rerun()


def render_tasks(project_name: str) -> None:
    """Task view + add form for a project tab."""
    from brain.task_brain import get_tasks, mark_done, add_task
    PICONS = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    PLABELS = {"high": "🔴 גבוהה", "medium": "🟡 בינונית", "low": "🟢 נמוכה"}

    result = get_tasks(area=project_name)
    tasks = result["data"]["tasks"] if result["status"] == "ok" else []

    if tasks:
        for t in tasks:
            icon = PICONS.get(t.get("priority", "medium"), "🟡")
            due_str = f" · <span style='color:var(--text-mute);font-size:.72rem;'>{t['due_date']}</span>" if t.get("due_date") else ""
            col_a, col_b = st.columns([10, 1])
            with col_a:
                st.markdown(
                    f'<div class="notif-item notif-warn" style="margin-bottom:6px;">'
                    f'<span class="notif-icon">{icon}</span>'
                    f'<span style="font-size:.84rem;">{t["description"]}{due_str}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_b:
                if st.button("✓", key=f"done_{t['id']}_{project_name}"):
                    mark_done(t["id"])
                    st.rerun()
    else:
        st.markdown(
            '<div style="font-family:var(--mono);font-size:.72rem;color:var(--text-mute);'
            'padding:10px 0;">אין משימות פתוחות</div>',
            unsafe_allow_html=True,
        )

    with st.expander("➕ הוסף משימה"):
        with st.form(f"add_task_{project_name}", clear_on_submit=True):
            desc = st.text_input("תיאור המשימה", placeholder="לדוג׳: הרץ /graphify, תקן Bug #42...")
            c1, c2 = st.columns(2)
            with c1:
                priority = st.selectbox("עדיפות", ["high", "medium", "low"],
                                        format_func=lambda x: PLABELS[x])
            with c2:
                due = st.date_input("יעד (אופציונלי)", value=None)
            if st.form_submit_button("הוסף", use_container_width=True):
                if desc.strip():
                    add_task(
                        area=project_name,
                        description=desc.strip(),
                        priority=priority,
                        due_date=str(due) if due else None,
                    )
                    st.success("✓ נוסף")
                    st.rerun()


def get_notifications(projects) -> list[dict]:
    """Aggregate notifications from all sources."""
    from brain.task_brain import get_tasks
    notes = []
    # High-priority tasks
    result = get_tasks()
    if result["status"] == "ok":
        for t in result["data"]["tasks"]:
            if t.get("priority") == "high":
                notes.append({
                    "type": "urgent",
                    "icon": "🔴",
                    "text": f"{t['area']} — {t['description']}",
                })
    # Stale projects
    for p in projects:
        if p.staleness_days >= 5:
            notes.append({
                "type": "warn",
                "icon": "⚠️",
                "text": f"{p.name} לא עודכן {p.staleness_days} ימים",
            })
    # Missing graphs
    try:
        from config.settings import settings
        base = Path(settings.projects_base_path)
    except Exception:
        base = Path.home() / "Projects"
    for p in projects:
        if not (base / p.name / "graphify-out" / "graph.json").exists():
            notes.append({
                "type": "info",
                "icon": "📊",
                "text": f"{p.name} — אין גרף ידע · /graphify",
            })
    return notes


# ── JARVIS Brain (shared with Telegram — same memory, same tools) ────────────
@st.cache_resource(show_spinner=False)
def get_jarvis_brain():
    """Single shared ContextManager instance — same memory_blocks, ChromaDB,
    and LLM routing the Telegram bot uses. Cached across reruns (heavy to build:
    SQLite + ChromaDB + embeddings)."""
    from brain.context_manager import ContextManager
    return ContextManager()


def _run_chat(cm, user_message: str) -> str:
    """Run cm.chat() to completion from Streamlit's sync context.
    Mirrors the new-event-loop-in-thread pattern used by load_trending() above —
    Streamlit's main thread already has no running loop, but isolating in a
    thread keeps repeated chat calls safe across reruns."""
    result: dict = {}

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["reply"] = loop.run_until_complete(cm.chat(user_message, interface="dashboard"))
        except Exception as e:
            result["error"] = str(e)
        finally:
            loop.close()

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=120)
    if "error" in result:
        return f"⚠️ שגיאה: {result['error']}"
    return result.get("reply", "⚠️ JARVIS לא הגיב בזמן (timeout).")


# ── Bootstrap ─────────────────────────────────────────────────────────────────
from brain.task_brain import get_dashboard_streak, init_task_brain
init_task_brain()
streak_data = get_dashboard_streak()

projects    = load_projects()
ledger      = load_ledger()
all_skills  = load_skills_index()

# ── Header ────────────────────────────────────────────────────────────────────
now = datetime.now()
streak_n = streak_data["streak"]
flame = "🔥" if streak_n >= 3 else "✦"
st.markdown(f"""
<div class="jarvis-header">
  <div>
    <div class="synapse-row">
      <div class="syn"></div><div class="syn"></div>
      <div class="syn"></div><div class="syn"></div>
    </div>
    <div class="jarvis-wordmark">JARVIS</div>
    <div class="jarvis-sub">mission control · neural interface</div>
  </div>
  <div class="header-right">
    <div class="streak-badge">
      <span class="streak-flame">{flame}</span>
      <span>{streak_n} יום ברצף</span>
      <span style="opacity:.4;">·</span>
      <span style="opacity:.55;">{streak_data['total']} סה״כ</span>
    </div>
    <div class="jarvis-clock">{now.strftime('%A %d %b · %H:%M')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
PROJECT_ICONS = {
    "PROJECT-JARVIS":    "🤖",
    "PROJECT-SANTIMENT": "📈",
    "PROJECT-CV-PRIVTE": "🎯",
    "PROJECT-CASTRO":    "💼",
    "MESHEK-46":         "🌿",
    "UPGRADE_V2":        "⚡",
}
project_map = {p.name: p for p in projects}
tab_labels  = ["🏠 Overview"] + [
    f"{PROJECT_ICONS.get(p.name,'📁')} {p.name.replace('PROJECT-','')}"
    for p in projects
]
tabs = st.tabs(tab_labels)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 0 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:

    # ── Cross-project summary (what did I do) ──────────────────────────────
    if projects:
        all_ctx = {p.name: read_context(p.name) for p in projects}
        ctx_key  = str(hash(tuple(sorted((k, v[:100]) for k, v in all_ctx.items()))))
        ctx_json = json.dumps(all_ctx)

        st.markdown('<div class="section-label">📡 Status Across All Projects</div>', unsafe_allow_html=True)
        with st.spinner(""):
            summary_text = cached_cross_project_summary(ctx_key, ctx_json)
        if summary_text:
            st.markdown(
                f'<div class="card card-violet"><div class="card-value" style="line-height:1.9;">'
                f'{summary_text}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="glow-div"></div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        # ── Notifications ──────────────────────────────────────────────────
        notes = get_notifications(projects)
        st.markdown('<div class="section-label">🔔 Notifications</div>', unsafe_allow_html=True)
        if notes:
            for n in notes[:8]:
                cls = {"urgent": "notif-urgent", "warn": "notif-warn", "info": "notif-info"}.get(n["type"], "notif-info")
                st.markdown(
                    f'<div class="notif-item {cls}">'
                    f'<span class="notif-icon">{n["icon"]}</span>'
                    f'<span>{n["text"]}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="notif-item notif-info">'
                '<span class="notif-icon">✦</span>'
                '<span style="color:var(--text-mute);">הכל תקין — אין התראות</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="glow-div"></div>', unsafe_allow_html=True)

        # ── Project health cards ───────────────────────────────────────────
        st.markdown('<div class="section-label">🗂️ Project Health</div>', unsafe_allow_html=True)
        if not projects:
            st.info("No projects found.")
        for p in projects:
            sc  = staleness_class(p.staleness_emoji)
            cc  = card_class(p.staleness_emoji)
            icon = PROJECT_ICONS.get(p.name, "📁")
            days_txt = f"{p.staleness_days}d ago" if p.staleness_days > 0 else "today"
            import html as html_lib
            done_s = html_lib.escape((p.last_completed or "—")[:75])
            next_s = html_lib.escape((p.next_step    or "—")[:75])
            st.markdown(f"""
<div class="card {cc}">
  <div class="card-title">
    {icon} {p.name}
    <span class="stale-badge {sc}">{p.staleness_emoji} {days_txt}</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
    <div><div class="card-label">✅ Last completed</div><div class="card-value">{done_s}</div></div>
    <div><div class="card-label">▶️ Next step</div><div class="card-value">{next_s}</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    with col_right:
        # ── LedgerAlpha ────────────────────────────────────────────────────
        st.markdown('<div class="section-label">📈 LedgerAlpha</div>', unsafe_allow_html=True)
        if ledger["status"] == "ok":
            d = ledger["data"]
            regime = d.get("regime", "unknown")
            rcls = {"bull": "regime-bull", "bear": "regime-bear"}.get(regime.lower(), "regime-neutral")
            top = d.get("top_signal")
            top_html = ""
            if top:
                dir_icon = "↑" if top.get("direction") == "long" else ("↓" if top.get("direction") == "short" else "→")
                top_html = f"""<div style="margin-top:10px;">
  <div class="card-label">Top Signal</div>
  <div style="font-family:var(--mono);font-size:1.05rem;color:var(--text);">
    {top.get('ticker','?')} <span style="color:var(--amber);margin-left:6px;">{dir_icon} {top.get('score','?')}</span>
  </div></div>"""
            st.markdown(f"""
<div class="card">
  <div class="card-label">Regime</div>
  <div style="font-size:1.5rem;font-weight:800;font-family:var(--display);" class="{rcls}">{regime.upper()}</div>
  {top_html}
  <div style="margin-top:8px;font-size:.65rem;color:var(--text-mute);font-family:var(--mono);">
    {d.get('timestamp','')[:16]}
  </div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="card card-red"><div class="card-value">LedgerAlpha unavailable</div></div>', unsafe_allow_html=True)

        # ── GitHub trending ─────────────────────────────────────────────────
        st.markdown('<div class="section-label" style="margin-top:16px;">🌐 GitHub This Week</div>', unsafe_allow_html=True)
        with st.spinner(""):
            repos = load_trending()
        if repos:
            for repo in repos[:4]:
                desc_r = (repo.description or "")[:65]
                import html as html_lib2
                st.markdown(f"""
<div class="card" style="padding:12px 16px;margin-bottom:8px;">
  <div style="font-family:var(--display);font-weight:700;font-size:.84rem;color:var(--cyan);">{html_lib2.escape(repo.name)}</div>
  <div style="font-size:.72rem;color:var(--text-mute);margin-top:2px;">{html_lib2.escape(desc_r)}</div>
  <div style="font-family:var(--mono);font-size:.68rem;color:var(--amber);margin-top:5px;">⭐ {repo.stars:,}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="card"><div class="card-value" style="color:var(--text-mute);">No data (rate limit?)</div></div>', unsafe_allow_html=True)

    # ── Knowledge graph (JARVIS main) ─────────────────────────────────────
    st.markdown('<div class="glow-div"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">🧠 Knowledge Graph · JARVIS</div>', unsafe_allow_html=True)
    jarvis_graph = Path(__file__).parent / "graphify-out" / "graph.html"
    if jarvis_graph.exists():
        html_g = jarvis_graph.read_text(encoding="utf-8", errors="replace")
        components.html(html_g, height=560, scrolling=True)
    else:
        st.markdown('<div class="card"><div class="card-value" style="color:var(--text-mute);">Graph not found — run /graphify</div></div>', unsafe_allow_html=True)

    # ── Skills of the Day ─────────────────────────────────────────────────
    st.markdown('<div class="glow-div"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">📚 Skills of the Day</div>', unsafe_allow_html=True)

    if "skill_seed" not in st.session_state:
        st.session_state.skill_seed = random.randint(0, 99999)

    search_q = st.text_input("🔍 חפש skill / פקודה...", key="skill_search",
                              placeholder="debug · python · graph · api...")

    if search_q:
        sq = search_q.lower()
        shown_skills = [s for s in all_skills
                        if sq in s["name"].lower() or sq in s["description"].lower()
                        or sq in s["slash"].lower()]
    else:
        shown_skills = get_random_skills(all_skills, n=4, seed=st.session_state.skill_seed)

    if not search_q:
        if st.button("🔄 Shuffle"):
            st.session_state.skill_seed = random.randint(0, 99999)
            st.rerun()

    if shown_skills:
        cols_sk = st.columns(2)
        for idx, sk in enumerate(shown_skills[:8]):
            with cols_sk[idx % 2]:
                slash_line = f'<div class="skill-slash">{sk["slash"]}</div>' if sk["slash"] else ""
                with st.expander(f"**{sk['name']}**", expanded=False):
                    st.markdown(
                        f'{slash_line}'
                        f'<div class="skill-desc">{sk["description"]}</div>',
                        unsafe_allow_html=True,
                    )
                    if sk.get("skill_md") and Path(sk["skill_md"]).exists():
                        content = Path(sk["skill_md"]).read_text(encoding="utf-8", errors="replace")
                        st.code(content[:1800], language="markdown")
    else:
        st.markdown('<div style="color:var(--text-mute);font-size:.82rem;">לא נמצאו סקילים תואמים</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TABS 1..N — PER PROJECT
# ══════════════════════════════════════════════════════════════════════════════
for i, proj in enumerate(projects):
    with tabs[i + 1]:
        p    = proj
        sc   = staleness_class(p.staleness_emoji)
        cc   = card_class(p.staleness_emoji)
        icon = PROJECT_ICONS.get(p.name, "📁")
        days_txt = (
            f"{p.staleness_days} יום לאחר עדכון" if p.staleness_days > 1
            else ("עודכן היום" if p.staleness_days == 0 else "עודכן אתמול")
        )

        # ── Project header ─────────────────────────────────────────────────
        st.markdown(f"""
<div class="card {cc}" style="padding:22px 26px;margin-bottom:20px;">
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
    <div>
      <div style="font-family:var(--display);font-size:1.45rem;font-weight:800;color:var(--text);">
        {icon} {p.name}
      </div>
      <div style="margin-top:6px;">
        <span class="stale-badge {sc}">{p.staleness_emoji} {days_txt}</span>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        # ── Load context early ──────────────────────────────────────────────
        ctx = read_context(p.name)

        # ── Snapshot ────────────────────────────────────────────────────────
        if ctx:
            st.markdown('<div class="section-label">⚡ Project Snapshot</div>', unsafe_allow_html=True)
            with st.spinner(""):
                snapshot = get_project_summary(p.name, ctx)
            if snapshot:
                with st.container(border=True):
                    st.markdown(snapshot)

        # ── Status + AI Rec ─────────────────────────────────────────────────
        col1, col2 = st.columns(2, gap="medium")
        with col1:
            st.markdown('<div class="section-label">Status</div>', unsafe_allow_html=True)
            import html as _h
            st.markdown(f"""
<div class="card">
  <div class="card-label">✅ Last Completed</div>
  <div class="card-value" style="margin-bottom:14px;">{_h.escape(p.last_completed or "—")}</div>
  <div class="glow-div" style="margin:10px 0;"></div>
  <div class="card-label">▶️ Next Step</div>
  <div class="card-value">{_h.escape(p.next_step or "—")}</div>
</div>""", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="section-label">🤖 AI Recommendation</div>', unsafe_allow_html=True)
            if ctx:
                with st.spinner("JARVIS thinking..."):
                    rec = get_llm_recommendation(p.name, ctx)
                st.markdown(f"""
<div class="ai-card">
  <div class="ai-card-label">⚡ JARVIS · Next Session</div>
  <div class="ai-card-text">{_h.escape(rec)}</div>
</div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div class="card"><div class="card-value" style="color:var(--text-mute);">No context.md found</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="glow-div"></div>', unsafe_allow_html=True)

        # ── Knowledge Graph ─────────────────────────────────────────────────
        st.markdown('<div class="section-label">🧠 Knowledge Graph</div>', unsafe_allow_html=True)
        embed_project_graph(p.name, height=460)

        st.markdown('<div class="glow-div"></div>', unsafe_allow_html=True)

        # ── Tasks ───────────────────────────────────────────────────────────
        st.markdown('<div class="section-label">✅ Tasks</div>', unsafe_allow_html=True)
        render_tasks(p.name)

        # ── context.md ─────────────────────────────────────────────────────
        if ctx:
            st.markdown('<div class="glow-div"></div>', unsafe_allow_html=True)
            with st.expander("📄 context.md (full)", expanded=False):
                import html as _h2
                st.markdown(
                    f'<div class="context-block">{_h2.escape(ctx)}</div>',
                    unsafe_allow_html=True,
                )

# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED CHAT — same brain as Telegram (memory_blocks, ChromaDB, tools, agent loop)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="glow-div" style="margin-top:32px;"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">💬 Chat with JARVIS — same brain as Telegram</div>', unsafe_allow_html=True)
st.caption("שיחה כאן משתפת זיכרון עם הטלגרם — אותו ContextManager, אותם memory blocks, אותם כלים.")

if "jarvis_chat_history" not in st.session_state:
    st.session_state.jarvis_chat_history = []

for msg in st.session_state.jarvis_chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("דבר עם JARVIS..."):
    st.session_state.jarvis_chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("JARVIS חושב..."):
            brain = get_jarvis_brain()
            reply = _run_chat(brain, user_input)
        st.markdown(reply)
    st.session_state.jarvis_chat_history.append({"role": "assistant", "content": reply})

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:48px;text-align:center;font-family:var(--mono);
     font-size:.62rem;color:var(--text-mute);letter-spacing:2px;text-transform:uppercase;">
  JARVIS · NEURAL INTERFACE · FREE STACK · GROQ + SQLITE + GRAPHIFY
</div>
""", unsafe_allow_html=True)
