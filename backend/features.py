"""Per (account, month t) features using only months <= t, plus forecast targets.

Shared by the forecast (Topic 5) and the risk flag (Topic 12). Every feature is a
backward-looking window within one account; targets use shift(-h) and are the only
forward-looking columns.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend import engine

HORIZONS = (1, 2, 3)
FEATURES = [
    "bal", "net", "net_med", "net_slope6", "in_med3", "in_med6", "in_med12",
    "out_med3", "out_med6", "out_med12", "in_cv12", "bills_share12", "loan_share12",
    "adb_slope6", "minbal3", "months_since_neg", "age", "month_sin", "month_cos",
    "bal_mean12", "bal_dev6", "bal_dev12",
]
# columns that are not dollar amounts (left unscaled when features are divided by `scale`)
UNITLESS = {"in_cv12", "bills_share12", "loan_share12", "months_since_neg", "age",
            "month_sin", "month_cos"}


def _roll(g: pd.core.groupby.SeriesGroupBy, w: int, how: str) -> pd.Series:
    r = getattr(g.rolling(w, min_periods=1), how)()
    return r.reset_index(level=0, drop=True)


def _slope(df: pd.DataFrame, col: str, w: int) -> pd.Series:
    """Least-squares slope per month over the last w rows (fewer at the start)."""
    gb = df.groupby("account_id")[col]
    ys = [gb.shift(k) for k in range(w)]  # k months ago
    y = pd.concat(ys, axis=1)
    x = -np.arange(w, dtype=float)  # time of each lag relative to t
    mask = y.notna().to_numpy()
    yv = np.nan_to_num(y.to_numpy())
    n = mask.sum(1)
    sx = (mask * x).sum(1)
    sy = yv.sum(1)
    sxx = (mask * x * x).sum(1)
    sxy = (yv * x).sum(1)
    den = n * sxx - sx * sx
    with np.errstate(divide="ignore", invalid="ignore"):
        slope = np.where(den > 0, (n * sxy - sx * sy) / den, 0.0)
    return pd.Series(slope, index=df.index)


def build(monthly: pd.DataFrame | None = None) -> pd.DataFrame:
    m = engine.load_monthly() if monthly is None else monthly
    m = m.sort_values(["account_id", "month"], kind="mergesort").reset_index(drop=True)
    acct = m["account_id"]
    f = pd.DataFrame({"account_id": acct, "month": m["month"]})
    f["bal"] = m["month_end_balance"]
    f["net"] = m["money_in"] - m["money_out"]
    g = lambda s: s.groupby(acct)  # noqa: E731
    f["net_med"] = g(f["net"]).expanding().median().reset_index(level=0, drop=True)
    tmp = pd.DataFrame({"account_id": acct, "net": f["net"], "adb": m["avg_daily_balance"]})
    f["net_slope6"] = _slope(tmp, "net", 6)
    f["adb_slope6"] = _slope(tmp, "adb", 6)
    for w in (3, 6, 12):
        f[f"in_med{w}"] = _roll(g(m["money_in"]), w, "median")
        f[f"out_med{w}"] = _roll(g(m["money_out"]), w, "median")
    in_mean = _roll(g(m["money_in"]), 12, "mean")
    in_std = _roll(g(m["money_in"]), 12, "std").fillna(0.0)
    f["in_cv12"] = np.where(in_mean > 0, in_std / in_mean.where(in_mean > 0, 1), 0.0)
    out12 = _roll(g(m["money_out"]), 12, "sum")
    for name, col in (("bills_share12", "household_bills"), ("loan_share12", "loan_payments")):
        s = _roll(g(m[col]), 12, "sum")
        f[name] = np.where(out12 > 0, s / out12.where(out12 > 0, 1), 0.0)
    f["minbal3"] = _roll(g(m["min_balance"]), 3, "min")
    idx = g(acct).cumcount()
    last_neg = idx.where(m["days_below_zero"] > 0).groupby(acct).ffill()
    f["months_since_neg"] = (idx - last_neg).fillna(60).clip(upper=60)
    f["age"] = idx
    mon = m["month"].str[5:7].astype(int)
    f["month_sin"] = np.sin(2 * np.pi * mon / 12)
    f["month_cos"] = np.cos(2 * np.pi * mon / 12)
    f["bal_mean12"] = _roll(g(f["bal"]), 12, "mean")
    f["bal_dev6"] = f["bal"] - _roll(g(f["bal"]), 6, "mean")   # mean reversion signal
    f["bal_dev12"] = f["bal"] - f["bal_mean12"]
    f["scale"] = _roll(g(f["net"]), 12, "std").fillna(0.0).clip(lower=50.0)
    for h in HORIZONS:
        f[f"y{h}"] = g(f["net"]).shift(-h)
        f[f"bal{h}"] = g(f["bal"]).shift(-h)
    return f
