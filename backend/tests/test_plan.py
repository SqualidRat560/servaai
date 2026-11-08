"""Plan builder (Topic 8)."""
from __future__ import annotations

import pytest

from backend import engine, plan


@pytest.mark.parametrize("aid", [63816, 32078, 99477])
@pytest.mark.parametrize("twist", list(engine.TWISTS))
def test_backup_rules(aid, twist):
    out = plan.build_plan(aid, engine.TWISTS[twist])
    b = out["backup"]
    for c in b["cuts"]:
        assert c["category"] in plan.FLEXIBLE and c["category"] not in plan.FIXED
        assert c["cut"] <= c["median"] * plan.MAX_CUT + 1e-6
    inf = lambda r: float("inf") if r["value"] is None else r["value"]  # noqa: E731
    assert inf(b["runway_after"]) >= inf(b["runway_before"])
    assert b["monthly_savings"] == pytest.approx(sum(c["cut"] for c in b["cuts"]))


def test_no_cuts_when_runway_already_long_enough():
    out = plan.build_plan(63816, engine.TWISTS["furnace_1mo"])  # 98.3 months
    assert out["backup"]["cuts"] == [] and out["backup"]["monthly_savings"] == 0


def test_goal_numbers_63816():
    p = engine.profile(63816)
    g = plan.build_plan(63816)["goal"]
    assert g["target_3_months"] == pytest.approx(3 * p.S)
    assert g["surplus_monthly"] == pytest.approx(p.I - p.S)
    assert g["asp_weekly"] == 0  # spending exceeds income: no surplus to save


def test_asp_is_half_the_surplus_per_week():
    ids = engine.get_profiles().index
    aid = next(a for a in ids[:500] if engine.profile(a).I > engine.profile(a).S + 100)
    p = engine.profile(aid)
    g = plan.build_plan(aid)["goal"]
    assert g["asp_weekly"] == pytest.approx(0.5 * (p.I - p.S) / (52 / 12))


def test_cuts_raise_runway_for_63816_job_loss():
    b = plan.build_plan(63816, engine.TWISTS["layoff_ei55"])["backup"]
    assert b["steps"] > 0 and b["runway_after"]["value"] > b["runway_before"]["value"]


def test_tools_named():
    tools = [t["tool"] for t in plan.build_plan(63816, engine.TWISTS["layoff_ei55"])["tools"]]
    assert tools == ["Automatic Savings Program + Goals", "Money Rules", "Orange Alerts",
                     "Left to Spend + Insights"]
