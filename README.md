# ServaAI

Forecasts a customer's next 3 months of balance, updates instantly when life happens (a layoff, a
rent hike, a scam), and builds a Tangerine plan. Sheridan Datathon 2026, Tangerine track.

**Finding:** for 32.8% of customers (95% CI 31.4% to 34.2%), the standard runway formula overstates
how long savings last after a job loss by more than six months. Details: [docs/findings.md](docs/findings.md).

Live: https://servaai.us

## What's inside
| Path | What it does |
|---|---|
| `backend/engine.py` | The judges' definitions (I, F, S, B, H, P, shocks, runway), matched exactly |
| `backend/realistic.py` | Realistic runway: EI ends after 6 months, capped at $729/week |
| `backend/features.py`, `backend/forecast.py` | 3-month balance forecast ladder and backtest ([docs/backtest.md](docs/backtest.md)) |
| `backend/plan.py` | Emergency fund, Automatic Savings Program, backup plan |
| `backend/agent.py` | Gemini event agent with fallbacks; explanations checked against engine numbers |
| `backend/population.py` | Portfolio finding, segments, Power BI exports |
| `backend/app.py` | FastAPI API, also serves the built frontend |
| `backend/tests/` | 94 tests, including an independent check on all 4,500 accounts |
| `frontend/` | React + Tailwind + Recharts + react-three-fiber |
| `deploy/` | Vultr + nginx + HTTPS setup ([deploy/RUNBOOK.md](deploy/RUNBOOK.md)) |

## Run it locally (Windows, from the repo folder)
Put the track data in `data/` and, for Gemini, a `backend/.env` with `GEMINI_API_KEY=...` and
`GEMINI_MODEL=gemini-3.6-flash` (without it, the built-in parser is used).

```bash
py -3.14 -m venv .venv
```
```bash
.venv/Scripts/python -m pip install -r backend/requirements.txt
```
```bash
npm --prefix frontend ci
```
```bash
npm --prefix frontend run build
```
```bash
.venv/Scripts/python -m uvicorn backend.app:app --port 8000
```
Open http://localhost:8000. The first start trains the forecast once (about 20 seconds).

Tests and analysis:
```bash
cd backend && ../.venv/Scripts/python -m pytest -q
```
```bash
.venv/Scripts/python -m backend.forecast
```
```bash
.venv/Scripts/python -m backend.population
```

## How the numbers are made
- **Judge formula**, from `monthly_summary.csv`: I and S are medians of money in and out, B is the
  mean daily balance over the account's last 6 months, runway = (B − one-off costs) ÷ (spending
  after the shock − income after it), capped at 120 months, rounded to 1 decimal. Checked against
  an independent standard-library script on all 4,500 accounts (100% match).
- **Realistic runway**: the same customer, simulated month by month with EI that stops after 6 months
  and is capped at $729/week. Caveat: money_in includes transfers and pensions, so EI here is an
  upper bound.
- **Gemini** only turns text into events and rephrases results; it never produces a number.

## Sources and credits
- PKDD'99 Discovery Challenge Financial dataset (real anonymized bank data), CTU Prague Relational
  Dataset Repository: https://relational.fel.cvut.cz/dataset/Financial
- Government of Canada, Employment Insurance regular benefits:
  https://www.canada.ca/en/services/benefits/ei/ei-regular-benefit.html
