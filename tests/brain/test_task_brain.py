import sqlite3
import pytest
import brain.task_brain as tb


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db = str(tmp_path / "test.db")
    monkeypatch.setattr(tb, "_DB_PATH", db)
    with sqlite3.connect(db) as conn:
        conn.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                project TEXT,
                description TEXT,
                status TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    tb.init_task_brain()


def test_migration_adds_columns():
    with sqlite3.connect(tb._DB_PATH) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    assert "area" in cols
    assert "due_date" in cols
    assert "source" in cols


def test_add_and_get_task():
    tb.add_task("studies", "מבחן סטטיסטיקה", due_date="2026-05-08")
    result = tb.get_tasks()
    assert result["status"] == "ok"
    assert result["data"]["count"] == 1
    assert result["data"]["tasks"][0]["description"] == "מבחן סטטיסטיקה"
    assert result["data"]["tasks"][0]["area"] == "studies"


def test_get_tasks_by_area():
    tb.add_task("studies", "מבחן")
    tb.add_task("work", "CV")
    result = tb.get_tasks(area="studies")
    assert result["data"]["count"] == 1
    assert result["data"]["tasks"][0]["area"] == "studies"


def test_mark_done_removes_from_open():
    tb.add_task("work", "שלח CV")
    tasks = tb.get_tasks()
    task_id = tasks["data"]["tasks"][0]["id"]
    result = tb.mark_done(task_id)
    assert result["status"] == "ok"
    assert tb.get_tasks()["data"]["count"] == 0


def test_unknown_area_accepted_with_warning(caplog):
    # Area validation is soft — unknown areas are accepted (project names etc.)
    import logging
    with caplog.at_level(logging.WARNING, logger="brain.task_brain"):
        result = tb.add_task("nonexistent_area", "something")
    assert result["status"] == "ok"
    assert "unknown area" in caplog.text


def test_format_empty():
    msg = tb.format_tasks_message()
    assert "אין" in msg


def test_format_with_tasks():
    tb.add_task("growth", "קרא ספר")
    tb.add_task("wellness", "ספורט")
    msg = tb.format_tasks_message()
    assert "TASKS [2 open]" in msg
    assert "growth" in msg
    assert "wellness" in msg


def test_worker_return_shape():
    result = tb.get_tasks()
    assert "status" in result
    assert "data" in result
    assert "error" in result
