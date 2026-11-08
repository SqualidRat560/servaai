"""Portfolio finding across all 4,500 customers (Topic 9).

    python -m backend.population

Writes docs/findings.md, powerbi/exports/*.csv and backend/cache/portfolio.parquet.
Every number comes from backend.engine (judge) and backend.realistic (realistic runway).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from backend import engine, realistic

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "powerbi" / "exports"
FINDINGS = ROOT / "docs" / "findings.md"
CACHE = engine.CACHE_DIR / "portfolio.parquet"
HEADLINE_TWIST = "layoff_ei55"
CAP = 120.0
SEGMENTS = ["Stable", "Hidden fragile", "Fragile", "Already short"]

SHOCKS: dict[str, tuple[str, engine.Shock]] = {
    "layoff_ei55": ("Job loss, EI 55% (README 1)", engine.TWISTS["layoff_ei55"]),
    "furnace_1mo": ("Repair = 1 month of spending (README 2)", engine.TWISTS["furnace_1mo"]),
    "layoff_ei55_bills15": ("Job loss EI 55% + bills +15% (README 3)", engine.TWISTS["layoff_ei55_bills15"]),
    "bills_up15": ("Household bills +15%", engine.Shock(bills_up_pct=0.15)),
    "rent_up200": ("Rent +$200/month", engine.Shock(rent_up=200)),
    "scam_1000": ("Scam of $1,000", engine.Shock(one_off=1000)),
}


def attributes() -> pd.DataFrame:
    d = engine.DATA_DIR
    acc = pd.read_csv(d / "accounts.csv")
    dist = pd.read_csv(d / "districts.csv")[["district_id", "district_name", "region"]]
    disp = pd.read_csv(d / "dispositions.csv")
    cli = pd.read_csv(d / "clients.csv")
    cards = pd.read_csv(d / "cards.csv")
    owner = disp[disp["type"] == "owner"].merge(cli, on="client_id", how="left")
    owner = owner.merge(cards[["disposition_id", "card_type"]], on="disposition_id", how="left")
    a = acc.merge(dist, on="district_id", how="left").merge(
        owner[["account_id", "gender", "birth_date", "card_type"]], on="account_id", how="left")
    ref = pd.Timestamp("2025-12-31")
    age = (ref - pd.to_datetime(a["birth_date"])).dt.days / 365.25
    a["owner_age_band"] = pd.cut(age, [0, 30, 45, 60, 200], right=False,
                                 labels=["<30", "30-44", "45-59", "60+"]).astype(str)
    a["card_type"] = a["card_type"].fillna("none")
    yrs = (ref - pd.to_datetime(a["account_opened"])).dt.days / 365.25
    a["account_age_band"] = pd.cut(yrs, [0, 2, 5, 200], right=False,
                                   labels=["<2 years", "2-4 years", "5+ years"]).astype(str)
    a = a.drop_duplicates("account_id").set_index("account_id")
    return a[["district_name", "region", "gender", "owner_age_band", "card_type", "account_age_band"]]


def runways() -> pd.DataFrame:
    """Long table: account x shock with judge and realistic runway (None -> NaN, status kept)."""
    prof = engine.get_profiles()
    rows = []
    for key, (label, shock) in SHOCKS.items():
        j = engine.judge_runway_all(shock, prof)
        for aid in prof.index:
            r = realistic.realistic_runway(engine.profile(aid), shock)
            rows.append((aid, key, label, j.at[aid, "value"], j.at[aid, "status"],
                         np.nan if r.value is None else r.value, r.status))
    return pd.DataFrame(rows, columns=["account_id", "shock", "shock_label", "judge", "judge_status",
                                       "realistic", "realistic_status"])


def _eff(v: pd.Series) -> pd.Series:
    """No shortfall counts as the 120-month cap when comparing runways."""
    return v.fillna(CAP)


def segment(judge: pd.Series, judge_status: pd.Series, real: pd.Series) -> pd.Series:
    j, r = _eff(judge), _eff(real)
    seg = np.select([judge_status == "zero", j < 6, r < 6], ["Already short", "Fragile", "Hidden fragile"],
                    default="Stable")
    return pd.Series(seg, index=judge.index)


def bootstrap(flags: np.ndarray, n: int = 1000, seed: int = 0) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(flags), size=(n, len(flags)))
    means = flags[idx].mean(axis=1)
    return float(flags.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def build(write: bool = True) -> dict:
    prof = engine.get_profiles()
    attrs = attributes()
    long = runways()
    head = long[long["shock"] == HEADLINE_TWIST].set_index("account_id").loc[prof.index]
    j, r = _eff(head["judge"]), _eff(head["realistic"])
    flags = {
        "judge_under_6": (j < 6).to_numpy(float),
        "realistic_under_6": (r < 6).to_numpy(float),
        "overstated_by_6plus": ((j - r) > 6).to_numpy(float),
    }
    headline = {k: bootstrap(v) for k, v in flags.items()}
    seg = segment(head["judge"], head["judge_status"], head["realistic"])

    acc = prof[["I", "F", "S", "B", "H", "P", "n_months", "last_month"]].join(attrs)
    acc["judge_ei55"] = head["judge"]
    acc["realistic_ei55"] = head["realistic"]
    acc["judge_ei55_label"] = np.where(head["judge_status"] == "no_shortfall", "no shortfall (120+)",
                                       head["judge"].round(1).astype(str))
    acc["overstatement_months"] = (j - r).round(1)
    acc["segment"] = seg

    by = {}
    for dim in ("region", "owner_age_band", "card_type", "account_age_band", "gender"):
        t = pd.crosstab(acc[dim], acc["segment"], normalize="index").reindex(columns=SEGMENTS, fill_value=0)
        t.insert(0, "customers", acc[dim].value_counts())
        by[dim] = t.sort_values("Hidden fragile", ascending=False)

    shock_tbl = long.assign(j=_eff(long["judge"]), r=_eff(long["realistic"])).groupby("shock").agg(
        label=("shock_label", "first"),
        judge_under_6=("j", lambda s: (s < 6).mean()),
        realistic_under_6=("r", lambda s: (s < 6).mean()),
        median_judge=("j", "median"), median_realistic=("r", "median"),
    ).loc[list(SHOCKS)]

    out = {"headline": headline, "segments": seg.value_counts().reindex(SEGMENTS, fill_value=0),
           "by": by, "shocks": shock_tbl, "accounts": acc, "long": long}
    if write:
        _write(out)
    return out


def _pct(t: tuple[float, float, float]) -> str:
    return f"{t[0]:.1%} (95% CI {t[1]:.1%} to {t[2]:.1%})"


def _write(o: dict) -> None:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    o["accounts"].to_csv(EXPORTS / "accounts.csv")
    o["long"].to_csv(EXPORTS / "shock_runways.csv", index=False)
    pd.DataFrame([{"metric": k, "share": v[0], "ci_low": v[1], "ci_high": v[2]}
                  for k, v in o["headline"].items()]).to_csv(EXPORTS / "headline.csv", index=False)
    for dim, t in o["by"].items():
        t.to_csv(EXPORTS / f"segments_by_{dim}.csv")
    o["shocks"].to_csv(EXPORTS / "shock_comparison.csv")
    engine.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    o["accounts"].to_parquet(CACHE)
    h, n = o["headline"], len(o["accounts"])
    seg = o["segments"]
    lines = [
        "# ServaAI findings (all 4,500 customers)", "",
        "Shock: README twist 1, job loss with EI at 55% of usual income. Judge = the track's formula "
        "(EI forever, no cap). Realistic = EI stops after 6 months and is capped at $729/week.", "",
        "## Headline", "",
        f"- **The judge formula overstates runway by more than 6 months for {_pct(h['overstated_by_6plus'])} of customers.**",
        f"- Under 6 months of runway: judge formula {_pct(h['judge_under_6'])}; realistic {_pct(h['realistic_under_6'])}.",
        f"- Intervals: 1,000 bootstrap resamples of the {n:,} accounts.", "",
        "## Segments", "",
        "| Segment | Rule | Customers | Share |", "|---|---|---:|---:|",
    ]
    rules = {"Stable": "realistic runway 6+ months or no shortfall",
             "Hidden fragile": "judge says 6+ months, realistic says under 6",
             "Fragile": "judge already under 6 months", "Already short": "buffer B <= 0"}
    for s in SEGMENTS:
        lines.append(f"| {s} | {rules[s]} | {seg[s]:,} | {seg[s] / n:.1%} |")
    lines += ["", "## Shock comparison (share under 6 months)", "",
              "| Shock | Judge | Realistic | Median judge | Median realistic |", "|---|---:|---:|---:|---:|"]
    for _, r in o["shocks"].iterrows():
        lines.append(f"| {r['label']} | {r['judge_under_6']:.1%} | {r['realistic_under_6']:.1%} | "
                     f"{r['median_judge']:.1f} | {r['median_realistic']:.1f} |")
    for dim, title in (("region", "region"), ("owner_age_band", "owner age")):
        t = o["by"][dim]
        lines += ["", f"## Hidden fragile share by {title}", "", f"| {title.capitalize()} | Customers | Hidden fragile |",
                  "|---|---:|---:|"]
        for k, r in t.iterrows():
            lines.append(f"| {k} | {int(r['customers']):,} | {r['Hidden fragile']:.1%} |")
    lines += ["", "## Caveats", "",
              "- money_in includes transfers and pensions, not only wages, so EI computed from it is an upper "
              "bound: real runways may be shorter still.",
              "- Medians of 120 mean 'no shortfall or 120+ months' (the track's cap).",
              "- Gender is shown as context only; it is not used in any score.", ""]
    FINDINGS.write_text("\n".join(lines), encoding="utf-8")


@lru_cache(maxsize=1)
def load_portfolio() -> pd.DataFrame:
    if not CACHE.exists():
        build(write=True)
    return pd.read_parquet(CACHE)


if __name__ == "__main__":
    build(write=True)
    print(FINDINGS.read_text(encoding="utf-8"))
