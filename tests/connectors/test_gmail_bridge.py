"""Tests for connectors/gmail_bridge.py."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from connectors.gmail_bridge import format_gmail_section, _classify_batch, fetch_gmail_summary


# ---------------------------------------------------------------------------
# format_gmail_section — pure formatting, no external deps
# ---------------------------------------------------------------------------

def _make_data(job=None, money=None, action=None, lead=None, total=5, noise=3):
    return {
        "job": job or [],
        "money": money or [],
        "action": action or [],
        "lead": lead or [],
        "total_scanned": total,
        "noise_skipped": noise,
    }


def test_format_no_interesting_emails():
    result = format_gmail_section(_make_data())
    assert "📧" in result
    assert "0" in result


def test_format_job_email_shows_company_and_status():
    data = _make_data(job=[{"company": "NICE", "status": "ראיון"}])
    result = format_gmail_section(data)
    assert "💼" in result
    assert "NICE" in result
    assert "ראיון" in result


def test_format_money_email_shows_summary():
    data = _make_data(money=[{"summary": "חיוב ₪450"}])
    result = format_gmail_section(data)
    assert "💰" in result
    assert "₪450" in result


def test_format_action_email_shows_summary():
    data = _make_data(action=[{"summary": "דחוף (שכירה)"}])
    result = format_gmail_section(data)
    assert "⚡" in result
    assert "דחוף" in result


def test_format_multiple_categories():
    data = _make_data(
        job=[{"company": "Google", "status": "סינון"}],
        money=[{"summary": "חיוב ₪200"}],
        action=[{"summary": "צריך אישור"}],
    )
    result = format_gmail_section(data)
    assert "💼" in result
    assert "💰" in result
    assert "⚡" in result
    assert "Google" in result


def test_format_lead_email_shows_role_and_company():
    data = _make_data(
        job=[],
        money=[],
        action=[],
        lead=[{"company": "Fiverr", "role": "Data Analyst"}],
        total=10,
        noise=8,
    )
    result = format_gmail_section(data)
    assert "📨" in result
    assert "Fiverr" in result
    assert "Data Analyst" in result


# ---------------------------------------------------------------------------
# fetch_gmail_summary — credentials check (no real IMAP)
# ---------------------------------------------------------------------------

def test_fetch_gmail_no_credentials(monkeypatch):
    monkeypatch.setattr("connectors.gmail_bridge.settings.gmail_app_password", "")
    result = fetch_gmail_summary()
    assert result["status"] == "error"
    assert result["data"] is None
    assert "credentials" in result["error"].lower() or "password" in result["error"].lower()


def test_fetch_gmail_imap_error(monkeypatch):
    monkeypatch.setattr("connectors.gmail_bridge.settings.gmail_app_password", "test-pass")
    monkeypatch.setattr("connectors.gmail_bridge.settings.gmail_email", "test@gmail.com")
    with patch("connectors.gmail_bridge.imaplib.IMAP4_SSL") as mock_imap:
        mock_imap.side_effect = ConnectionError("IMAP unreachable")
        result = fetch_gmail_summary()
    assert result["status"] == "error"
    assert result["data"] is None


# ---------------------------------------------------------------------------
# _classify_batch — LLM classification logic (mock Groq)
# ---------------------------------------------------------------------------

def _make_mock_groq(response_json: list) -> MagicMock:
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(response_json)
    mock_client.chat.completions.create.return_value = mock_resp
    return mock_client


def test_classify_batch_job_email():
    groq = _make_mock_groq([
        {"id": 0, "category": "job", "company": "NICE", "status": "ראיון",
         "summary": "ראיון", "amount": None}
    ])
    emails = [{"id": 0, "sender": "hr@nice.com", "subject": "Interview Invite", "body": "Schedule..."}]
    result = _classify_batch(groq, emails)
    assert len(result) == 1
    assert result[0]["category"] == "job"
    assert result[0]["company"] == "NICE"


def test_classify_batch_money_email():
    groq = _make_mock_groq([
        {"id": 0, "category": "money", "company": None, "status": None,
         "summary": "חיוב ₪450", "amount": "450"}
    ])
    emails = [{"id": 0, "sender": "bank@hapoalim.co.il", "subject": "Bank statement", "body": "450 NIS"}]
    result = _classify_batch(groq, emails)
    assert result[0]["category"] == "money"
    assert "₪" in result[0]["summary"] or "money" in result[0]["category"]


def test_classify_batch_linkedin_relevant_lead():
    groq = _make_mock_groq([
        {"id": 0, "category": "lead", "company": "Fiverr", "role": "Data Analyst",
         "status": None, "summary": "Data Analyst @ Fiverr", "amount": None}
    ])
    emails = [{"id": 0, "sender": "jobs-noreply@linkedin.com",
               "subject": "Data Analyst at Fiverr matches your profile", "body": "..."}]
    result = _classify_batch(groq, emails)
    assert result[0]["category"] == "lead"
    assert result[0]["company"] == "Fiverr"


def test_classify_batch_linkedin_irrelevant_lead():
    groq = _make_mock_groq([
        {"id": 0, "category": "noise", "company": None, "role": None,
         "status": None, "summary": None, "amount": None}
    ])
    emails = [{"id": 0, "sender": "jobs-noreply@linkedin.com",
               "subject": "Warehouse Manager at XYZ", "body": "..."}]
    result = _classify_batch(groq, emails)
    assert result[0]["category"] == "noise"


def test_classify_batch_noise_email():
    groq = _make_mock_groq([
        {"id": 0, "category": "noise", "company": None, "status": None,
         "summary": None, "amount": None}
    ])
    emails = [{"id": 0, "sender": "noreply@amazon.com", "subject": "Your order shipped", "body": "..."}]
    result = _classify_batch(groq, emails)
    assert result[0]["category"] == "noise"


def test_classify_batch_handles_llm_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("Groq timeout")
    emails = [{"id": 0, "sender": "a@b.com", "subject": "test", "body": "..."}]
    result = _classify_batch(mock_client, emails)
    assert result == []
