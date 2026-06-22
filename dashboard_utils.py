"""dashboard_utils.py — Pure helpers for dashboard.py (no Streamlit deps)."""
from __future__ import annotations

import random
from pathlib import Path


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
