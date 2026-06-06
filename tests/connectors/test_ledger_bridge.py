import json
import pytest
from connectors.ledger_bridge import fetch_ledger_signals


@pytest.fixture
def signals_dir(tmp_path, monkeypatch):
    regime = {"regime": "bull", "timestamp": "2026-05-06T07:30:00"}
    signals = [{"ticker": "AAPL", "score": 0.87, "direction": "long"}]
    (tmp_path / "regime.json").write_text(json.dumps(regime), encoding="utf-8")
    (tmp_path / "latest_signals.json").write_text(json.dumps(signals), encoding="utf-8")
    monkeypatch.setattr(
        "connectors.ledger_bridge.settings.ledgeralpha_signals_path", str(tmp_path)
    )
    return tmp_path


def test_fetch_ok(signals_dir):
    result = fetch_ledger_signals()
    assert result["status"] == "ok"
    assert result["data"]["regime"] == "bull"
    assert result["data"]["top_signal"]["ticker"] == "AAPL"
    assert result["error"] is None


def test_fetch_missing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "connectors.ledger_bridge.settings.ledgeralpha_signals_path", str(tmp_path)
    )
    result = fetch_ledger_signals()
    assert result["status"] == "error"
    assert result["data"] is None
    assert "not found" in result["error"]


def test_fetch_empty_signals(tmp_path, monkeypatch):
    (tmp_path / "regime.json").write_text(
        json.dumps({"regime": "bear", "timestamp": "2026-05-06"}), encoding="utf-8"
    )
    (tmp_path / "latest_signals.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(
        "connectors.ledger_bridge.settings.ledgeralpha_signals_path", str(tmp_path)
    )
    result = fetch_ledger_signals()
    assert result["status"] == "ok"
    assert result["data"]["top_signal"] is None
