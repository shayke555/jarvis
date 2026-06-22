"""Phase 1 — extracts durable facts about Shay from conversation turns and
upserts them into the `human_block` memory blocks, with a confidence gate
to avoid polluting memory with noise.

Kept deliberately small and isolated: a failure here must never break chat.
"""
import json
import logging

logger = logging.getLogger(__name__)

_CONFIDENCE_THRESHOLD = 0.8

_EXTRACTION_PROMPT = """You extract durable facts about Shay from a conversation turn.
A "durable fact" is something that stays true beyond this single conversation —
a new project, a preference, a decision, a skill, a goal. Do NOT extract small talk,
one-off questions, or facts already obviously known.

Conversation turn:
User: {user_message}
JARVIS: {assistant_response}

Respond with ONLY a JSON object, no prose, in this exact shape:
{{"has_fact": true|false, "key": "short_snake_case_key", "fact": "one durable sentence", "confidence": 0.0-1.0}}

If there is no durable fact worth remembering, respond: {{"has_fact": false}}
"""


async def maybe_update_human_block(context_manager, user_message: str, assistant_response: str) -> None:
    """Run a small LLM extraction over the latest turn; upsert into human_block
    only if confidence clears the threshold and the fact isn't a near-duplicate
    of an existing one under the same key."""
    prompt = _EXTRACTION_PROMPT.format(user_message=user_message, assistant_response=assistant_response)
    messages = [{"role": "user", "content": prompt}]

    raw = await context_manager.llm.chat(messages, context_tokens=len(prompt) // 4)

    extracted = _parse_extraction(raw)
    if extracted is None or not extracted.get("has_fact"):
        return

    try:
        confidence = float(extracted.get("confidence", 0))
    except (TypeError, ValueError):
        logger.debug("block_updater: non-numeric confidence in extraction: %r", extracted.get("confidence"))
        return

    if confidence < _CONFIDENCE_THRESHOLD:
        logger.debug("block_updater: discarding low-confidence fact (%.2f): %s", confidence, extracted.get("fact"))
        return

    key = extracted.get("key", "").strip()
    fact = extracted.get("fact", "").strip()
    if not key or not fact:
        return

    existing = context_manager.sqlite.get_block("human", key)
    if existing and existing["content"].strip() == fact:
        return  # exact duplicate — nothing to do

    context_manager.sqlite.upsert_block(
        "human", key, fact,
        {"source": "block_updater", "confidence": confidence},
    )
    logger.info("block_updater: upserted human_block[%s] (confidence=%.2f): %s", key, confidence, fact)


def _parse_extraction(raw: str) -> dict | None:
    """LLMs sometimes wrap JSON in prose or code fences — extract the object defensively."""
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug("block_updater: failed to parse extraction JSON: %s — raw: %s", e, raw[:200])
        return None
