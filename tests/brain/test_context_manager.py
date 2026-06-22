from unittest.mock import MagicMock
from brain.context_manager import ContextManager


def _make_cm(human_blocks=None, persona_blocks=None, project_blocks=None) -> ContextManager:
    """Build a ContextManager with mocked stores — mirrors _make_loop in test_agent_loop.py."""
    cm = ContextManager.__new__(ContextManager)
    cm.sqlite = MagicMock()
    cm.chroma = MagicMock()
    cm.llm = MagicMock()

    def get_all_blocks(block_type=None):
        return {
            "human": human_blocks or [],
            "persona": persona_blocks or [],
            "project": project_blocks or [],
        }.get(block_type, [])

    cm.sqlite.get_all_blocks = MagicMock(side_effect=get_all_blocks)
    return cm


def _block(block_type, key, content):
    return {"id": 1, "block_type": block_type, "key": key, "content": content,
            "metadata": {}, "version": 1, "updated_at": "2026-06-08"}


def test_build_system_prompt_includes_human_and_persona_blocks():
    cm = _make_cm(
        human_blocks=[_block("human", "identity", "Shay Goba, IE student")],
        persona_blocks=[_block("persona", "communication_style", "direct, no fluff")],
    )
    prompt = cm._build_system_prompt(relevant_memories=[])

    assert "Shay Goba, IE student" in prompt
    assert "direct, no fluff" in prompt
    assert "Who Shay Is" in prompt
    assert "How JARVIS Should Behave" in prompt


def test_build_system_prompt_includes_project_blocks():
    cm = _make_cm(project_blocks=[_block("project", "ledgeralpha", "AI hedge fund analyst")])
    prompt = cm._build_system_prompt(relevant_memories=[])

    assert "AI hedge fund analyst" in prompt
    assert "Active Projects" in prompt


def test_build_system_prompt_includes_episodic_memories():
    cm = _make_cm()
    prompt = cm._build_system_prompt(relevant_memories=[{"text": "Shay prefers Python over JS"}])

    assert "Shay prefers Python over JS" in prompt
    assert "Relevant Memories" in prompt


def test_build_system_prompt_omits_empty_sections():
    cm = _make_cm()
    prompt = cm._build_system_prompt(relevant_memories=[])

    assert "Active Projects" not in prompt
    assert "Who Shay Is" not in prompt
    assert "Relevant Memories" not in prompt


def test_seed_skips_when_human_blocks_already_exist():
    cm = _make_cm(human_blocks=[_block("human", "identity", "already seeded")])
    cm.sqlite.upsert_block = MagicMock()

    cm._seed_memory_blocks_if_empty()

    cm.sqlite.upsert_block.assert_not_called()


def test_seed_populates_blocks_from_yaml_when_empty(monkeypatch):
    cm = _make_cm(human_blocks=[])
    cm.sqlite.upsert_block = MagicMock()
    monkeypatch.setattr(cm, "_load_shay_context", lambda: (
        "identity:\n  name: Shay Goba\n"
        "personality:\n  style: direct\n"
        "communication_with_jarvis:\n  tone: direct partner\n"
    ))

    cm._seed_memory_blocks_if_empty()

    seeded_keys = [call.args[1] for call in cm.sqlite.upsert_block.call_args_list]
    assert "identity" in seeded_keys
    assert "personality" in seeded_keys
    assert "communication_style" in seeded_keys


def test_seed_does_nothing_when_yaml_missing(monkeypatch):
    cm = _make_cm(human_blocks=[])
    cm.sqlite.upsert_block = MagicMock()
    monkeypatch.setattr(cm, "_load_shay_context", lambda: "")

    cm._seed_memory_blocks_if_empty()

    cm.sqlite.upsert_block.assert_not_called()
