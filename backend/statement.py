"""'My account' view: balance, loan, cards and a paginated transaction list.

transactions.csv (about 1.06M rows) is read once, cached to backend/cache/transactions.parquet,
and kept in memory sorted by account (newest first) with a per-account row range, so a
request never touches the CSV.

Rows inside one day are not in time order in transactions.csv, so a row's `balance` is not
trusted as the day's close. The day's closing balance is rebuilt backwards from the
account's current balance (month_end_balance of its last month): close(day) = current
balance - sum of all signed amounts after that day. Because the CSV's amounts are rounded, that
estimate drifts by cents, so each day is then snapped to the raw `balance` on that day closest
to the estimate (the last transaction of the day), so every close shown is a real data value.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from backend import engine

TX_CACHE = engine.CACHE_DIR / "transactions.parquet"
DATA_END = pd.Period("2025-12", freq="M")
PURPOSE_LABEL = {
    "household bills": "Household bills", "insurance": "Insurance", "loan payment": "Loan payment",
    "pension": "Pension", "interest credited": "Interest", "statement fee": "Statement fee",
    "penalty interest (negative balance)": "Penalty interest",
}
COLS = ["transaction_id", "account_id", "date", "direction", "operation", "purpose", "amount", "signed_amount", "balance"]


def _load_transactions() -> pd.DataFrame:
    src = engine.DATA_DIR / "transactions.csv"
    if TX_CACHE.exists() and TX_CACHE.stat().st_mtime >= src.stat().st_mtime:
        try:
            cached = pd.read_parquet(TX_CACHE)
            if list(cached.columns) == COLS:
                return cached
        except Exception:
            pass
    tx = pd.read_csv(src, usecols=COLS, dtype={"purpose": "string", "operation": "string", "direction": "string"})
    tx["purpose"] = tx["purpose"].fillna("")
    try:
        engine.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tx.to_parquet(TX_CACHE)
    except Exception:
        pass
    return tx


@lru_cache(maxsize=1)
def store() -> dict:
    """Transactions sorted by account then newest first, with day closes and row ranges."""
    tx = _load_transactions()
    tx = tx.sort_values(["account_id", "date", "transaction_id"], ascending=[True, False, False],
                        kind="mergesort").reset_index(drop=True)
    prof = engine.get_profiles()
    monthly = engine.load_monthly_cached()
    current = monthly.groupby("account_id")["month_end_balance"].last()
    # day net flows, newest first per account; close(day) = current - sum of later days' nets
    day = tx.groupby(["account_id", "date"], sort=False)["signed_amount"].sum().reset_index()
    day["later"] = day.groupby("account_id")["signed_amount"].cumsum() - day["signed_amount"]
    day["approx"] = day["account_id"].map(current) - day["later"]
    tx = tx.merge(day[["account_id", "date", "approx"]], on=["account_id", "date"], how="left")
    gap = (tx["balance"] - tx["approx"]).abs()
    best = gap.groupby([tx["account_id"], tx["date"]]).idxmin()
    snapped = pd.Series(tx.loc[best.to_numpy(), "balance"].to_numpy(), index=best.index, name="close")
    tx = tx.join(snapped, on=["account_id", "date"]).drop(columns=["approx"])
    acct = tx["account_id"].to_numpy()
    starts = np.flatnonzero(np.r_[True, acct[1:] != acct[:-1]])
    ends = np.r_[starts[1:], len(acct)]
    ranges = {int(acct[s]): (int(s), int(e)) for s, e in zip(starts, ends)}
    return {"tx": tx, "ranges": ranges, "current": current, "last_month": monthly.groupby("account_id")["month"].last(),
            "accounts": set(prof.index)}


@lru_cache(maxsize=1)
def _side_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    d = engine.DATA_DIR
    loans = pd.read_csv(d / "loans.csv").set_index("account_id")
    disp = pd.read_csv(d / "dispositions.csv")
    cards = pd.read_csv(d / "cards.csv").merge(disp[["disposition_id", "account_id", "type"]], on="disposition_id")
    return loans, cards


def loan_summary(account_id: int) -> dict | None:
    loans, _ = _side_tables()
    if account_id not in loans.index:
        return None
    L = loans.loc[account_id]
    start = pd.Period(str(L["loan_start"])[:7], freq="M")
    elapsed = max(min((DATA_END - start).n, int(L["duration_months"])), 0)
    paid = elapsed * float(L["monthly_payment"])
    return {
        "loan_id": int(L["loan_id"]), "amount": float(L["amount"]),
        "monthly_payment": float(L["monthly_payment"]), "duration_months": int(L["duration_months"]),
        "loan_start": str(L["loan_start"]), "status": str(L["status"]), "status_meaning": str(L["status_meaning"]),
        "months_paid": elapsed, "paid_to_date": paid, "remaining": max(float(L["amount"]) - paid, 0.0),
        "next_payment": float(L["monthly_payment"]),
        "estimate_note": "Paid and remaining are estimates: months since the loan started (to Dec 2025) x the monthly payment.",
    }


def statement(account_id, limit: int = 50, before: str | None = None, direction: str | None = None) -> dict:
    p = engine.profile(account_id)  # raises UnknownAccount
    aid = p.account_id
    s = store()
    limit = max(1, min(int(limit), 500))
    rows = s["tx"].iloc[slice(*s["ranges"].get(aid, (0, 0)))]
    if direction in ("in", "out"):
        rows = rows[rows["signed_amount"] > 0] if direction == "in" else rows[rows["signed_amount"] < 0]
    if before:
        rows = rows[rows["date"] < before]
    page = rows.iloc[:limit]
    if len(page) == limit and len(rows) > limit:  # never split a day across pages
        last_day = page["date"].iloc[-1]
        page = rows[rows["date"] >= last_day]
    has_more = len(rows) > len(page)
    _, cards = _side_tables()
    mine = cards[cards["account_id"] == aid]
    return {
        "account_id": aid,
        "balance": float(s["current"].get(aid, np.nan)),
        "balance_as_of": str(s["last_month"].get(aid, "")),
        "loan": loan_summary(aid),
        "cards": [{"card_type": str(c.card_type), "issued": str(c.issued)[:10], "holder": str(c.type)}
                  for c in mine.itertuples()],
        "transactions": [
            {"id": int(r.transaction_id), "date": str(r.date), "direction": "in" if r.signed_amount > 0 else "out",
             "operation": str(r.operation), "purpose": PURPOSE_LABEL.get(r.purpose, "Other"),
             "amount": float(r.amount), "signed_amount": float(r.signed_amount), "day_close_balance": round(float(r.close), 2)}
            for r in page.itertuples()],
        "next_before": str(page["date"].iloc[-1]) if has_more and len(page) else None,
        "has_more": has_more,
    }
