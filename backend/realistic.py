"""ServaAI realistic runway (DECISIONS.md Topic 7).

The judge formula assumes EI pays forever at p * I. In reality EI regular benefits stop
(default here: after 6 months) and are capped at $729/week. This module simulates the
balance month by month instead.

Caveat (shown in the app): money_in includes transfers and pensions, so EI computed from I
is an upper bound and the real runway may be even shorter.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from backend import engine

EI_WEEKLY_MAX = 729.0
EI_MONTHLY_MAX = EI_WEEKLY_MAX * 52 / 12  # 3,159.00 dollars per month
DEFAULT_EI_MONTHS = 6
HORIZON = 120


@dataclass(frozen=True)
class RealisticRunway:
    value: float | None  # months, 1 decimal; None = "no shortfall (120+)"
    status: str          # "zero" | "no_shortfall" | "finite" | "capped"
    label: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def income_in_month(p: engine.Profile, shock: engine.Shock, month: int, ei_months: int | None,
                    cap: bool, reemploy_month: int | None) -> float:
    """Income in simulated month `month` (1-based)."""
    if shock.ei_pct is None:
        return p.I
    if reemploy_month is not None and month >= reemploy_month:
        return p.I
    if ei_months is not None and month > ei_months:
        return 0.0
    ei = shock.ei_pct * p.I
    return min(ei, EI_MONTHLY_MAX) if cap else ei


def realistic_runway(p: engine.Profile, shock: engine.Shock, ei_months: int | None = DEFAULT_EI_MONTHS,
                     cap: bool = True, reemploy_month: int | None = None) -> RealisticRunway:
    s = engine.apply_shock(p, shock)
    balance = p.B - s.one_off
    if balance <= 0:
        return RealisticRunway(0.0, "zero", "0.0 months",
                               "the buffer is used up before the shock even starts")
    why = _reason(p, shock, ei_months, cap, reemploy_month)
    for month in range(1, HORIZON + 1):
        income = income_in_month(p, shock, month, ei_months, cap, reemploy_month)
        burn = s.S_new - income
        if burn > 0 and balance - burn <= 0:
            value = engine.round_half_up(min((month - 1) + balance / burn, HORIZON))
            return RealisticRunway(value, "finite", f"{value:.1f} months", why)
        balance -= burn
    long_run_burn = s.S_new - income_in_month(p, shock, HORIZON + 1, ei_months, cap, reemploy_month)
    if long_run_burn <= 0:
        return RealisticRunway(None, "no_shortfall", engine.NO_SHORTFALL_LABEL, why)
    return RealisticRunway(engine.RUNWAY_CAP, "capped", "120.0 months (cap)", why)


def _reason(p, shock, ei_months, cap, reemploy_month) -> str:
    if shock.ei_pct is None:
        return "no job loss: income stays at I, same as the judge formula"
    ei = shock.ei_pct * p.I
    parts = [f"EI {shock.ei_pct:.0%} of I = {ei:,.2f}/month"]
    if cap and ei > EI_MONTHLY_MAX:
        parts.append(f"capped at {EI_MONTHLY_MAX:,.2f}/month ($729/week)")
    parts.append(f"for {ei_months} months, then $0" if ei_months is not None else "paid forever")
    if reemploy_month is not None:
        parts.append(f"back to full income I from month {reemploy_month}")
    return ", ".join(parts)
