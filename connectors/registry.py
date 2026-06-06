from __future__ import annotations

import logging
from typing import Callable

from connectors.ledger_bridge import fetch_ledger_signals
from connectors.gmail_bridge import fetch_gmail_summary

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, Callable | None] = {
    "ledger": fetch_ledger_signals,
    "gmail": fetch_gmail_summary,
    "tasks": None,        # registered at bot startup after TaskBrain init
    "calendar": None,     # Future
    "drive": None,        # Future
    "web_monitor": None,  # Future
    "web_research": None, # Future
    "whatsapp": None,     # Future (n8n bridge)
}


def register(name: str, fn: Callable) -> None:
    _REGISTRY[name] = fn


def execute(name: str, **kwargs) -> dict:
    fn = _REGISTRY.get(name)
    if fn is None:
        return {"status": "error", "data": None, "error": f"connector '{name}' not available"}
    try:
        return fn(**kwargs)
    except Exception as e:
        logger.error("connector '%s' raised: %s", name, e)
        return {"status": "error", "data": None, "error": str(e)}


def available() -> list[str]:
    return [k for k, v in _REGISTRY.items() if v is not None]
