"""JARVIS Mission Control — Neural Interface Dashboard.

Run: streamlit run dashboard.py
"""
from __future__ import annotations

import asyncio
import json
import random
import sys
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import streamlit.components.v1 as components

from dashboard_utils import (
    DASHBOARD_CSS,
    cached_cross_project_summary,
    card_class,
    embed_project_graph,
    get_llm_recommendation,
    get_notifications,
    get_project_summary,
    get_random_skills,
    load_cv_status,
    load_gmail_summary,
    load_ledger,
    load_projects,
    load_skills_index,
    load_trending,
    read_context,
    render_tasks,
    staleness_class,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JARVIS · Mission Control",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design system — Neural Interface ─────────────────────────────────────────
st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)

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
] + ["💼 קריירה", "📈 מניות", "📧 מייל"]
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

# ══════════════════════════════════════════════════════════════════════════════
# TAB N+1 — CAREER (💼 קריירה)
# ══════════════════════════════════════════════════════════════════════════════
_STATUS_COLORS = {
    "applied":     ("var(--cyan)",   "🔵"),
    "interviewing":("var(--amber)",  "🟡"),
    "offered":     ("var(--mint)",   "🟢"),
    "rejected":    ("var(--coral)",  "🔴"),
}

with tabs[len(projects) + 1]:
    st.markdown('<div class="section-label">מועמדויות פתוחות</div>', unsafe_allow_html=True)
    cv_data = load_cv_status()
    if cv_data["status"] == "error":
        st.warning(f"⚠️ {cv_data['error']}")
    elif not cv_data["data"] or cv_data["data"].get("total", 0) == 0:
        st.markdown("""
<div class="card" style="text-align:center;padding:36px 20px;">
  <div style="font-size:2rem;opacity:.4;margin-bottom:8px;">💼</div>
  <div style="font-family:var(--mono);font-size:.72rem;color:var(--text-mute);">
    אין מועמדויות פתוחות — הוסף ב-PROJECT-CV
  </div>
</div>""", unsafe_allow_html=True)
    else:
        data = cv_data["data"]
        apps = data.get("open_applications", [])
        total = data.get("total", 0)

        # Summary stats
        status_counts = Counter(a.get("status", "?") for a in apps)
        stat_cols = st.columns(len(status_counts) or 1)
        for i, (s, count) in enumerate(sorted(status_counts.items())):
            color, emoji = _STATUS_COLORS.get(s, ("var(--text-dim)", "⚪"))
            with stat_cols[i % len(stat_cols)]:
                st.markdown(f"""
<div class="card" style="text-align:center;padding:14px;">
  <div style="font-size:1.5rem;">{emoji}</div>
  <div style="font-family:var(--mono);font-size:1.2rem;font-weight:700;color:{color};">{count}</div>
  <div style="font-family:var(--mono);font-size:.65rem;color:var(--text-mute);">{s.upper()}</div>
</div>""", unsafe_allow_html=True)

        # Filter
        filter_status = st.selectbox("סנן לפי סטטוס", ["הכל"] + sorted(status_counts.keys()), key="cv_filter")
        filtered = apps if filter_status == "הכל" else [a for a in apps if a.get("status") == filter_status]

        st.markdown(f'<div class="section-label" style="margin-top:16px;">{len(filtered)} מועמדויות</div>', unsafe_allow_html=True)
        for app in filtered[:20]:
            company = app.get("company", "?")
            role = app.get("role", "?")
            status = app.get("status", "?")
            date_applied = app.get("date_applied", "?")
            color, emoji = _STATUS_COLORS.get(status, ("var(--text-dim)", "⚪"))
            st.markdown(f"""
<div class="card" style="padding:12px 18px;margin-bottom:8px;border-left:3px solid {color};">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <span style="font-weight:600;">{company}</span>
      <span style="color:var(--text-dim);margin-left:8px;font-size:.85rem;">{role}</span>
    </div>
    <div style="font-family:var(--mono);font-size:.72rem;">
      <span style="color:{color};">{emoji} {status}</span>
      <span style="color:var(--text-mute);margin-left:8px;">{date_applied}</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB N+2 — TRADING SIGNALS (📈 מניות)
# ══════════════════════════════════════════════════════════════════════════════
with tabs[len(projects) + 2]:
    st.markdown('<div class="section-label">LedgerAlpha Signals</div>', unsafe_allow_html=True)
    ledger = load_ledger()
    if ledger["status"] == "error":
        st.warning(f"⚠️ LedgerAlpha לא זמין: {ledger['error']}")
    else:
        d = ledger["data"]
        regime = d.get("regime", "unknown")
        top = d.get("top_signal")
        timestamp = d.get("timestamp", "")

        col1, col2 = st.columns(2)
        all_signals = d.get("all_signals", [])
        signal_count = d.get("signal_count", 0)
        with col1:
            regime_color = {"bullish": "var(--mint)", "bearish": "var(--coral)"}.get(regime, "var(--amber)")
            st.markdown(f"""
<div class="card" style="padding:18px 22px;">
  <div class="card-label">REGIME</div>
  <div class="card-value" style="font-size:1.4rem;font-weight:700;color:{regime_color};">
    {regime.upper()}
  </div>
  <div style="font-family:var(--mono);font-size:.68rem;color:var(--text-mute);margin-top:6px;">
    {timestamp} · {signal_count} signals
  </div>
</div>""", unsafe_allow_html=True)
        with col2:
            if top:
                ticker = top.get("ticker", "?")
                score = top.get("score", "?")
                direction = top.get("direction", "?")
                dir_color = "var(--mint)" if direction == "long" else "var(--coral)"
                st.markdown(f"""
<div class="card" style="padding:18px 22px;">
  <div class="card-label">TOP SIGNAL</div>
  <div class="card-value" style="font-size:1.3rem;font-weight:700;">{ticker}</div>
  <div style="font-family:var(--mono);font-size:.78rem;color:{dir_color};margin-top:4px;">
    {direction.upper()} · score: {score}
  </div>
</div>""", unsafe_allow_html=True)

        if all_signals:
            st.markdown('<div class="section-label" style="margin-top:20px;">כל האיתותים</div>', unsafe_allow_html=True)
            for sig in all_signals:
                t = sig.get("ticker", "?")
                s = sig.get("score", "?")
                dr = sig.get("direction", "?")
                dr_color = "var(--mint)" if dr == "long" else "var(--coral)"
                score_pct = int(float(s) * 100) if isinstance(s, (int, float)) else 0
                st.markdown(f"""
<div class="notif-item notif-info" style="margin-bottom:5px;">
  <span style="font-family:var(--mono);font-weight:600;min-width:60px;">{t}</span>
  <span style="color:{dr_color};font-family:var(--mono);font-size:.78rem;margin-left:12px;">{dr.upper()}</span>
  <span style="margin-left:auto;font-family:var(--mono);font-size:.72rem;color:var(--text-dim);">score: {s}</span>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB N+3 — GMAIL (📧 מייל)
# ══════════════════════════════════════════════════════════════════════════════
with tabs[len(projects) + 3]:
    st.markdown('<div class="section-label">מיילים מסווגים</div>', unsafe_allow_html=True)
    gmail = load_gmail_summary()
    if gmail["status"] == "unconfigured":
        st.info("📧 Gmail לא מוגדר — הוסף GMAIL_EMAIL + GMAIL_APP_PASSWORD ל-.env")
    elif gmail["status"] == "error":
        st.warning(f"⚠️ {gmail['error']}")
    elif not gmail["data"]:
        st.info("אין מיילים חדשים.")
    else:
        data = gmail["data"]
        scanned = data.get("total_scanned", 0)
        categories = {
            "💼 עבודה": data.get("job", []),
            "💰 כסף": data.get("money", []),
            "⚡ פעולה נדרשת": data.get("action", []),
            "📨 ליד": data.get("lead", []),
        }
        total = sum(len(v) for v in categories.values())
        st.markdown(f"**{total} מיילים מעניינים** מתוך {scanned} שנסרקו")
        for cat_label, items in categories.items():
            if items:
                st.markdown(f"**{cat_label}** ({len(items)})")
                for item in items:
                    summary = item.get("summary", item.get("company", item.get("role", "?")))
                    st.markdown(f"""
<div class="notif-item notif-info" style="margin-bottom:5px;font-size:.84rem;">
  {summary}
</div>""", unsafe_allow_html=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:48px;text-align:center;font-family:var(--mono);
     font-size:.62rem;color:var(--text-mute);letter-spacing:2px;text-transform:uppercase;">
  JARVIS · NEURAL INTERFACE · FREE STACK · GROQ + SQLITE + GRAPHIFY
</div>
""", unsafe_allow_html=True)
