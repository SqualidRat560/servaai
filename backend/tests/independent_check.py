"""Independent recomputation of the judge numbers, written from data/README.md.

Deliberately uses only the standard library (csv, statistics, decimal) and does NOT
import backend.engine, pandas or numpy, so a shared bug cannot hide in both.

    python -m backend.tests.independent_check                 # summary for all accounts
    python -m backend.tests.independent_check --account 63816 # one account
"""
from __future__ import annotations

import argparse
import csv
import statistics
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"

TWIST_NAMES = ("layoff_ei55", "furnace_1mo", "layoff_ei55_bills15")


def _load():
    by_account: dict[int, list[dict]] = {}
    with open(DATA / "monthly_summary.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_account.setdefault(int(row["account_id"]), []).append(row)
    for rows in by_account.values():
        rows.sort(key=lambda r: r["month"])  # 'YYYY-MM' sorts in time order
    loans: dict[int, dict] = {}
    with open(DATA / "loans.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            loans[int(row["account_id"])] = row
    return by_account, loans


def readme_runway(buffer: float, one_off_costs: float, spending_after: float,
                  income_after: float) -> float | None:
    """README rule. Returns months (1 decimal) or None for 'no shortfall (120+)'."""
    buffer_left = buffer - one_off_costs
    gap = spending_after - income_after
    if buffer_left <= 0:
        return 0.0
    if gap <= 0:
        return None
    months = min(buffer_left / gap, 120)
    return float(Decimal(str(months)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def account_numbers(rows: list[dict], loan: dict | None) -> dict:
    col = lambda name: [float(r[name]) for r in rows]  # noqa: E731
    money_in, money_out = col("money_in"), col("money_out")
    bills, insurance, loan_pay = col("household_bills"), col("insurance"), col("loan_payments")
    I = statistics.median(money_in)
    S = statistics.median(money_out)
    H = statistics.median(bills)
    F = statistics.median([b + i + l for b, i, l in zip(bills, insurance, loan_pay)])
    B = statistics.fmean(float(r["avg_daily_balance"]) for r in rows[-6:])
    P = float(loan["monthly_payment"]) if loan and loan["status"] in ("C", "D") else 0.0
    return {
        "I": I, "F": F, "S": S, "B": B, "H": H, "P": P,
        "n_months": len(rows), "last_month": rows[-1]["month"],
        "layoff_ei55": readme_runway(B, 0.0, S, 0.55 * I),
        "furnace_1mo": readme_runway(B, 1 * S, S, I),
        "layoff_ei55_bills15": readme_runway(B, 0.0, S + 0.15 * H, 0.55 * I),
    }


def compute_all() -> dict[int, dict]:
    by_account, loans = _load()
    return {aid: account_numbers(rows, loans.get(aid)) for aid, rows in sorted(by_account.items())}


def _fmt(v) -> str:
    if v is None:
        return "no shortfall (120+)"
    return f"{v:,.2f}" if isinstance(v, float) else str(v)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--account", type=int, help="print one account's numbers")
    args = ap.parse_args()
    allv = compute_all()
    if args.account is not None:
        if args.account not in allv:
            raise SystemExit(f"unknown account_id {args.account}")
        for k, v in allv[args.account].items():
            print(f"{k:>20}: {_fmt(v)}")
        return
    vals = list(allv.values())
    print(f"accounts: {len(vals)}")
    print(f"B <= 0: {sum(v['B'] <= 0 for v in vals)} | I == 0: {sum(v['I'] == 0 for v in vals)} | "
          f"S == 0: {sum(v['S'] == 0 for v in vals)} | ends before 2025-12: "
          f"{sum(v['last_month'] < '2025-12' for v in vals)}")
    for t in TWIST_NAMES:
        r = [v[t] for v in vals]
        print(f"{t}: zero={sum(x == 0.0 for x in r)} no_shortfall={sum(x is None for x in r)} "
              f"cap120={sum(x == 120.0 for x in r)}")


if __name__ == "__main__":
    main()
