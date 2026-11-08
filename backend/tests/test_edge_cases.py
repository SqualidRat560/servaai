"""Edge cases a judge could hit live: zero/negative/huge inputs, empty or hostile text, no-EI paths."""
from __future__ import annotations

import math

import pytest

from backend import agent, engine, realistic


# ------------------------------------------------ judge_runway boundaries (pure arithmetic)

def test_judge_runway_zero_buffer_gives_zero_months():
    r = engine.judge_runway(B=0.0, one_off=0.0, S_new=1000.0, I_new=500.0)
    assert r.value == 0.0 and r.status == "zero"


def test_judge_runway_negative_buffer_after_one_off_gives_zero_months():
    r = engine.judge_runway(B=500.0, one_off=10_000.0, S_new=1000.0, I_new=2000.0)
    assert r.value == 0.0 and r.status == "zero"


def test_judge_runway_income_equals_spending_is_no_shortfall():
    r = engine.judge_runway(B=1000.0, one_off=0.0, S_new=1500.0, I_new=1500.0)
    assert r.value is None and r.status == "no_shortfall"


def test_judge_runway_zero_income_is_finite_not_a_crash():
    r = engine.judge_runway(B=3000.0, one_off=0.0, S_new=1000.0, I_new=0.0)
    assert r.value == 3.0 and r.status == "finite"


def test_judge_runway_tiny_gap_hits_the_120_month_cap():
    r = engine.judge_runway(B=1_000_000.0, one_off=0.0, S_new=1000.01, I_new=1000.0)
    assert r.value == engine.RUNWAY_CAP and r.status == "capped"


@pytest.mark.parametrize("raw, expected", [(2.25, 2.3), (2.35, 2.4), (0.05, 0.1)])
def test_round_half_up_rounds_ties_up(raw, expected):
    assert engine.round_half_up(raw) == expected


# ------------------------------------------------ Shock validation (bad input never reaches the maths)

@pytest.mark.parametrize("bad", [{"one_off": -1}, {"rent_up": -50}, {"bills_up_pct": -0.1},
                                 {"ei_pct": 1.5}, {"ei_pct": -0.2}, {"one_off": math.nan},
                                 {"one_off": math.inf}, {"one_off": True}, {"repair_months": "2"}])
def test_shock_rejects_bad_values(bad):
    with pytest.raises(ValueError):
        engine.Shock(**bad)


def test_shock_ei_zero_percent_is_allowed_and_zeroes_income():
    p = engine.profile(63816)
    s = engine.apply_shock(p, engine.Shock(ei_pct=0.0))
    assert s.I_new == 0.0


def test_unknown_account_raises_clean_error():
    with pytest.raises(engine.UnknownAccount):
        engine.profile(-1)


def test_huge_one_off_gives_zero_runway_on_a_real_account():
    out = engine.run(63816, engine.Shock(one_off=10_000_000))
    assert out["judge_runway"]["value"] == 0.0


# ------------------------------------------------ realistic runway without EI

def test_realistic_zero_percent_ei_never_beats_judge_runway():
    p = engine.profile(63816)
    shock = engine.Shock(ei_pct=0.0)
    s = engine.apply_shock(p, shock)
    j = engine.judge_runway(p.B, s.one_off, s.S_new, s.I_new)
    r = realistic.realistic_runway(p, shock)
    if j.value is not None and r.value is not None:
        assert r.value <= j.value + 1e-9


def test_realistic_reemployment_in_month_one_restores_full_income():
    p = engine.profile(63816)
    shock = engine.Shock(ei_pct=0.55)
    assert realistic.income_in_month(p, shock, month=1, ei_months=6, cap=True, reemploy_month=1) == p.I


# ------------------------------------------------ event agent with hostile / empty text (offline)

@pytest.mark.parametrize("text", ["", "   ", None, "a" * 5000, "!!!???", "$$$$", "lost my job " * 200])
def test_parse_event_never_crashes_offline(text):
    out = agent.parse_event(text, use_gemini=False)
    assert out["source"] == "rules"
    assert isinstance(out["shock"], dict)
    engine.Shock(**{k: v for k, v in out["shock"].items() if k != "reemploy_month"})  # still a valid Shock


def test_parse_event_empty_text_applies_no_shock():
    out = agent.parse_event("", use_gemini=False)
    assert out["shock"]["ei_pct"] is None and out["shock"]["one_off"] == 0.0


def test_parse_event_falls_back_to_rules_when_gemini_errors(monkeypatch):
    monkeypatch.setattr(agent, "_env", lambda: ("fake-key", "fake-model"))
    def boom(*a, **k):
        raise RuntimeError("503 unavailable")
    monkeypatch.setattr(agent, "_gemini_json", boom)
    out = agent.parse_event("I lost my job", use_gemini=True)
    assert out["source"] == "rules" and out["errors"] and out["shock"]["ei_pct"] == 0.55


def test_parse_event_survives_gemini_returning_garbage_json(monkeypatch):
    monkeypatch.setattr(agent, "_env", lambda: ("fake-key", "fake-model"))
    monkeypatch.setattr(agent, "_gemini_json", lambda *a, **k: "not json {{{")
    out = agent.parse_event("rent up $200", use_gemini=True)
    assert out["source"] == "rules" and out["shock"]["rent_up"] == 200.0
