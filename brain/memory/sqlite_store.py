import sqlite3
from pathlib import Path
from datetime import datetime
import json


class SQLiteStore:
    def __init__(self, db_path: str = "./jarvis.db") -> None:
        self.db_path = db_path
        self.init_db()

    def init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY,
                    interface TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    tags TEXT,
                    project TEXT,
                    file_path TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS regime_events (
                    id INTEGER PRIMARY KEY,
                    headline TEXT,
                    source TEXT,
                    sentiment_score REAL,
                    keywords_matched TEXT,
                    alerted BOOLEAN,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    project TEXT,
                    description TEXT,
                    status TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_blocks (
                    id INTEGER PRIMARY KEY,
                    block_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    UNIQUE(block_type, key)
                )
            """)

            conn.commit()

    def add_message(self, interface: str, role: str, content: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (interface, role, content) VALUES (?, ?, ?)",
                (interface, role, content)
            )
            conn.commit()

    def get_recent_messages(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def set_preference(self, key: str, value: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, datetime.now().isoformat())
            )
            conn.commit()

    def get_preference(self, key: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT value FROM preferences WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row['value'] if row else None

    def get_all_preferences(self) -> dict[str, str]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT key, value FROM preferences")
            return {row['key']: row['value'] for row in cursor.fetchall()}

    def add_lesson(self, title: str, content: str, tags: list[str], project: str, file_path: str) -> int:
        tags_json = json.dumps(tags)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO lessons (title, content, tags, project, file_path) VALUES (?, ?, ?, ?, ?)",
                (title, content, tags_json, project, file_path)
            )
            conn.commit()
            return cursor.lastrowid

    def add_regime_event(self, headline: str, source: str, sentiment_score: float, keywords_matched: str, alerted: bool) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO regime_events (headline, source, sentiment_score, keywords_matched, alerted) VALUES (?, ?, ?, ?, ?)",
                (headline, source, sentiment_score, keywords_matched, alerted)
            )
            conn.commit()

    def get_recent_regime_events(self, limit: int = 10) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM regime_events ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_task(self, project: str, description: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (project, description, status) VALUES (?, ?, ?)",
                (project, description, 'open')
            )
            conn.commit()
            return cursor.lastrowid

    def update_task_status(self, task_id: int, status: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (status, task_id)
            )
            conn.commit()

    def get_open_tasks(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE status = 'open' ORDER BY created_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def upsert_block(self, block_type: str, key: str, content: str, metadata: dict | None = None) -> None:
        """Create or update a memory block. Bumps version atomically on conflict (avoids
        a read-then-write race between concurrent upserts to the same block)."""
        metadata_json = json.dumps(metadata or {})
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO memory_blocks (block_type, key, content, metadata, updated_at, version)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(block_type, key) DO UPDATE SET
                    content = excluded.content,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at,
                    version = memory_blocks.version + 1
                """,
                (block_type, key, content, metadata_json, datetime.now().isoformat())
            )
            conn.commit()

    def get_block(self, block_type: str, key: str) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM memory_blocks WHERE block_type = ? AND key = ?",
                (block_type, key)
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result['metadata'] = json.loads(result['metadata'] or '{}')
            return result

    def get_all_blocks(self, block_type: str | None = None) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if block_type is None:
                cursor = conn.execute("SELECT * FROM memory_blocks ORDER BY block_type, key")
            else:
                cursor = conn.execute(
                    "SELECT * FROM memory_blocks WHERE block_type = ? ORDER BY key",
                    (block_type,)
                )
            results = []
            for row in cursor.fetchall():
                item = dict(row)
                item['metadata'] = json.loads(item['metadata'] or '{}')
                results.append(item)
            return results
