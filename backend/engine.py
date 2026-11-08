"""ServaAI judge engine.

Exact judge numbers (I, F, S, B, H, P) and the judge runway, following
data/README.md "How judges calculate the numbers" to the letter. Every number
the app shows is computed here or by modules built on top of this file.

Definitions (monthly_summary.csv sorted by account_id, month):
  I = median(money_in)            S = median(money_out)
  H = median(household_bills)     F = median(household_bills + insurance + loan_payments)
  B = mean(avg_daily_balance) over the account's LAST 6 rows
  P = loans.monthly_payment if the loan is still running (status C or D), else 0
Shocks: EI at p -> I' = p*I; bills up q -> S' = S + q*H; rent up r -> S' = S + r;
        repair of k months -> one_off = k*S; repair or scam of d dollars -> one_off = d.
Runway: buffer_left = B - one_off; gap = S' - I'
        buffer_left <= 0 -> 0; gap <= 0 -> "no shortfall (120+)";
        else min(buffer_left / gap, 120), rounded to 1 decimal.
S already includes loan payments, so P is never added to the runway.
"""
from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("SERVAAI_DATA_DIR", ROOT / "data"))
CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_FILE = CACHE_DIR / "profiles.parquet"

RUNWAY_CAP = 120.0
NO_SHORTFALL_LABEL = "no shortfall (120+)"
DATA_END_MONTH = "2025-12"
RUNNING_LOAN_STATUSES = ("C", "D")


class UnknownAccount(KeyError):
    """The account_id is not one of the 4,500 accounts."""


# ---------------------------------------------------------------- profiles

def load_monthly() -> pd.DataFrame:
    """monthly_summary.csv sorted by account_id, then month (stable sort)."""
    m = pd.read_csv(DATA_DIR / "monthly_summary.csv", dtype={"month": str})
    return m.sort_values(["account_id", "month"], kind="mergesort").reset_index(drop=True)


@lru_cache(maxsize=1)
def load_monthly_cached() -> pd.DataFrame:
    """load_monthly() kept in memory (do not mutate the result)."""
    return load_monthly()


def _compute_profiles() -> pd.DataFrame:
    m = load_monthly()
    g = m.groupby("account_id", sort=True)
    fixed_costs = m["household_bills"] + m["insurance"] + m["loan_payments"]
    last6 = g.tail(6)  # rows are sorted by month, so these are the last 6 rows
    prof = pd.DataFrame({
        "I": g["money_in"].median(),
        "F": fixed_costs.groupby(m["account_id"]).median(),
        "S": g["money_out"].median(),
        "B": last6.groupby("account_id")["avg_daily_balance"].mean(),
        "H": g["household_bills"].median(),
        "n_months": g.size(),
        "first_month": g["month"].first(),
        "last_month": g["month"].last(),
    })
    loans = pd.read_csv(DATA_DIR / "loans.csv").set_index("account_id")
    running_payment = loans["monthly_payment"].where(loans["status"].isin(RUNNING_LOAN_STATUSES))
    prof["P"] = running_payment.reindex(prof.index).fillna(0.0)
    prof["loan_status"] = loans["status"].reindex(prof.index).astype(object)
    prof["b_nonpos"] = prof["B"] <= 0
    prof["i_zero"] = prof["I"] == 0
    prof["s_zero"] = prof["S"] == 0
    prof["ends_early"] = prof["last_month"] < DATA_END_MONTH
    prof.index.name = "account_id"
    return prof


def precompute_profiles(force: bool = False) -> pd.DataFrame:
    """All 4,500 profiles, cached to backend/cache/profiles.parquet.

    The cache is rebuilt when it is missing or older than a source CSV.
    """
    sources = [DATA_DIR / "monthly_summary.csv", DATA_DIR / "loans.csv"]
    newest_source = max(p.stat().st_mtime for p in sources)
    if not force and CACHE_FILE.exists() and CACHE_FILE.stat().st_mtime >= newest_source:
        try:
            return pd.read_parquet(CACHE_FILE)
        except Exception:  # unreadable cache: rebuild below
            pass
    prof = _compute_profiles()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_DIR / "profiles.parquet.tmp"
        prof.to_parquet(tmp)
        os.replace(tmp, CACHE_FILE)
    except Exception:  # caching is an optimisation only
        pass
    return prof


