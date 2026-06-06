import json
import logging
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)


def fetch_ledger_signals() -> dict:
    """Read regime + signals from PROJECT-SANTIMENT. Zero cost — local files only."""
    try:
        base = Path(settings.ledgeralpha_signals_path)
        regime_path = base / "regime.json"
        signals_path = base / "latest_signals.json"

        if not regime_path.exists():
            raise FileNotFoundError(f"{regime_path}")
        if not signals_path.exists():
            raise FileNotFoundError(f"{signals_path}")

        regime_data = json.loads(regime_path.read_text(encoding="utf-8"))
        signals_data = json.loads(signals_path.read_text(encoding="utf-8"))

        top_signal = (
            signals_data[0]
            if isinstance(signals_data, list) and signals_data
            else None
        )

        return {
            "status": "ok",
            "data": {
                "regime": regime_data.get("regime", "unknown"),
                "top_signal": top_signal,
                "timestamp": regime_data.get("timestamp", ""),
            },
            "error": None,
        }
    except FileNotFoundError as e:
        logger.warning("LedgerAlpha signals not found: %s", e)
        return {"status": "error", "data": None, "error": f"signals file not found: {e}"}
    except Exception as e:
        logger.error("ledger_bridge error: %s", e)
        return {"status": "error", "data": None, "error": str(e)}
