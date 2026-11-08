# Task for Claude Code: account view + "faded" redesign + agent flow

Read CLAUDE.md, DECISIONS.md and docs/findings.md first. The live site (https://servaai.us) works and the
headline numbers must not change. Work on a new branch `feature/account-view`. Do NOT touch backend/.env.
Hard stop: if this is not tested and working by 10:45 AM, say so and leave `main` untouched.

SCOPE CHANGE (09:45): build sections 1, 2 and 4 only, then docs/prompt-chatbot.md. SKIP section 3 (redesign)
entirely: keep the current look. No design questions; start building.

## 1. What: a "My account" view (new API + new page section)

Show a customer what a bank app shows. Data already in data/: accounts.csv, loans.csv, transactions.csv
(about 1.06M rows; columns transaction_id, account_id, date, direction, operation, purpose, amount,
signed_amount, balance, partner_bank, partner_account), monthly_summary.csv, cards.csv, standing_orders.csv.

New endpoint `GET /api/accounts/{id}/statement?limit=50&before=YYYY-MM-DD`, returning:
- `balance`: current balance = `month_end_balance` of the account's last row in monthly_summary
  (rows inside one day are NOT in time order in transactions.csv, so do not trust "last row's balance").
- `loan`: null if none, else loan_id, amount, monthly_payment, duration_months, loan_start, status_meaning,
  `paid_to_date` = min(months elapsed since loan_start up to 2025-12, duration) x monthly_payment,
  `remaining` = max(amount - paid_to_date, 0), `next_payment` = monthly_payment. Label remaining as an estimate
  in the UI. Verify against the sum of `purpose == "loan payment"` transactions for account 63816 and say what you found.
- `transactions`: newest first, each with date, direction, operation, purpose (friendly label, blank = "Other"),
  amount, signed_amount, and the day's closing balance. Paginate with `before`.
- `cards`: card_type + issued date if the account has one (via dispositions.csv).
Performance: load transactions.csv ONCE at startup into a per-account structure with only the needed columns
(or cache a parquet like the other caches); never read the 100 MB CSV per request. The server has 4 GB RAM. Keep
startup under about 60 s. Return 404 for unknown accounts like the existing endpoints.

UI: a "My account" card on the Customer page: balance (big), loan card (progress bar paid vs remaining,
monthly payment), cards, and a transaction list with icons-free, readable rows (date, purpose, amount, in green/out
ink), a "Load more" button, and a filter for in/out. Mobile first.

## 2. What: the agent flow, end to end

The customer types what happened ("my hydro bill went up 20% and I lost my job"). Flow, on one screen:
1. Prompt box + visible **twist cards** (not tiny links): the 3 README twists plus 5 more from the agent test
   phrases (scam $1,500, rent up $300, bills up 10%, car repair $1,200, job loss then new job in month 4).
   Clicking a card fills the prompt and runs it.
2. Agent reads it (existing /api/parse-event) and shows the confirmation chip ("Job loss at 55% EI, bills +15%").
3. Outcome: judge runway vs realistic runway (existing RunwayPair) plus the plain-language explanation
   (/api/explain; numbers only from the engine).
4. Two clear next steps under the outcome: "See my 3-month forecast" (existing ForecastChart, /api/forecast)
   and "See how everyone compares" (Portfolio page). If `VITE_POWERBI_URL` is set, the Portfolio page shows the
   published Power BI report in an iframe above the native charts; if it is not set, show only the native charts
   (do not show a broken frame).
Do not change any engine number. All numbers shown must come from the API.

## 3. (SKIPPED) Redesign: do not change the visual style.

## 4. Rules and checks (do all, show the output)
- Backend: add tests in backend/tests/ for the statement endpoint (account with a loan, account without a loan,
  unknown account, pagination, balance equals last month_end_balance). All 126 existing tests must still pass.
- Frontend: `npm run build` passes with no errors. Open the app at 390 px and 1280 px wide and check it.
- Smoke test locally: account 63816 twist 3 must still show Judge 3.1, Realistic 1.9; /api/health ok.
- Commit in small steps on the branch. Do not commit data/, .env, deploy/.vultr_deploy_key or any key.
- When done, tell me exactly what changed and what you could not verify. Do not deploy; I will run
  deploy\update_server.ps1 myself after I look at it.
