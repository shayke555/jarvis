import os
import tempfile
import pytest
from brain.memory.sqlite_store import SQLiteStore


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = SQLiteStore(db_path=path)
    yield s
    # WAL mode keeps a handle open on Windows until GC'd — best-effort cleanup only.
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except OSError:
            pass


def test_upsert_block_creates_new_block(store):
    store.upsert_block("human", "name", "Shay Goba", {"source": "test"})
    block = store.get_block("human", "name")
    assert block is not None
    assert block["content"] == "Shay Goba"
    assert block["block_type"] == "human"
    assert block["key"] == "name"
    assert block["version"] == 1
    assert block["metadata"] == {"source": "test"}


def test_upsert_block_updates_existing_and_bumps_version(store):
    store.upsert_block("human", "name", "Shay Goba")
    store.upsert_block("human", "name", "Shay Goba — updated")

    block = store.get_block("human", "name")
    assert block["content"] == "Shay Goba — updated"
    assert block["version"] == 2


def test_get_block_returns_none_when_missing(store):
    assert store.get_block("human", "nonexistent") is None


def test_get_all_blocks_filters_by_type(store):
    store.upsert_block("human", "name", "Shay")
    store.upsert_block("human", "role", "Engineer")
    store.upsert_block("persona", "tone", "direct")

    human_blocks = store.get_all_blocks("human")
    assert {b["key"] for b in human_blocks} == {"name", "role"}

    persona_blocks = store.get_all_blocks("persona")
    assert {b["key"] for b in persona_blocks} == {"tone"}


def test_get_all_blocks_without_filter_returns_everything(store):
    store.upsert_block("human", "name", "Shay")
    store.upsert_block("persona", "tone", "direct")

    all_blocks = store.get_all_blocks()
    assert len(all_blocks) == 2
