"""Export the 3 answer-key accounts' raw rows for a teammate's hand spreadsheet.

    python -m backend.tests.make_answer_key

Writes docs/answer_key/<id>_monthly.csv (all monthly_summary rows, sorted by month) and
docs/answer_key/<id>_loan.csv (its loans.csv row, if any). The folder is git-ignored
because it holds raw data rows. Uses only the standard library and does not compute
anything, so the hand check stays independent of the engine.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "docs" / "answer_key"
KEY = Path(__file__).resolve().parent / "answer_key.json"


def main() -> None:
    accounts = json.loads(KEY.read_text(encoding="utf-8"))["accounts"]
    ids = {int(a) for a in accounts}
    OUT.mkdir(parents=True, exist_ok=True)

    with open(DATA / "monthly_summary.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header, rows = reader.fieldnames, [r for r in reader if int(r["account_id"]) in ids]
    with open(DATA / "loans.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        loan_header, loans = reader.fieldnames, [r for r in reader if int(r["account_id"]) in ids]

    for aid in sorted(ids):
        mine = sorted((r for r in rows if int(r["account_id"]) == aid), key=lambda r: r["month"])
        with open(OUT / f"{aid}_monthly.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            w.writerows(mine)
        loan = [r for r in loans if int(r["account_id"]) == aid]
        if loan:
            with open(OUT / f"{aid}_loan.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=loan_header)
                w.writeheader()
                w.writerows(loan)
        print(f"{aid}: {len(mine)} monthly rows, loan: {loan[0]['status'] if loan else 'none'} "
              f"-> {accounts[str(aid)]['role']}")
    print(f"Wrote {OUT}. Compute I, F, S, B, H, P and the 3 README twists by hand, then fill "
          f"the 'hand' values in {KEY.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
