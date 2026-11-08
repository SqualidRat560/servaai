"""Phase 1 gate: the judge engine matches an independent check on all 4,500 accounts."""
from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend import engine
from backend.tests import independent_check

TESTS = Path(__file__).resolve().parent
METRICS = ("I", "F", "S", "B", "H", "P")
CENT = 0.005


@pytest.fixture(scope="module")
def profiles() -> pd.DataFrame:
    return engine.precompute_profiles(force=True)


@pytest.fixture(scope="module")
def indep() -> pd.DataFrame:
    return pd.DataFrame.from_dict(independent_check.compute_all(), orient="index")


# ------------------------------------------------ 100% match vs the independent check

def test_same_4500_accounts(profiles, indep):
    assert len(profiles) == 4500
    assert set(profiles.index) == set(indep.index)


@pytest.mark.parametrize("metric", METRICS)
def test_judge_numbers_match_independent_all_accounts(profiles, indep, metric):
    diff = (profiles[metric] - indep.loc[profiles.index, metric]).abs()
    bad = diff[diff > CENT]
    assert bad.empty, f"{metric}: {len(bad)} accounts differ, e.g. {bad.head().to_dict()}"


@pytest.mark.parametrize("twist", list(engine.TWISTS))
def test_readme_twists_match_independent_all_accounts(profiles, indep, twist):
    ours = engine.judge_runway_all(engine.TWISTS[twist], profiles)["value"]
    theirs = indep.loc[profiles.index, twist].astype(float)  # None -> NaN = no shortfall
    same = (ours == theirs) | (ours.isna() & theirs.isna())
    assert same.all(), f"{twist}: {int((~same).sum())} accounts differ, e.g. " \
                       f"{pd.DataFrame({'engine': ours, 'independent': theirs})[~same].head()}"


@pytest.mark.parametrize("twist", list(engine.TWISTS))
def test_single_account_path_equals_all_accounts_path(profiles, twist):
    shock = engine.TWISTS[twist]
    allv = engine.judge_runway_all(shock, profiles)
    for aid in profiles.index:
        p = engine.profile(aid)
        s = engine.apply_shock(p, shock)
        r = engine.judge_runway(p.B, s.one_off, s.S_new, s.I_new)
        row = allv.loc[aid]
        assert r.status == row["status"], aid
        if r.value is None:
            assert math.isnan(row["value"]), aid
        else:
            assert r.value == row["value"], aid


# ------------------------------------------------ edge cases from the data

def test_edge_case_counts(profiles):
    assert int(profiles["b_nonpos"].sum()) == 23
    assert int(profiles["i_zero"].sum()) == 14
    assert int(profiles["s_zero"].sum()) == 77
    assert int(profiles["ends_early"].sum()) == 76
    assert int(profiles["n_months"].min()) >= 6


def test_nonpositive_buffer_is_zero_under_every_twist(profiles):
    ids = profiles.index[profiles["b_nonpos"]]
    for shock in engine.TWISTS.values():
        out = engine.judge_runway_all(shock, profiles).loc[ids]
        assert (out["value"] == 0.0).all() and (out["status"] == "zero").all()


def test_b_uses_the_accounts_own_last_6_rows():
    m = engine.load_monthly()
    rows = m[m["account_id"] == 99477]
    assert rows["month"].iloc[-1] == "2024-03"
    expected = rows["avg_daily_balance"].iloc[-6:].mean()
    assert engine.profile(99477).B == pytest.approx(expected, abs=1e-9)


def test_three_answer_key_accounts_have_their_roles():
    normal, neg, early = engine.profile(63816), engine.profile(32078), engine.profile(99477)
    assert normal.loan_status == "C" and normal.P > 0 and normal.H > 0 and normal.n_months == 69
    assert neg.B <= 0
    assert early.ends_early and early.last_month == "2024-03" and early.I == 0


# ------------------------------------------------ runway rules

def test_rule_buffer_used_up_is_zero():
    r = engine.judge_runway(B=100.0, one_off=100.0, S_new=50.0, I_new=0.0)
    assert (r.value, r.status) == (0.0, "zero")
    assert engine.judge_runway(-5.0, 0.0, 50.0, 0.0).value == 0.0


def test_rule_buffer_check_comes_before_gap_check():
    r = engine.judge_runway(B=-1.0, one_off=0.0, S_new=10.0, I_new=50.0)  # gap < 0 too
    assert r.status == "zero" and r.value == 0.0


