"""Event agent (Topic 6). Offline by default; set RUN_GEMINI=1 to also test the live Gemini path."""
from __future__ import annotations

import os

import pytest

from backend import agent, engine

# (text, expected shock fields, expected reemploy_month)
PHRASES = [
    # the 3 README twist cards, verbatim
    ("This customer was laid off. EI pays 55% of their usual income for 6 months. Do they make it?",
     {"ei_pct": 0.55}, None),
    ("The furnace dies, and the repair costs a full month of their typical spending.",
     {"repair_months": 1.0}, None),
    ("They lose their job (EI at 55%) and their household bills go up 15% in the same month.",
     {"ei_pct": 0.55, "bills_up_pct": 0.15}, None),
    # others
    ("I lost my job", {"ei_pct": 0.55}, None),
    ("I got laid off and EI pays 50%", {"ei_pct": 0.50}, None),
    ("My rent went up $200", {"rent_up": 200.0}, None),
    ("Landlord raised the rent by 150 dollars a month", {"rent_up": 150.0}, None),
    ("Household bills up 10%", {"bills_up_pct": 0.10}, None),
    ("My hydro bill increased 20%", {"bills_up_pct": 0.20}, None),
    ("I got scammed out of $1,500", {"one_off": 1500.0}, None),
    ("Someone phished my account and stole $2k", {"one_off": 2000.0}, None),
    ("The car repair is $1,200", {"one_off": 1200.0}, None),
    ("Our roof needs fixing, it will cost $8,000", {"one_off": 8000.0}, None),
    ("A repair that costs two months of spending", {"repair_months": 2.0}, None),
    ("My pay was cut 20%", {"ei_pct": 0.80}, None),
    ("Laid off with EI at 55%, but I start a new job in month 4", {"ei_pct": 0.55}, 4),
    ("Rent up 300 and bills up 5%", {"rent_up": 300.0, "bills_up_pct": 0.05}, None),
    ("I was fired and my utilities went up 12%", {"ei_pct": 0.55, "bills_up_pct": 0.12}, None),
    ("Vet emergency, $900", {"one_off": 900.0}, None),
    ("What a lovely day", {}, None),  # nothing financial
]
DEFAULTS = {"ei_pct": None, "bills_up_pct": 0.0, "rent_up": 0.0, "repair_months": 0.0, "one_off": 0.0}


def _matches(out: dict, expected: dict, reemploy) -> bool:
    want = DEFAULTS | expected
    got = out["shock"]
    for k, v in want.items():
        if v is None:
            if got[k] is not None:
                return False
        elif got[k] is None or abs(got[k] - v) > 1e-9:
            return False
    return got["reemploy_month"] == reemploy


def test_rule_parser_handles_the_3_readme_twists():
    for text, exp, re_m in PHRASES[:3]:
        out = agent.parse_event(text, use_gemini=False)
        assert out["source"] == "rules" and _matches(out, exp, re_m), (text, out["shock"])


def test_rule_parser_pass_rate():
    ok = [t for t, e, r in PHRASES if _matches(agent.parse_event(t, use_gemini=False), e, r)]
    missed = [t for t, e, r in PHRASES if t not in ok]
    assert len(ok) >= 15, f"rules parsed {len(ok)}/20; missed: {missed}"


def test_percent_normalisation_and_defaults():
    events, notes = agent.normalize(agent.ParsedEvents(events=[agent.Event(type="job_loss", pct=55)]))
    assert events[0].pct == 0.55
    events, notes = agent.normalize(agent.ParsedEvents(events=[agent.Event(type="job_loss")]))
    assert events[0].pct == 0.55 and any("assumed" in n for n in notes)
    events, notes = agent.normalize(agent.ParsedEvents(events=[agent.Event(type="rent_up")]))
    assert events == [] and notes


def test_events_map_to_engine_shock_and_numbers_come_from_the_engine():
    out = agent.parse_event(PHRASES[2][0], use_gemini=False)
    s = engine.Shock(**{k: v for k, v in out["shock"].items() if k != "reemploy_month"})
    assert engine.run(63816, s)["judge_runway"]["value"] == 3.1  # README twist 3 on 63816


def test_explain_rejects_invented_numbers():
    facts = {"judge_label": "3.4 months", "realistic_label": "2.0 months", "balance_now": 14201.18}
    assert agent.numbers_are_grounded("The formula says 3.4 months, realistically 2.0 months.", facts)[0]
    assert agent.numbers_are_grounded("You have $14,201 today.", facts)[0]
    ok, bad = agent.numbers_are_grounded("You will last 7.5 months.", facts)
    assert not ok and bad == [7.5]


def test_explain_template_uses_engine_numbers_only():
    f = agent.explain_facts(63816, engine.TWISTS["layoff_ei55"])
    out = agent.explain(f, use_gemini=False)
    assert out["source"] == "template" and "3.4 months" in out["text"] and "2.0 months" in out["text"]
    assert agent.numbers_are_grounded(out["text"], f)[0]


@pytest.mark.skipif(os.environ.get("RUN_GEMINI") != "1", reason="live Gemini test: set RUN_GEMINI=1")
def test_live_gemini_pass_rate():
    results = [(t, agent.parse_event(t)) for t, e, r in PHRASES]
    ok = [t for (t, out), (_, e, r) in zip(results, PHRASES) if _matches(out, e, r)]
    sources = {}
    for _, out in results:
        sources[out["source"]] = sources.get(out["source"], 0) + 1
    print(f"\nlive parse: {len(ok)}/20 correct; sources {sources}")
    for (t, out), (_, e, r) in zip(results, PHRASES):
        if t not in ok:
            print("  MISSED:", t, "->", out["shock"], out["source"], out["errors"][:1])
    assert len(ok) >= 18
