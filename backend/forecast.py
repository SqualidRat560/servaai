"""3-month balance forecast: regression ladder with an honest backtest (Topic 5).

    python -m backend.forecast        # run the backtest, write docs/backtest.md, save models

Ladder: flat (balance unchanged) -> statistical baseline (median net flow + damped trend)
-> Ridge (one model per horizon) -> XGBoost (one model per horizon, absolute-error loss on
flows divided by each account's own volatility, early stopping on 2024). Time split by origin month t:
train 2020-07..2023-09, validate 2024-01..09, test 2025-01..09.
Trajectory = balance at t + cumulative predicted net flows. Event shocks are added by the
engine on top of the predicted normal path.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from backend import engine, features, realistic

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = engine.CACHE_DIR / "forecast.joblib"
REPORT = ROOT / "docs" / "backtest.md"
SPLITS = {"train": ("2020-07", "2023-09"), "val": ("2024-01", "2024-09"), "test": ("2025-01", "2025-09")}
H = features.HORIZONS
ALPHAS = [0.01, 0.1, 1, 10, 100, 1000, 10000]
DAMP = 0.5


def _split(f: pd.DataFrame, name: str) -> pd.DataFrame:
    a, b = SPLITS[name]
    ok = f["month"].between(a, b)
    for h in H:
        ok &= f[f"y{h}"].notna()
    return f[ok]


def baseline_flows(df: pd.DataFrame) -> np.ndarray:
    """Statistical baseline: flow at h = median net flow so far + DAMP * 6-month slope * h."""
    return np.column_stack([df["net_med"] + DAMP * df["net_slope6"] * h for h in H])


def _cum_balance(df: pd.DataFrame, flows: np.ndarray) -> np.ndarray:
    return df["bal"].to_numpy()[:, None] + np.cumsum(flows, axis=1)


def _actual(df: pd.DataFrame) -> np.ndarray:
    return np.column_stack([df[f"bal{h}"] for h in H])


def _metrics(pred: np.ndarray, actual: np.ndarray) -> dict:
    err = np.abs(pred - actual)
    pct = err / np.maximum(np.abs(actual), 100.0)
    return {f"h{h}": (float(err[:, i].mean()), float(np.median(pct[:, i]) * 100)) for i, h in enumerate(H)}


def _fit_ridge(train: pd.DataFrame, alpha: float) -> dict:
    X = train[features.FEATURES].to_numpy()
    return {h: make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(X, train[f"y{h}"]) for h in H}


def ridge_flows(models: dict, df: pd.DataFrame) -> np.ndarray:
    X = df[features.FEATURES].to_numpy()
    return np.column_stack([models[h].predict(X) for h in H])


def _X_scaled(df: pd.DataFrame) -> np.ndarray:
    x = df[features.FEATURES].copy()
    money = [c for c in features.FEATURES if c not in features.UNITLESS]
    x[money] = x[money].div(df["scale"], axis=0)
    return x.to_numpy()


def _fit_xgb(train: pd.DataFrame, val: pd.DataFrame) -> dict:
    models = {}
    for h in H:
        m = XGBRegressor(n_estimators=600, learning_rate=0.05, max_depth=6, subsample=0.8,
                         colsample_bytree=0.8, objective="reg:absoluteerror",
                         early_stopping_rounds=40, n_jobs=-1, verbosity=0, random_state=0)
        m.fit(_X_scaled(train), train[f"y{h}"] / train["scale"],
              eval_set=[(_X_scaled(val), val[f"y{h}"] / val["scale"])], verbose=False)
        models[h] = m
    return models


def xgb_flows(models: dict, df: pd.DataFrame) -> np.ndarray:
    X = _X_scaled(df)
    return np.column_stack([models[h].predict(X) for h in H]) * df["scale"].to_numpy()[:, None]


def model_flows(b: dict, df: pd.DataFrame, which: str | None = None) -> np.ndarray:
    which = which or b["winner"]
    if which == "baseline":
        return baseline_flows(df)
    if which == "ridge":
        return ridge_flows(b["ridge"], df)
    return xgb_flows(b["xgboost"], df)


def backtest(write: bool = True) -> dict:
    f = features.build()
    tr, va, te = (_split(f, s) for s in ("train", "val", "test"))
    # choose alpha on the 2024 validation months (balance MAE averaged over h = 1..3)
    scores = {}
    for a in ALPHAS:
        m = _fit_ridge(tr, a)
        scores[a] = float(np.abs(_cum_balance(va, ridge_flows(m, va)) - _actual(va)).mean())
    alpha = min(scores, key=scores.get)
    ridge_tr = _fit_ridge(tr, alpha)                      # for validation errors (band)
    ridge = _fit_ridge(pd.concat([tr, va]), alpha)        # refit on train + val, test on 2025

    xgbm = _fit_xgb(tr, va)  # trained on train only; 2024 is used for early stopping
    preds = {
        "flat": np.repeat(te["bal"].to_numpy()[:, None], len(H), axis=1),
        "baseline": _cum_balance(te, baseline_flows(te)),
        "ridge": _cum_balance(te, ridge_flows(ridge, te)),
        "xgboost": _cum_balance(te, xgb_flows(xgbm, te)),
    }
    actual = _actual(te)
    results = {k: _metrics(v, actual) for k, v in preds.items()}
    avg = {k: float(np.mean([results[k][f"h{h}"][0] for h in H])) for k in results}
    winner = min(("baseline", "ridge", "xgboost"), key=lambda k: avg[k])

    # band: P10/P90 of the winner's 2024 validation errors, scaled by each account's volatility
    val_flows = {"baseline": lambda: baseline_flows(va), "ridge": lambda: ridge_flows(ridge_tr, va),
                 "xgboost": lambda: xgb_flows(xgbm, va)}[winner]()
    scale_va, scale_te = va["scale"].to_numpy()[:, None], te["scale"].to_numpy()[:, None]
    z = (_actual(va) - _cum_balance(va, val_flows)) / scale_va
    quantiles = {h: (float(np.quantile(z[:, i], 0.10)), float(np.quantile(z[:, i], 0.90)))
                 for i, h in enumerate(H)}
    lo = preds[winner] + np.array([quantiles[h][0] for h in H]) * scale_te
    hi = preds[winner] + np.array([quantiles[h][1] for h in H]) * scale_te
    coverage = float(((actual >= lo) & (actual <= hi)).mean())

    last_rows = f.groupby("account_id").tail(1).set_index("account_id")
    bundle = {"winner": winner, "alpha": alpha, "ridge": ridge, "xgboost": xgbm, "quantiles": quantiles,
              "results": results, "avg_mae": avg, "coverage": coverage,
              "rows": {"train": len(tr), "val": len(va), "test": len(te)},
              "last_rows": last_rows[features.FEATURES + ["month", "scale"]]}
    if write:
        engine.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle, BUNDLE)
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(_report(bundle), encoding="utf-8")
    return bundle


def _report(b: dict) -> str:
    names = {"flat": "Flat (balance unchanged)", "baseline": "Statistical baseline",
             "ridge": f"Ridge (alpha={b['alpha']:g})",
             "xgboost": "XGBoost (absolute error, volatility-scaled)"}
    lines = ["# Forecast backtest (month-end balance, next 3 months)", "",
             f"Origins: train 2020-07..2023-09 ({b['rows']['train']:,} rows), validate 2024-01..09 "
             f"({b['rows']['val']:,}), test 2025-01..09 ({b['rows']['test']:,}). "
             "No feature uses any month after the origin.", "",
             "Test set (2025). MAE in dollars; MdAPE = median of |error| / max(|actual balance|, $100).", "",
             "| Model | MAE h=1 | MAE h=2 | MAE h=3 | MdAPE h=1 | MdAPE h=2 | MdAPE h=3 |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for k, r in b["results"].items():
        lines.append(f"| {names[k]} | " + " | ".join(f"{r[f'h{h}'][0]:,.0f}" for h in H) + " | "
                     + " | ".join(f"{r[f'h{h}'][1]:.1f}%" for h in H) + " |")
    flat, win = b["avg_mae"]["flat"], b["avg_mae"][b["winner"]]
    verdict = (f"**{names[b['winner']]}** wins and powers the app: average MAE {win:,.0f} vs "
               f"{flat:,.0f} for the flat baseline ({(1 - win / flat) * 100:+.1f}% better)."
               if win < flat else
               f"**Honest result:** no model beats the flat baseline on average MAE "
               f"({win:,.0f} vs {flat:,.0f}). The app still shows {names[b['winner']]} but says so.")
    lines += ["", verdict, "",
              f"Uncertainty band: P10-P90 of the winner's 2024 validation errors, scaled per account by "
              f"its 12-month net-flow volatility. Share of 2025 test balances inside the band: "
              f"{b['coverage'] * 100:.1f}% (target 80%).", ""]
    return "\n".join(lines)


@lru_cache(maxsize=1)
def load_bundle() -> dict:
    if not BUNDLE.exists():
        return backtest(write=True)
    return joblib.load(BUNDLE)


def _next_months(last: str, n: int = 3) -> list[str]:
    p = pd.Period(last, freq="M")
    return [str(p + i) for i in range(1, n + 1)]


def forecast(account_id, shock: engine.Shock | None = None, cap: bool = True,
             reemploy_month: int | None = None) -> dict:
    """Next 3 month-end balances: normal path + band, and the path after the shock."""
    p = engine.profile(account_id)
    b = load_bundle()
    row = b["last_rows"].loc[[p.account_id]]
    flows = model_flows(b, row)[0]
    bal0 = float(row["bal"].iloc[0])
    scale = float(row["scale"].iloc[0])
    base = bal0 + np.cumsum(flows)
    lo = [float(base[i] + b["quantiles"][h][0] * scale) for i, h in enumerate(H)]
    hi = [float(base[i] + b["quantiles"][h][1] * scale) for i, h in enumerate(H)]
    out = {"account_id": p.account_id, "model": b["winner"], "start_month": str(row["month"].iloc[0]),
           "start_balance": bal0, "months": _next_months(str(row["month"].iloc[0])),
           "base": [float(x) for x in base], "p10": lo, "p90": hi, "shocked": None}
    if shock is not None:
        s = engine.apply_shock(p, shock)
        shocked_flows = []
        for i, h in enumerate(H):
            income = realistic.income_in_month(p, shock, h, realistic.DEFAULT_EI_MONTHS, cap, reemploy_month)
            delta = (income - p.I) - (s.S_new - p.S) - (s.one_off if h == 1 else 0.0)
            shocked_flows.append(flows[i] + delta)
        out["shocked"] = [float(x) for x in bal0 + np.cumsum(shocked_flows)]
    return out


if __name__ == "__main__":
    bnd = backtest(write=True)
    print(REPORT.read_text(encoding="utf-8"))
