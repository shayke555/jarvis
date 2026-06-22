import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from brain.memory.block_updater import maybe_update_human_block, _parse_extraction


def _make_cm(llm_response: str, existing_block=None):
    cm = MagicMock()
    cm.llm.chat = AsyncMock(return_value=llm_response)
    cm.sqlite.get_block = MagicMock(return_value=existing_block)
    cm.sqlite.upsert_block = MagicMock()
    return cm


@pytest.mark.asyncio
async def test_upserts_fact_when_confidence_above_threshold():
    cm = _make_cm(json.dumps({
        "has_fact": True, "key": "new_project", "fact": "Shay started PROJECT-X", "confidence": 0.9
    }))

    await maybe_update_human_block(cm, "I started a new project", "Nice, tell me more")

    cm.sqlite.upsert_block.assert_called_once()
    args = cm.sqlite.upsert_block.call_args.args
    assert args[0] == "human"
    assert args[1] == "new_project"
    assert args[2] == "Shay started PROJECT-X"


@pytest.mark.asyncio
async def test_discards_fact_below_confidence_threshold():
    cm = _make_cm(json.dumps({
        "has_fact": True, "key": "maybe_fact", "fact": "Shay might like X", "confidence": 0.4
    }))

    await maybe_update_human_block(cm, "I think I like X", "Cool")

    cm.sqlite.upsert_block.assert_not_called()


@pytest.mark.asyncio
async def test_skips_when_no_fact_extracted():
    cm = _make_cm(json.dumps({"has_fact": False}))

    await maybe_update_human_block(cm, "מה השעה?", "12:00")

    cm.sqlite.upsert_block.assert_not_called()


@pytest.mark.asyncio
async def test_skips_exact_duplicate_fact():
    cm = _make_cm(
        json.dumps({"has_fact": True, "key": "role", "fact": "Shay is an IE student", "confidence": 0.95}),
        existing_block={"content": "Shay is an IE student"},
    )

    await maybe_update_human_block(cm, "I'm an IE student", "Got it")

    cm.sqlite.upsert_block.assert_not_called()


@pytest.mark.asyncio
async def test_handles_malformed_llm_response_gracefully():
    cm = _make_cm("this is not json at all")

    await maybe_update_human_block(cm, "hello", "hi")

    cm.sqlite.upsert_block.assert_not_called()


def test_parse_extraction_handles_prose_wrapped_json():
    raw = 'Sure! Here is the result: {"has_fact": true, "key": "x", "fact": "y", "confidence": 0.9} hope that helps'
    parsed = _parse_extraction(raw)
    assert parsed == {"has_fact": True, "key": "x", "fact": "y", "confidence": 0.9}


def test_parse_extraction_returns_none_for_garbage():
    assert _parse_extraction("no json here") is None
