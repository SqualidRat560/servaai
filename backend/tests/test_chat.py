"""Chatbot + lifestyle advice: numbers only from the engine."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend import advice, agent, engine
from backend.app import app

client = TestClient(app)


def test_twist_cards_still_return_a_chip_to_confirm_via_parse_event():
    d = client.post("/api/parse-event", json={"text": "I lost my job and rent went up $200"}).json()
    assert d["shock"]["ei_pct"] == 0.55 and d["shock"]["rent_up"] == 200 and d["chip"]


def test_template_advice_is_grounded_and_practical():
    f = advice.facts(63816, engine.TWISTS["layoff_ei55_bills15"])
    out = advice.outcome_advice(f, use_gemini=False)
    assert out["source"] == "template" and 3 <= len(out["suggestions"]) <= 5
    assert agent.numbers_are_grounded(out["summary"] + " " + " ".join(out["suggestions"]), f)[0]
    assert any("Employment Insurance" in s for s in out["suggestions"])


def test_general_answer_template_is_grounded():
    out = advice.answer(63816, "how can I save more?", use_gemini=False)
    f = advice.facts(63816, engine.Shock())
    assert out["suggestions"] and agent.numbers_are_grounded(" ".join(out["suggestions"]), f)[0]


def test_advice_endpoint_keeps_engine_numbers():
    d = client.post("/api/advice", json={"account_id": 63816, "ei_pct": 0.55, "bills_up_pct": 0.15}).json()
    assert d["facts"]["judge_runway_months"] == 3.1 and d["facts"]["realistic_runway_months"] == 1.9
    assert d["suggestions"]


def test_speak_without_key_is_404(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setattr(agent, "_env", lambda: (None, "x"))
    assert client.post("/api/speak", json={"text": "hello"}).status_code == 404
