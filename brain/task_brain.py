import logging
import sqlite3
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

_DB_PATH = "./jarvis.db"

VALID_AREAS = frozenset(
    ["studies", "work", "personal", "projects", "growth", "wellness", "claude_code"]
)
PRIORITY_LEVELS = frozenset(["high", "medium", "low"])


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_task_brain() -> None:
    """Migrate tasks table and create streak table."""
    with _connect() as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        if "area" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN area TEXT DEFAULT 'personal'")
        if "due_date" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN due_date DATE")
        if "source" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN source TEXT DEFAULT 'manual'")
        if "updated_at" not in cols:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            )
        if "priority" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'medium'")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_streak (
                id      INTEGER PRIMARY KEY CHECK (id = 1),
                last_date TEXT,
                streak  INTEGER DEFAULT 0,
                total   INTEGER DEFAULT 0
            )
        """)
    logger.info("TaskBrain initialized — schema migrated, WAL mode active")


def add_task(
    area: str,
    description: str,
    due_date: str | None = None,
    source: str = "manual",
    priority: str = "medium",
) -> dict:
    if area in VALID_AREAS or area.startswith("PROJECT-") or area.isupper():
        pass  # valid: known area or project name
    else:
        logger.warning("add_task: unknown area '%s'", area)
    if priority not in PRIORITY_LEVELS:
        priority = "medium"
    try:
        with _connect() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (area, description, status, due_date, source, priority) "
                "VALUES (?, ?, 'open', ?, ?, ?)",
                (area, description, due_date, source, priority),
            )
            return {"status": "ok", "data": {"id": cursor.lastrowid}, "error": None}
    except Exception as e:
        logger.error("add_task error: %s", e)
        return {"status": "error", "data": None, "error": str(e)}


def get_tasks(area: str | None = None) -> dict:
    try:
        with _connect() as conn:
            if area:
                rows = conn.execute(
                    "SELECT id, area, description, due_date, priority FROM tasks "
                    "WHERE status='open' AND area=? ORDER BY "
                    "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, due_date ASC",
                    (area,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, area, description, due_date, priority FROM tasks "
                    "WHERE status='open' ORDER BY "
                    "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, area, due_date ASC"
                ).fetchall()
            tasks = [dict(r) for r in rows]
            return {"status": "ok", "data": {"tasks": tasks, "count": len(tasks)}, "error": None}
    except Exception as e:
        logger.error("get_tasks error: %s", e)
        return {"status": "error", "data": None, "error": str(e)}


def mark_done(task_id: int) -> dict:
    try:
        with _connect() as conn:
            conn.execute(
                "UPDATE tasks SET status='done', updated_at=? WHERE id=?",
                (datetime.now().isoformat(), task_id),
            )
            return {"status": "ok", "data": {"id": task_id}, "error": None}
    except Exception as e:
        logger.error("mark_done error: %s", e)
        return {"status": "error", "data": None, "error": str(e)}


def get_dashboard_streak() -> dict:
    """Track daily dashboard opens. Returns streak, total, and whether it's a new day."""
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT last_date, streak, total FROM dashboard_streak WHERE id = 1"
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO dashboard_streak VALUES (1, ?, 1, 1)", (today,)
                )
                return {"streak": 1, "total": 1, "new_day": True}
            last_date, streak, total = row["last_date"], row["streak"], row["total"]
            if last_date == today:
                conn.execute(
                    "UPDATE dashboard_streak SET total = total + 1 WHERE id = 1"
                )
                return {"streak": streak, "total": total + 1, "new_day": False}
            new_streak = streak + 1 if last_date == yesterday else 1
            conn.execute(
                "UPDATE dashboard_streak SET last_date=?, streak=?, total=total+1 WHERE id=1",
                (today, new_streak),
            )
            return {"streak": new_streak, "total": total + 1, "new_day": True}
    except Exception as e:
        logger.error("get_dashboard_streak error: %s", e)
        return {"streak": 0, "total": 0, "new_day": False}


def format_tasks_message() -> str:
    result = get_tasks()
    if result["status"] == "error":
        return "📋 TASKS: unavailable"
    tasks = result["data"]["tasks"]
    if not tasks:
        return "📋 TASKS: אין משימות פתוחות"
    by_area: dict[str, list] = {}
    for t in tasks:
        by_area.setdefault(t["area"], []).append(t)
    lines = [f"📋 TASKS [{result['data']['count']} open]"]
    for area in sorted(by_area):
        for t in by_area[area]:
            due = f" — {t['due_date']}" if t.get("due_date") else ""
            lines.append(f"  • {area}: {t['description']}{due}")
    return "\n".join(lines)
