"""dashboard_utils.py — Helpers for dashboard.py (data loaders + UI components)."""
from __future__ import annotations

import asyncio
import random
import threading
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


# ── Design system CSS ────────────────────────────────────────────────────────

DASHBOARD_CSS = """
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
"""

# ── Skills index ─────────────────────────────────────────────────────────────

_SKIP_SKILL_DIRS = {
    "_archived", "MORE_SKILLS_NEED_CHECK", "graphify-out",
    "ecc", "gstack", "skills_dependency_map.md",
}

_SLASH_MAP: dict[str, str] = {
    "graphify": "/graphify",
    "daily-standup": "/daily-standup",
    "session-start": "/session-start",
    "session-close": "/session-close",
    "debug-smart": "/debug-smart",
    "git-workflow": "/git-workflow",
    "db-architect": "/db-architect",
    "market-sentiment": "/market-sentiment",
    "meta-prompt": "/meta-prompt",
    "idea-validator": "/idea-validator",
    "venture-architect": "/venture-architect",
    "skill-builder": "/skill-builder",
    "python-analyst": "/python-analyst",
    "growth-loop": "/growth-loop",
    "cost-aware-llm-pipeline": "/cost-aware-llm-pipeline",
    "process-map": "/process-map",
    "proposal-write": "/proposal-write",
    "sop-write": "/sop-write",
    "data-scraper-agent": "/data-scraper-agent",
    "subagents-manager": "/subagents-manager",
    "agentic-engineering": "/agentic-engineering",
    "ln-200-scope-decomposer": "/ln-200-scope-decomposer",
    "ln-651-query-efficiency-auditor": "/ln-651-query-efficiency-auditor",
    "backend-patterns": "/backend-patterns",
    "python-testing": "/python-testing",
    "api-connector-builder": "/api-connector-builder",
    "api-integrator": "/api-integrator",
    "async-debug": "/async-debug",
    "database-migrations": "/database-migrations",
    "continuous-agent-loop": "/continuous-agent-loop",
    "langgraph-helper": "/langgraph-helper",
    "agent-harness-construction": "/agent-harness-construction",
    "error-handler": "/error-handler",
    "env-setup": "/env-setup",
    "caveman": "/caveman",
    "project-context": "/project-context",
}


def _extract_skill_desc(skill_dir: Path) -> str:
    for fname in ("SKILL.md", "README.md"):
        f = skill_dir / fname
        if not f.exists():
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            for line in content.split("\n")[:15]:
                line = line.strip()
                if line.lower().startswith("description:"):
                    val = line.split(":", 1)[1].strip().strip('"')
                    if val and len(val) > 5:
                        return val[:140]
            for line in content.split("\n")[1:20]:
                line = line.strip()
                if (line and not line.startswith("#") and not line.startswith("---")
                        and not line.startswith("name:") and not line.startswith("```")
                        and len(line) > 10):
                    return line[:140]
        except Exception:
            pass
    return ""


def load_skills_index() -> list[dict]:
    """Read all installed top-level skills from ~/.claude/skills/."""
    skills_dir = Path.home() / ".claude" / "skills"
    if not skills_dir.exists():
        return []
    skills = []
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or d.name in _SKIP_SKILL_DIRS or d.name.startswith("."):
            continue
        desc = _extract_skill_desc(d)
        skill_md = d / "SKILL.md"
        skills.append({
            "name": d.name,
            "description": desc or "—",
            "slash": _SLASH_MAP.get(d.name, ""),
            "skill_md": str(skill_md) if skill_md.exists() else None,
        })
    return skills


def get_random_skills(all_skills: list[dict], n: int = 4, seed: int | None = None) -> list[dict]:
    """Return n random skills. Uses seed for consistent shuffle per session."""
    rng = random.Random(seed)
    return rng.sample(all_skills, min(n, len(all_skills)))


# ── Cross-project summary ─────────────────────────────────────────────────────

def get_cross_project_summary(contexts: dict[str, str]) -> str:
    """Groq summary of all project contexts — 'what did I do, where do things stand'."""
    if not contexts:
        return ""
    combined = "\n\n".join(
        f"=== {name} ===\n{ctx[:800]}" for name, ctx in contexts.items() if ctx
    )
    if not combined.strip():
        return ""
    try:
        from config.settings import settings  # type: ignore[import]
        if not settings.groq_api_key:
            return ""
        from groq import Groq  # type: ignore[import]
        client = Groq(api_key=settings.groq_api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "אתה JARVIS. קרא את ה-context.md של כל הפרויקטים.\n"
                        "לכל פרויקט שורה אחת: EMOJI **שם** — הושלם: X · הבא: Y\n"
                        "קצר, ישיר, עברית. מקסימום 6 שורות."
                    ),
                },
                {"role": "user", "content": combined[:4000]},
            ],
            max_tokens=280,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ {type(e).__name__}"


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


# ── Context + staleness helpers ───────────────────────────────────────────────

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


# ── UI components (Streamlit) ─────────────────────────────────────────────────

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
