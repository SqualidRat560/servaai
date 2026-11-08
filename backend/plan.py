"""Tangerine plan builder (Topic 8): goal plan + backup plan from the customer's own numbers."""
from __future__ import annotations

from backend import engine, realistic

FLEXIBLE = {
    "card_withdrawals": "card spending",
    "cash_withdrawals_genuine": "cash withdrawals",
    "transfers_out_other": "other transfers out (if discretionary)",
    "bank_fees": "bank fees",
}
FIXED = ("household_bills", "insurance", "loan_payments")  # never cut
STEP = 0.10      # cut 10% of a category's median per step
MAX_CUT = 0.50   # never cut a category by more than half
ASP_SHARE = 0.5  # Automatic Savings Program = 50% of monthly surplus
WEEKS_PER_MONTH = 52 / 12
BACKUP_TARGET = 3.0  # months of realistic runway the backup plan aims for


def flexible_medians(account_id: int) -> dict[str, float]:
    m = engine.load_monthly_cached()
    rows = m[m["account_id"] == account_id]
    return {c: float(rows[c].median()) for c in FLEXIBLE}


def _runway_value(r) -> float:
    return float("inf") if r.value is None else r.value


def build_plan(account_id, shock: engine.Shock | None = None, cap: bool = True,
               reemploy_month: int | None = None) -> dict:
    p = engine.profile(account_id)
    shock = shock or engine.Shock()
    surplus = p.I - p.S
    asp_month = ASP_SHARE * max(surplus, 0.0)
    target3, target6 = 3 * p.S, 6 * p.S
    goal = {
        "surplus_monthly": surplus,
        "target_3_months": target3, "target_6_months": target6,
        "progress_3": (p.B / target3) if target3 > 0 else None,
        "progress_6": (p.B / target6) if target6 > 0 else None,
        "asp_weekly": asp_month / WEEKS_PER_MONTH,
        "months_to_3": (max(target3 - p.B, 0.0) / asp_month) if asp_month > 0 else None,
        "orange_alert_below": p.S,  # alert when the balance drops below one month of spending
    }

    before = realistic.realistic_runway(p, shock, cap=cap, reemploy_month=reemploy_month)
    med = flexible_medians(p.account_id)
    cut = {c: 0.0 for c in med}
    current = before
    steps = 0
    while _runway_value(current) < BACKUP_TARGET:
        room = {c: med[c] * MAX_CUT - cut[c] for c in med if med[c] > 0 and cut[c] < med[c] * MAX_CUT - 1e-9}
        if not room:
            break
        c = max(room, key=lambda k: med[k] - cut[k])  # currently largest remaining category
        cut[c] += min(med[c] * STEP, room[c])
        steps += 1
        current = _with_savings(p, shock, sum(cut.values()), cap, reemploy_month)
    saved = sum(cut.values())
    backup = {
        "runway_before": before.to_dict(), "runway_after": current.to_dict(),
        "monthly_savings": saved, "steps": steps, "target_months": BACKUP_TARGET,
        "reached_target": _runway_value(current) >= BACKUP_TARGET,
        "cuts": [{"category": c, "label": FLEXIBLE[c], "median": med[c], "cut": cut[c],
                  "cut_pct": (cut[c] / med[c]) if med[c] > 0 else 0.0}
                 for c in sorted(cut, key=lambda k: -cut[k]) if cut[c] > 0],
    }
    tools = [
        {"tool": "Automatic Savings Program + Goals",
         "action": f"Auto-save ${goal['asp_weekly']:,.2f} per week into an emergency-fund Goal "
                   f"(3-month target ${target3:,.2f})." if asp_month > 0 else
                   "No monthly surplus yet: start the Goal with any amount once the backup cuts free up money."},
        {"tool": "Money Rules", "action": "Round up every purchase and save the change into the same Goal."},
        {"tool": "Orange Alerts",
         "action": f"Alert when the balance drops below ${p.S:,.2f} (one month of typical spending)."},
        {"tool": "Left to Spend + Insights",
         "action": (f"Track the backup cuts: ${saved:,.2f} less per month across "
                    f"{', '.join(FLEXIBLE[x['category']] for x in backup['cuts'])}.") if saved > 0 else
                   "Watch flexible spending each month; no cuts needed under this shock."},
    ]
    return {"account_id": p.account_id, "goal": goal, "backup": backup, "tools": tools}


def _with_savings(p: engine.Profile, shock: engine.Shock, saved: float, cap: bool,
                  reemploy_month: int | None) -> realistic.RealisticRunway:
    """Realistic runway when monthly spending is lower by `saved` (cuts apply to S')."""
    lower = engine.Profile(**{**p.to_dict(), "S": p.S - saved})
    # bills/rent shocks are absolute or based on H, so lowering S only removes the cut amount;
    # a repair of k months is still k months of the ORIGINAL spending.
    s = engine.Shock(ei_pct=shock.ei_pct, bills_up_pct=shock.bills_up_pct, rent_up=shock.rent_up,
                     repair_months=0.0, one_off=shock.one_off + shock.repair_months * p.S)
    return realistic.realistic_runway(lower, s, cap=cap, reemploy_month=reemploy_month)
