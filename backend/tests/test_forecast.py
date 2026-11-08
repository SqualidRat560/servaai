"""Forecast (Topic 5): no leakage, honest backtest, sensible output."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend import engine, features, forecast


@pytest.fixture(scope="module")
def full():
    return features.build()


def test_no_feature_uses_future_months(full):
    """Features at month t are identical when every month after t is deleted."""
    m = engine.load_monthly()
    rng = np.random.default_rng(7)
    accts = rng.choice(m["account_id"].unique(), 200, replace=False)
    parts, keys = [], []
    for a in accts:
        rows = m[m["account_id"] == a]
        t = rows["month"].iloc[rng.integers(0, len(rows))]
        parts.append(rows[rows["month"] <= t])
        keys.append((a, t))
    trunc = features.build(pd.concat(parts)).set_index(["account_id", "month"])
    ref = full.set_index(["account_id", "month"]).loc[keys, features.FEATURES + ["scale"]]
    got = trunc.loc[keys, features.FEATURES + ["scale"]]
    pd.testing.assert_frame_equal(got, ref, check_exact=False, rtol=1e-9, atol=1e-9)


def test_targets_are_future_net_flows(full):
    a = full[full["account_id"] == 63816].reset_index(drop=True)
    assert a.loc[10, "y1"] == pytest.approx(a.loc[11, "net"])
    assert a.loc[10, "bal3"] == pytest.approx(a.loc[13, "bal"])


def test_backtest_report_and_winner():
    b = forecast.load_bundle()
    assert set(b["results"]) == {"flat", "baseline", "ridge", "xgboost"}
    assert b["winner"] in {"baseline", "ridge", "xgboost"}
    assert b["rows"]["test"] > 30000
    assert forecast.REPORT.exists() and "Flat (balance unchanged)" in forecast.REPORT.read_text(encoding="utf-8")
    assert 0.6 <= b["coverage"] <= 0.95


def test_forecast_output_shape_and_band():
    out = forecast.forecast(63816)
    assert out["months"] == ["2026-01", "2026-02", "2026-03"]
    for lo, mid, hi in zip(out["p10"], out["base"], out["p90"]):
        assert lo <= mid <= hi
    assert out["shocked"] is None


def test_shock_lowers_the_path_by_the_engine_delta():
    p = engine.profile(63816)
    base = forecast.forecast(63816)
    shocked = forecast.forecast(63816, engine.TWISTS["layoff_ei55"])
    # EI 55% of I is capped at 3,159/month, so each month loses I - 3,159
    loss = p.I - min(0.55 * p.I, 3159.0)
    for h, (b0, s0) in enumerate(zip(base["base"], shocked["shocked"]), start=1):
        assert b0 - s0 == pytest.approx(loss * h, abs=0.01)


def test_one_off_hits_month_one_only():
    base = forecast.forecast(99477)
    shocked = forecast.forecast(99477, engine.Shock(one_off=1000))
    diffs = [b - s for b, s in zip(base["base"], shocked["shocked"])]
    assert diffs == pytest.approx([1000, 1000, 1000])


def test_early_ending_account_forecasts_after_its_last_month():
    out = forecast.forecast(99477)
    assert out["start_month"] == "2024-03" and out["months"][0] == "2024-04"
