"""Unit tests for dashboard_utils.py pure helper functions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard_utils import build_chat_messages


def test_empty_history_returns_system_only():
    msgs = build_chat_messages("JARVIS", "some context", [])
    assert len(msgs) == 1
    assert msgs[0]["role"] == "system"
    assert "JARVIS" in msgs[0]["content"]
    assert "some context" in msgs[0]["content"]


def test_history_appended_after_system():
    history = [
        {"role": "user", "content": "שאלה"},
        {"role": "assistant", "content": "תשובה"},
    ]
    msgs = build_chat_messages("PROJ", "ctx", history)
    assert len(msgs) == 3
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"


def test_keeps_last_10_turns():
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
        for i in range(15)
    ]
    msgs = build_chat_messages("PROJ", "ctx", history)
    # 1 system + 10 history = 11
    assert len(msgs) == 11
    assert msgs[1]["content"] == "msg 5"
    assert msgs[-1]["content"] == "msg 14"


def test_context_truncated_at_3000_chars():
    long_ctx = "x" * 5000
    msgs = build_chat_messages("PROJ", long_ctx, [])
    assert "x" * 3000 in msgs[0]["content"]
    assert "x" * 3001 not in msgs[0]["content"]


def test_project_name_in_system_prompt():
    msgs = build_chat_messages("PROJECT-CASTRO", "ctx", [])
    assert "PROJECT-CASTRO" in msgs[0]["content"]
