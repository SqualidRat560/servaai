# ServaAI (Sheridan Datathon 2026, Tangerine track)

## Goal
Any account_id + any life event -> judge runway (exact), realistic runway, 3-month balance
forecast, and a Tangerine plan. Gemini parses events; the Python engine makes every number.
3D web UI at servaai.us; Power BI for the portfolio story.

## Decisions (What / Why / Where / How cards live in DECISIONS.md)
- One driver, one Claude Code session; team is new to React, so Claude writes the frontend.
- Stack: FastAPI backend + React/Vite + react-three-fiber; Tailwind (#F28500 on navy); Recharts.
- 3D build order: hero coin scene -> galaxy -> ribbon -> logo. Cut order: logo -> ribbon -> galaxy -> hero.
  Budget: <3 s load, 60 fps, lazy-loaded, 2D toggle, reduced-motion respected.
- Engine verified by 3 hand-checked accounts + 100% match vs independent_check.py.
- Forecast: median net flow + 0.5 x damped 6-month trend; P10-P90 band from own residuals;
  backtest vs flat baseline in docs/backtest.md, reported honestly.
- Agent: Gemini Flash-tier, JSON schema + pydantic; always confirm before applying; optional
  "Explain" summary using only engine numbers; regex fallback + sliders.
- Realistic runway: EI 6 months, cap $3,159/mo on (toggle), optional re-employment;
  money_in caveat stated as an upper bound.
- Plan: 3- and 6-month targets; ASP = 50% of surplus weekly; cut card, cash, transfers_out_other
  ("if discretionary") and bank_fees largest-first in 10% steps; never cut fixed costs.
  Tools: ASP + Goals, Money Rules, Orange Alerts, Left to Spend + Insights.
- Portfolio: 4 segments; headline "formula overstates runway >6 months for about 1 in 3", bootstrap CI.
  Power BI pages: headline, segments by region/age, shock comparison; screenshots in app + Devpost.
- Deploy: Vultr + Docker Compose + nginx + Let's Encrypt, Sunday 7-9 AM; A record set early;
  local laptop backup.
- Demo: presenter != driver; freeze 9 AM, submit 11:30 AM; 2-min screen recording. No ML layer.

## Judge definitions (match exactly)
From data/monthly_summary.csv sorted by account_id, month:
- I = median(money_in); S = median(money_out); H = median(household_bills)
- F = median(household_bills + insurance + loan_payments): display only
- B = mean(avg_daily_balance) over the account's LAST 6 rows by month
- P = loans.monthly_payment if loan status is C or D, else 0
- Shocks: EI at p -> I' = p*I. Bills up q -> S' = S + q*H. Rent up r -> S' = S + r.
  Repair k months -> one_off = k*S. Repair or scam d dollars -> one_off = d.
- buffer_left = B - one_off; gap = S' - I'
  if buffer_left <= 0: 0; elif gap <= 0: "no shortfall (120+)"; else min(buffer_left/gap, 120),
  rounded to 1 decimal. S already includes loan payments: never add P again.

## Hard rules
- IMPORTANT: numbers only from backend/engine + tests; the LLM never invents numbers.
- Judge number first, realistic beside it, both labelled.
- 2D core works with 3D off; cut 3D first if behind.
- Gemini key only in backend .env, never in frontend or git.
- Run pytest after every backend change and show the output.
- Every phase: plan (What/Why/Where/How) -> approval -> build -> evidence -> CHECK -> "go".

## Commands
cd backend && pytest -q
cd backend && uvicorn app:app --reload
cd frontend && npm run dev
python -m backend.population