@lru_cache(maxsize=1)
def get_profiles() -> pd.DataFrame:
    """Profiles held in memory for fast lookups (do not mutate the result)."""
    return precompute_profiles()


@dataclass(frozen=True)
class Profile:
    account_id: int
    I: float
    F: float
    S: float
    B: float
    H: float
    P: float
    n_months: int
    first_month: str
    last_month: str
    loan_status: str | None
    b_nonpos: bool
    i_zero: bool
    s_zero: bool
    ends_early: bool

    def to_dict(self) -> dict:
        return asdict(self)


def profile(account_id) -> Profile:
    """Judge numbers for one account. Raises UnknownAccount for a bad id."""
    if isinstance(account_id, bool):
        raise UnknownAccount(account_id)
    try:
        aid = int(str(account_id).strip())
    except (TypeError, ValueError):
        raise UnknownAccount(account_id) from None
    prof = get_profiles()
    if aid not in prof.index:
        raise UnknownAccount(aid)
    r = prof.loc[aid]
    return Profile(
        account_id=aid,
        I=float(r["I"]), F=float(r["F"]), S=float(r["S"]),
        B=float(r["B"]), H=float(r["H"]), P=float(r["P"]),
        n_months=int(r["n_months"]),
        first_month=str(r["first_month"]), last_month=str(r["last_month"]),
        loan_status=None if pd.isna(r["loan_status"]) else str(r["loan_status"]),
        b_nonpos=bool(r["b_nonpos"]), i_zero=bool(r["i_zero"]),
        s_zero=bool(r["s_zero"]), ends_early=bool(r["ends_early"]),
    )


# ---------------------------------------------------------------- shocks

@dataclass(frozen=True)
class Shock:
    """A shock or a mix of shocks; parts add up.

    ei_pct:        job loss with EI, income becomes ei_pct * I (0.55 = 55%). None = no job loss.
    bills_up_pct:  household bills up, S' = S + bills_up_pct * H (0.15 = 15%).
    rent_up:       rent up by this many dollars per month, S' = S + rent_up.
    repair_months: repair costing k months of typical spending, one_off = k * S.
    one_off:       repair or scam of d dollars, one_off = d.
    """
    ei_pct: float | None = None
    bills_up_pct: float = 0.0
    rent_up: float = 0.0
    repair_months: float = 0.0
    one_off: float = 0.0

    def __post_init__(self):
        values = {"bills_up_pct": self.bills_up_pct, "rent_up": self.rent_up,
                  "repair_months": self.repair_months, "one_off": self.one_off}
        if self.ei_pct is not None:
            values["ei_pct"] = self.ei_pct
        for name, v in values.items():
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
                raise ValueError(f"{name} must be a finite number, got {v!r}")
            if v < 0:
                raise ValueError(f"{name} cannot be negative, got {v!r}")
        if self.ei_pct is not None and self.ei_pct > 1:
            raise ValueError(f"ei_pct is a share of income between 0 and 1, got {self.ei_pct!r}")


@dataclass(frozen=True)
class ShockedInputs:
    I_new: float
    S_new: float
    one_off: float
    explanation: str


def apply_shock(p: Profile, shock: Shock) -> ShockedInputs:
    I_new = shock.ei_pct * p.I if shock.ei_pct is not None else p.I
    S_new = p.S + shock.bills_up_pct * p.H + shock.rent_up
    one_off = shock.repair_months * p.S + shock.one_off

    parts = []
    if shock.ei_pct is not None:
        parts.append(f"income I' = {shock.ei_pct:g} x I {p.I:,.2f} = {I_new:,.2f}")
    else:
        parts.append(f"income I' = I = {I_new:,.2f}")
    spend = f"spending S' = S {p.S:,.2f}"
    if shock.bills_up_pct:
        spend += f" + {shock.bills_up_pct:g} x H {p.H:,.2f}"
    if shock.rent_up:
        spend += f" + rent {shock.rent_up:,.2f}"
    parts.append(f"{spend} = {S_new:,.2f}")
    if one_off:
        cost = []
        if shock.repair_months:
            cost.append(f"{shock.repair_months:g} x S {p.S:,.2f}")
        if shock.one_off:
            cost.append(f"{shock.one_off:,.2f}")
        parts.append(f"one-off = {' + '.join(cost)} = {one_off:,.2f}")
    return ShockedInputs(I_new=I_new, S_new=S_new, one_off=one_off, explanation="; ".join(parts))