@pytest.mark.parametrize("S_new,I_new", [(50.0, 60.0), (50.0, 50.0)])
def test_rule_no_shortfall(S_new, I_new):
    r = engine.judge_runway(B=100.0, one_off=0.0, S_new=S_new, I_new=I_new)
    assert r.value is None and r.status == "no_shortfall" and r.label == "no shortfall (120+)"


def test_rule_cap_at_120():
    r = engine.judge_runway(B=1000.0, one_off=0.0, S_new=5.0, I_new=0.0)  # 200 months
    assert (r.value, r.status) == (120.0, "capped")


def test_rule_rounds_half_up_to_one_decimal():
    assert engine.judge_runway(B=1.25, one_off=0.0, S_new=1.0, I_new=0.0).value == 1.3
    assert engine.judge_runway(B=1.24, one_off=0.0, S_new=1.0, I_new=0.0).value == 1.2
    assert engine.round_half_up(0.25) == 0.3  # Python's round() would give 0.2
    assert engine.round_half_up(2.45) == 2.5 and engine.round_half_up(0.05) == 0.1


def test_loan_payment_is_never_added():
    assert "P" not in inspect.signature(engine.judge_runway).parameters
    p = engine.profile(63816)
    for shock in engine.TWISTS.values():
        a = engine.apply_shock(p, shock)
        b = engine.apply_shock(dataclasses.replace(p, P=p.P * 10 + 999), shock)
        assert a == b


def test_mixed_shock_is_additive():
    p = engine.profile(63816)
    s = engine.apply_shock(p, engine.Shock(ei_pct=0.55, bills_up_pct=0.15, rent_up=200,
                                           repair_months=1, one_off=500))
    assert s.I_new == pytest.approx(0.55 * p.I)
    assert s.S_new == pytest.approx(p.S + 0.15 * p.H + 200)
    assert s.one_off == pytest.approx(p.S + 500)


def test_readme_twist_examples_on_the_normal_account():
    p = engine.profile(63816)
    r1 = engine.run(63816, engine.TWISTS["layoff_ei55"])["judge_runway"]
    assert r1["value"] == engine.round_half_up(p.B / (p.S - 0.55 * p.I))
    r2 = engine.run(63816, engine.TWISTS["furnace_1mo"])["judge_runway"]
    assert r2["value"] == engine.round_half_up((p.B - p.S) / (p.S - p.I))
    r3 = engine.run(63816, engine.TWISTS["layoff_ei55_bills15"])["judge_runway"]
    assert r3["value"] == engine.round_half_up(p.B / (p.S + 0.15 * p.H - 0.55 * p.I))


# ------------------------------------------------ input handling

@pytest.mark.parametrize("bad", [1, -7, "abc", None, "", True])
def test_unknown_account_raises(bad):
    with pytest.raises(engine.UnknownAccount):
        engine.profile(bad)


def test_account_id_as_text_works():
    assert engine.profile(" 63816 ") == engine.profile(63816)


@pytest.mark.parametrize("kwargs", [{"ei_pct": 1.5}, {"ei_pct": -0.1}, {"repair_months": -1},
                                    {"one_off": -5}, {"rent_up": float("nan")},
                                    {"bills_up_pct": float("inf")}])
def test_bad_shock_values_raise(kwargs):
    with pytest.raises(ValueError):
        engine.Shock(**kwargs)


# ------------------------------------------------ cache and independence

def test_cache_round_trip_is_exact(profiles):
    assert engine.CACHE_FILE.exists()
    cached = engine.precompute_profiles()
    pd.testing.assert_frame_equal(cached, profiles, check_dtype=False)


def test_independent_check_does_not_import_the_engine_or_pandas():
    tree = ast.parse((TESTS / "independent_check.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    banned = {n for n in names if n.split(".")[0] in {"pandas", "numpy", "engine"}
              or n.startswith("backend")}
    assert not banned, banned


# ------------------------------------------------ hand-made answer key (filled by the team)

def test_answer_key_hand_values():
    key = json.loads((TESTS / "answer_key.json").read_text(encoding="utf-8"))["accounts"]
    checked = 0
    for aid, entry in key.items():
        p = engine.profile(int(aid))
        for name, hand in entry["hand"].items():
            if hand is None:
                continue
            if name in METRICS:
                assert getattr(p, name) == pytest.approx(float(hand), abs=0.01), (aid, name)
            else:
                r = engine.run(int(aid), engine.TWISTS[name])["judge_runway"]
                if isinstance(hand, str):
                    assert r["label"] == hand, (aid, name)
                else:
                    assert r["value"] == float(hand), (aid, name)
            checked += 1
    if checked == 0:
        pytest.skip("answer_key.json not filled yet: a teammate adds the hand-computed values")
