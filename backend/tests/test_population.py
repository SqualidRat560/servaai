"""Portfolio finding (Topic 9)."""
from __future__ import annotations

import pytest

from backend import engine, population


@pytest.fixture(scope="module")
def out():
    return population.build(write=True)


def test_segments_partition_all_accounts(out):
    assert int(out["segments"].sum()) == 4500
    assert out["segments"]["Already short"] == 23


def test_hidden_fragile_rule(out):
    a = out["accounts"]
    h = a[a["segment"] == "Hidden fragile"]
    j = h["judge_ei55"].fillna(120)
    r = h["realistic_ei55"].fillna(120)
    assert len(h) > 0 and (j >= 6).all() and (r < 6).all()


def test_intervals_contain_point_estimates(out):
    for share, lo, hi in out["headline"].values():
        assert lo <= share <= hi and 0 <= lo and hi <= 1


def test_headline_matches_engine_for_one_account(out):
    a = out["accounts"].loc[63816]
    assert a["judge_ei55"] == engine.run(63816, engine.TWISTS["layoff_ei55"])["judge_runway"]["value"]


def test_files_written(out):
    assert population.FINDINGS.exists() and (population.EXPORTS / "accounts.csv").exists()
    assert "overstates runway" in population.FINDINGS.read_text(encoding="utf-8")


def test_portfolio_api():
    from fastapi.testclient import TestClient
    from backend.app import app
    d = TestClient(app).get("/api/portfolio").json()
    assert len(d["points"]) == 4500 and d["headline"]["overstated_by_6plus"]["share"] > 0.2