# ---------------------------------------------------------------- runway

def round_half_up(x: float, places: int = 1) -> float:
    """Round like a spreadsheet's ROUND (half away from zero for positives)."""
    quantum = Decimal(1).scaleb(-places)
    return float(Decimal(repr(float(x))).quantize(quantum, rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Runway:
    value: float | None  # months, 1 decimal; None means "no shortfall (120+)"
    status: str          # "zero" | "no_shortfall" | "finite" | "capped"
    label: str
    buffer_left: float
    gap: float
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


def judge_runway(B: float, one_off: float, S_new: float, I_new: float) -> Runway:
    """The judges' runway. There is deliberately no loan-payment input: S already includes it."""
    buffer_left = B - one_off
    gap = S_new - I_new
    if buffer_left <= 0:
        return Runway(0.0, "zero", "0.0 months", buffer_left, gap,
                      f"buffer left = B {B:,.2f} - one-off {one_off:,.2f} = {buffer_left:,.2f} <= 0, "
                      "so runway = 0 months")
    if gap <= 0:
        return Runway(None, "no_shortfall", NO_SHORTFALL_LABEL, buffer_left, gap,
                      f"gap = S' {S_new:,.2f} - I' {I_new:,.2f} = {gap:,.2f} <= 0: income covers "
                      f"spending, {NO_SHORTFALL_LABEL}")
    raw = buffer_left / gap
    if raw >= RUNWAY_CAP:
        value, status, label = RUNWAY_CAP, "capped", "120.0 months (cap)"
    else:
        value, status = round_half_up(raw), "finite"
        label = f"{value:.1f} months"
    return Runway(value, status, label, buffer_left, gap,
                  f"(B {B:,.2f} - one-off {one_off:,.2f}) / (S' {S_new:,.2f} - I' {I_new:,.2f}) "
                  f"= {buffer_left:,.2f} / {gap:,.2f} = {raw:.4f} -> {label}")


def judge_runway_all(shock: Shock, profiles: pd.DataFrame | None = None) -> pd.DataFrame:
    """Judge runway for every account at once (same rule and arithmetic as judge_runway).

    Returns columns I_new, S_new, one_off, buffer_left, gap, value (NaN = no shortfall), status.
    """
    p = get_profiles() if profiles is None else profiles
    I_new = shock.ei_pct * p["I"] if shock.ei_pct is not None else p["I"].copy()
    S_new = p["S"] + shock.bills_up_pct * p["H"] + shock.rent_up
    one_off = shock.repair_months * p["S"] + shock.one_off
    buffer_left = p["B"] - one_off
    gap = S_new - I_new
    raw = buffer_left / gap.where(gap > 0)
    rounded = raw.clip(upper=RUNWAY_CAP).map(lambda x: round_half_up(x) if pd.notna(x) else np.nan)
    zero, no_short = buffer_left <= 0, gap <= 0
    status = np.select([zero, no_short, raw >= RUNWAY_CAP], ["zero", "no_shortfall", "capped"],
                       default="finite")
    value = np.where(zero, 0.0, np.where(no_short, np.nan, rounded))
    return pd.DataFrame({"I_new": I_new, "S_new": S_new, "one_off": one_off,
                         "buffer_left": buffer_left, "gap": gap, "value": value,
                         "status": status}, index=p.index)


# ---------------------------------------------------------------- README twist cards

TWISTS: dict[str, Shock] = {
    # "This customer was laid off. EI pays 55% of their usual income for 6 months."
    "layoff_ei55": Shock(ei_pct=0.55),
    # "The furnace dies, and the repair costs a full month of their typical spending."
    "furnace_1mo": Shock(repair_months=1),
    # "They lose their job (EI at 55%) and their household bills go up 15% in the same month."
    "layoff_ei55_bills15": Shock(ei_pct=0.55, bills_up_pct=0.15),
}


def run(account_id, shock: Shock) -> dict:
    """One account + one shock -> profile, shocked inputs and judge runway (for the API)."""
    p = profile(account_id)
    s = apply_shock(p, shock)
    r = judge_runway(p.B, s.one_off, s.S_new, s.I_new)
    return {"profile": p.to_dict(), "shock": asdict(shock),
            "shocked": asdict(s), "judge_runway": r.to_dict()}
