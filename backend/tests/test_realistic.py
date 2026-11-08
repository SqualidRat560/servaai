"""Realistic runway (Topic 7): reduces to the judge formula when EI is unlimited."""
from __future__ import annotations

import math

import pytest

from backend import engine, realistic


@pytest.fixture(scope="module")
def ids():
    return list(engine.get_profiles().index)


@pytest.mark.parametrize("twist", list(engine.TWISTS))
def test_equals_judge_when_ei_forever_and_uncapped(ids, twist):
    shock = engine.TWISTS[twist]
    bad = []
    for aid in ids:
        p = engine.profile(aid)
        s = engine.apply_shock(p, shock)
        j = engine.judge_runway(p.B, s.one_off, s.S_new, s.I_new)
        r = realistic.realistic_runway(p, shock, ei_months=None, cap=False)
        if j.value is None or r.value is None:
            ok = j.value is None and r.value is None
        else:
            ok = abs(j.value - r.value) <= 0.1 + 1e-9
        if not ok:
            bad.append((aid, j.value, r.value))
    assert not bad, f"{len(bad)} differ, e.g. {bad[:5]}"


def test_no_job_loss_equals_judge_exactly(ids):
    for shock in (engine.TWISTS["furnace_1mo"], engine.Shock(bills_up_pct=0.2, rent_up=300)):
        for aid in ids[:1500]:
            p = engine.profile(aid)
            s = engine.apply_shock(p, shock)
            j = engine.judge_runway(p.B, s.one_off, s.S_new, s.I_new)
            r = realistic.realistic_runway(p, shock)
            assert (j.value, j.status) == (r.value, r.status), aid


def test_cap_and_ei_end_only_lower_runway_and_reemployment_only_raises(ids):
    shock = engine.TWISTS["layoff_ei55"]
    inf = lambda r: math.inf if r.value is None else r.value  # noqa: E731
    for aid in ids[::7]:
        p = engine.profile(aid)
        forever = inf(realistic.realistic_runway(p, shock, ei_months=None, cap=False))
        capped = inf(realistic.realistic_runway(p, shock, ei_months=None, cap=True))
        real = inf(realistic.realistic_runway(p, shock))
        back = inf(realistic.realistic_runway(p, shock, reemploy_month=4))
        assert capped <= forever and real <= capped and back >= real, aid


def test_known_account_63816():
    p = engine.profile(63816)
    r = realistic.realistic_runway(p, engine.TWISTS["layoff_ei55"])
    # EI = 0.55 * 12,792.06 = 7,035.63 > cap 3,159, so the burn is 12,863.41 - 3,159 = 9,704.41
    assert r.value == engine.round_half_up(p.B / (p.S - realistic.EI_MONTHLY_MAX))
    assert r.value < engine.run(63816, engine.TWISTS["layoff_ei55"])["judge_runway"]["value"]
    assert "capped" in r.reason


def test_zero_buffer_is_zero():
    p = engine.profile(32078)
    assert realistic.realistic_runway(p, engine.TWISTS["layoff_ei55"]).value == 0.0
