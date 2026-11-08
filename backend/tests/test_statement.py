"""'My account' statement endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend import engine
from backend.app import app

client = TestClient(app)


def _get(aid, **params):
    return client.get(f"/api/accounts/{aid}/statement", params=params)


def test_account_with_loan_63816():
    d = _get(63816, limit=10).json()
    loan = d["loan"]
    assert loan["monthly_payment"] == 3153.27 and loan["months_paid"] == 58
    assert abs(loan["paid_to_date"] - 58 * 3153.27) < 0.01
    assert abs(loan["remaining"] - (189196.2 - 58 * 3153.27)) < 0.01
    assert loan["next_payment"] == 3153.27


def test_account_without_loan():
    d = _get(99477).json()
    assert d["loan"] is None and len(d["transactions"]) > 0


def test_unknown_account_is_404():
    assert _get(1).status_code == 404


def test_balance_equals_last_month_end_balance():
    m = engine.load_monthly_cached()
    for aid in (63816, 32078, 99477):
        last = m[m["account_id"] == aid]["month_end_balance"].iloc[-1]
        d = _get(aid, limit=5).json()
        assert d["balance"] == last
        assert d["transactions"][0]["day_close_balance"] == round(last, 2)


def test_newest_first_and_pagination_has_no_gaps_or_overlaps():
    first = _get(63816, limit=20).json()
    dates = [t["date"] for t in first["transactions"]]
    assert dates == sorted(dates, reverse=True) and first["has_more"]
    second = _get(63816, limit=20, before=first["next_before"]).json()
    ids1 = {t["id"] for t in first["transactions"]}
    ids2 = {t["id"] for t in second["transactions"]}
    assert not ids1 & ids2
    assert max(t["date"] for t in second["transactions"]) < min(dates)
    # walking every page returns every transaction exactly once
    seen, before = [], None
    while True:
        page = _get(63816, limit=200, **({"before": before} if before else {})).json()
        seen += [t["id"] for t in page["transactions"]]
        if not page["has_more"]:
            break
        before = page["next_before"]
    import pandas as pd
    raw = pd.read_csv(engine.DATA_DIR / "transactions.csv", usecols=["account_id"])
    assert len(seen) == len(set(seen)) == int((raw["account_id"] == 63816).sum())


def test_direction_filter_and_labels():
    d = _get(63816, limit=30, direction="in").json()
    assert d["transactions"] and all(t["signed_amount"] > 0 and t["direction"] == "in" for t in d["transactions"])
    labels = {t["purpose"] for t in _get(63816, limit=200).json()["transactions"]}
    assert "Loan payment" in labels and "" not in labels


def test_bad_params_are_422():
    assert _get(63816, before="June").status_code == 422
    assert _get(63816, direction="sideways").status_code == 422
