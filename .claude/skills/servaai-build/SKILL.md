---
name: servaai-build
description: Interview-first build of ServaAI (Sheridan Datathon 2026, Tangerine track) using the What/Why/Where/How method. Asks the team about every feature and algorithm, records decisions, then builds a Python engine, Gemini event agent, 3-month forecast, 3D web UI and Power BI dashboards phase by phase. Use when starting or resuming the ServaAI project.
---

# ServaAI build partner: What / Why / Where / How

You help a team of 4 students build **ServaAI** at Sheridan Datathon 2026 (Tangerine track).
Hacking ends **Sunday Nov 8, 12:00 PM**; Devpost closes at noon; demos 1:00-2:30 PM.
The USER decides. You propose, ask, record, then build exactly what was decided.

## The method: every feature is a What / Why / Where / How card

Before you ask about or build any feature, present it as a card:

- **WHAT**: one sentence on what it does, and what the user or judge sees on screen.
- **WHY**: which judging criterion or prize it serves (see "Why map" below), and what breaks
  or is lost without it.
- **WHERE**: where it lives: data files and columns it reads, backend module and function, API
  endpoint, frontend page and component, and the moment in the demo it appears.
- **HOW**: the algorithm or implementation, step by step, the libraries used, and the test
  that proves it works.

Then ask the user the open choices for that card with the AskUserQuestion tool. After they
answer, write the FINAL card into `DECISIONS.md` under the topic heading and show it.
When you present a plan in plan mode, structure it as What / Why / Where / How too.

### Why map (use these names in every WHY)
- Tangerine live twist: judge picks an account_id + shock card; runway must match theirs.
- Discovery (35%), Data Use (25%), Communication (25%), Impact (15%).
- Best Data Visualization & Storytelling prize.
- MLH Best Use of Gemini API: requires a real Gemini API feature + the Gemini Project Number.
- MLH Best Use of Vultr: app deployed on Vultr.
- MLH Best Domain (GoDaddy Registry): servaai.us must point at the live app.
- Devpost promise: the pitch says "forecasts a customer's next 3 months of balance, updates
  instantly when life happens (a layoff, a rent hike, a scam), and builds a Tangerine plan".
  Anything promised there must work in the demo.

## How to run this skill

1. Read `DECISIONS.md` if it exists. Tell the user in one line which topics are done, then
   continue from the first open topic or the next build phase. If missing, start at Topic 1.
2. One topic at a time. For each topic: show the card(s) with your recommendation, then ask
   1 to 4 questions with AskUserQuestion. Each question names what is being decided and has
   2 to 4 options. Put the recommended option FIRST, labelled "(Recommended)". If
   AskUserQuestion is unavailable, ask a numbered list in plain text and wait.
3. If an answer breaks a Fixed fact, say why in one sentence and ask again.
4. After Topics 1-12, write `CLAUDE.md` from the template at the bottom and ask the user to
   approve it. No project code before approval.
5. Build phase by phase. Each phase: plan mode, plan as What/Why/Where/How, wait for approval,
   build, show evidence (test output, numbers, screenshots), ask the CHECK questions, wait for
   "go". Never skip a gate.
6. Keep messages short. The clock matters more than prose.

## Fixed facts (not up for a vote)

Judge definitions, from `data/monthly_summary.csv` sorted by account_id then month:
- I = median(money_in); S = median(money_out); H = median(household_bills)
- F = median(household_bills + insurance + loan_payments): display only
- B = mean(avg_daily_balance) over the account's LAST 6 rows by month
- P = loans.monthly_payment if loan status is C or D, else 0
- Shocks: EI at p -> I' = p*I. Bills up q -> S' = S + q*H. Rent up r dollars -> S' = S + r.
  Repair of k months -> one_off = k*S. Repair or scam of d dollars -> one_off = d.
- buffer_left = B - one_off; gap = S' - I'
  if buffer_left <= 0: 0; elif gap <= 0: "no shortfall (120+)"; else min(buffer_left/gap, 120),
  rounded to 1 decimal. S already includes loan payments: never add P again.
- Every number shown anywhere comes from the tested Python engine. The LLM never produces numbers.
- The judges' number is always shown first and labelled; ServaAI's realistic number beside it.

Data and context:
- 4,500 accounts, 185,326 account-months (2020-01..2025-12). Real anonymized PKDD'99 bank
  data, dates shifted, amounts in CAD. No merchant, fraud or wage fields.
- Edge cases: 23 accounts B <= 0, 14 with I = 0, 77 with S = 0, about 76 end before 2025-12.
- EI 2026: 55% of insurable earnings, max 729 dollars per week (about 3,159 per month).
- First-pass finding to verify: under EI 55%, the judge formula puts 35.5% of customers under
  6 months; realistic (EI ends at 6 months, capped) puts 51.3%; the formula overstates runway
  by more than 6 months for 32.9%. Caveat: money_in includes transfers and pensions.
- Team limit 4. Devpost project "servaai" exists with tracks: Tangerine, Data Viz, Gemini,
  Vultr, GoDaddy. Domain servaai.us is registered (currently parked on Articulation).

Non-negotiable safety rules for the build:
- The 2D core (account lookup, numbers, shock controls, trajectory chart, plan) must work
  BEFORE any 3D work starts, and the app must still work with 3D switched off.
- 3D is the first thing cut if a gate is missed.
- Gemini API key lives only in a server-side `.env`, never in frontend code or git.

## Interview topics

Text in [brackets] is guidance for you, not shown to the user.

### Topic 1: Team, skills, setup
Cards: none. Questions:
1. Who drives Claude Code, and how many sessions in parallel?
   "One driver, one session (Recommended)" / "Two drivers: backend and frontend sessions" / "Other"
2. Team experience with React or JavaScript?
   "At least one person is comfortable (Recommended)" / "Beginners" / "None"
   [If none: recommend Topic 2 option "Streamlit + one embedded 3D component" and say why.]
3. Python and Node installed? "Both" / "Python only" / "Check for me"
4. Data in `data/` with the track README? "Yes" / "Copy it for me" / "Not yet"

### Topic 2: Architecture
Card: Web app architecture.
- WHAT: a website at servaai.us where a judge types an account_id and an event and sees numbers,
  a 3-month trajectory and a plan.
- WHY: Tangerine live twist; Vultr; GoDaddy; Communication.
- WHERE: `backend/` (FastAPI + engine), `frontend/` (React + Vite + Three.js), `powerbi/`.
- HOW: FastAPI serves JSON from the engine; React calls it; Three.js via react-three-fiber.
Questions:
1. Stack? "FastAPI backend + React/Vite + react-three-fiber (Recommended)" /
   "Streamlit app + one embedded 3D component (simpler, less 3D)" / "Next.js full-stack"
2. Styling? "Tailwind, Tangerine orange #F28500 accent, dark navy background (Recommended)" /
   "Plain CSS" / "A component library (shadcn/ui)"
3. Charts in 2D? "Recharts (Recommended)" / "Plotly" / "ECharts"

### Topic 3: 3D UI scope
Card: 3D layer.
- WHAT: a 3D scene that makes the finding visible at a glance.
- WHY: Best Data Visualization & Storytelling; Communication; first impression in a 1-minute pitch.
- WHERE: `frontend/src/three/`; shown on the landing page and the customer page.
- HOW: react-three-fiber + drei; InstancedMesh for many points; orbit controls; a 2D toggle.
Questions:
1. How much 3D? "One hero 3D scene + 2D dashboards (Recommended)" /
   "3D on every page" / "3D charts only"
2. Which 3D scene(s)? (multiSelect)
   "Portfolio galaxy: 4,500 customers as points, colour = fragility segment, size = buffer" /
   "Balance ribbon: the 3-month trajectory as a 3D ribbon, with a branch per event" /
   "Runway tunnel: months of runway as a tunnel you fly through" /
   "Rotating 3D logo/hero only"
   [Recommend galaxy + ribbon: they carry the data and the finding.]
3. Performance budget? "Loads in under 3 s, 60 fps on a laptop, 2D fallback (Recommended)" /
   "Best visuals, no budget"
4. Motion? "Respect reduced-motion and keep camera moves slow (Recommended)" / "Full animation"

### Topic 4: Judge engine (verification choices only)
Card: Judge engine. WHERE: `backend/engine.py`, tests in `backend/tests/`.
HOW: vectorized pandas groupby; independent check script that does not import the engine.
Questions:
1. Answer key? "Pick 3 accounts (normal, B <= 0, ends early) and print raw rows for a hand
   spreadsheet (Recommended)" / "We already have IDs" / "Independent script only"
2. Match strictness? "100% of 4,500 accounts vs an independent script (Recommended)" / "Test accounts only"

### Topic 5: 3-month balance forecast algorithm
Card: Trajectory forecast.
- WHAT: the customer's month-end balance for the next 3 months, with an uncertainty band.
- WHY: Devpost promise; Discovery; Communication.
- WHERE: `backend/forecast.py`; endpoint `/forecast/{account_id}`; ribbon + 2D line chart.
- HOW: depends on the choice below. Backtest: forecast from each month-end in 2025-01..2025-09,
  compare months t+1..t+3 with actual month_end_balance. Report MAE and median absolute % error
  vs a "nothing changes" baseline (balance stays flat).
Regression ladder (build in this order, compare all on the same 2025 backtest):
1. Baseline: median net flow (I - S) per month + damped 6-month trend, added month by month.
2. Ridge regression: target = net flow at horizon h (one model per h = 1, 2, 3); features from
   months <= t only: last 3/6/12-month income and spending medians, income volatility (CV),
   household_bills share, loan_payments share, avg_daily_balance 6-month slope, min_balance
   last 3 months, months since last negative day, account age, calendar month.
   StandardScaler + RidgeCV. Trajectory = current balance + cumulative predicted net flows.
3. XGBoost regression: same rows, features and horizons; objective reg:squarederror (or
   reg:absoluteerror), early stopping on the 2024 validation months, max 12 configs.
Split by time: train t in 2020-07..2023-09, validate 2024-01..2024-09, test 2025-01..2025-09.
No feature may use any month after t. Event shocks are applied by the engine ON TOP of the
predicted flows (e.g. income part x 0.55 for job loss); the model predicts the normal path.
Deliverable: docs/backtest.md with a table: MAE and median absolute % error at h = 1, 2, 3 for
flat baseline, statistical baseline, Ridge, XGBoost; show the winner in the app and say
honestly if ML does not beat the baseline.
Questions:
1. How far up the ladder? "Baseline + Ridge now, XGBoost if on time (Recommended)" /
   "Baseline only" / "All three now"
2. Uncertainty band? "P10-P90 from the model's validation residuals (Recommended)" /
   "Fixed +/-1 standard deviation" / "No band"
3. Must beat? "The flat baseline on MAE, or we say so honestly (Recommended)" / "No backtest"

### Topic 6: Event agent (Gemini)
Card: Event agent.
- WHAT: the user types "I lost my job" or "rent went up 200"; the agent extracts a structured
  event, shows it for confirmation, then the engine re-forecasts.
- WHY: Devpost promise; MLH Gemini; live twist speed.
- WHERE: `backend/agent.py`; endpoint `/parse-event`; chat box on the customer page.
- HOW: Gemini with a JSON response schema:
  {events: [{type: job_loss|income_cut|bills_up|rent_up|one_off|scam|reemployment,
  pct?, amount?, start_month (1-3), duration_months?}]}. Validate with pydantic. Show parsed
  values; user clicks Apply. A rule-based fallback parser handles the 3 README twist cards if
  the API fails. A test file of 20 phrasings must parse correctly.
Questions:
1. What may the agent do? "Parse events only; numbers always from the engine (Recommended)" /
   "Parse events + write a plain-English summary of the engine's result" / "Both, summary optional"
   [Recommend the third: parse always, summary as a button. The summary may only use numbers
   passed in from the engine.]
2. Confirmation step? "Always show parsed values before applying (Recommended)" / "Apply instantly"
3. Fallback if Gemini fails? "Rule-based parser for common events + sliders (Recommended)" / "Sliders only"
4. Which Gemini model? "A fast Flash-tier model, checked in AI Studio tonight (Recommended)" / "A Pro-tier model"

### Topic 7: Realistic runway and shocks
Card: Realistic runway. WHERE: `backend/realistic.py`.
HOW: month-by-month balance simulation; EI income = min(p*I, cap) for EI months, then 0 or I
from a re-employment month; spending = S'; runway = first month below zero, interpolated.
Test: with EI forever and no cap it equals the judge runway within 0.1.
Questions:
1. EI duration default? "6 months (Recommended)" / "Slider 1-12, default 6"
2. EI cap? "On by default with a toggle (Recommended)" / "Off"
3. Re-employment option? "Yes, optional (Recommended)" / "No"
4. money_in caveat? "State it as an upper bound (Recommended)" / "Estimate wages from transfers_in"

### Topic 8: Plan builder (Tangerine actions)
Card: Plan builder. WHERE: `backend/plan.py`; plan cards on the customer page.
HOW: surplus = I - S; targets 3 and 6 months of S; weekly Automatic Savings Program amount;
cut flexible categories largest-first in 10% steps; backup plan re-runs the forecast with cuts.
Questions:
1. Emergency target? "Show 3 and 6 months (Recommended)" / "3 only" / "6 only"
2. ASP share of surplus? "50% (Recommended)" / "25%" / "Reach 3 months in 12 months"
3. Flexible categories? (multiSelect) "card_withdrawals" / "cash_withdrawals_genuine" /
   "transfers_out_other" / "bank_fees"
4. Tangerine tools in plans? (multiSelect) "Automatic Savings Program + Goals" /
   "Money Rules" / "Orange Alerts" / "Left to Spend + Insights"

### Topic 9: Portfolio finding and Power BI
Card: Fragility map + Power BI.
- WHAT: segments Stable / Hidden fragile / Fragile / Already short across 4,500 customers.
- WHY: Discovery; Data Viz prize; the 15-second headline.
- WHERE: `backend/population.py` -> `powerbi/exports/*.csv`; `powerbi/ServaAI.pbix`; the 3D galaxy.
- HOW: run judge + realistic runway per shock for all accounts; bootstrap 95% interval for the
  headline share; breakdown by region, owner age band, card type, account age.
Questions:
1. Power BI pages? (multiSelect) "Headline: judge vs realistic" / "Segments by region and age" /
   "Shock comparison" / "Single-customer drill-through"
2. How do judges see Power BI? "Screenshots in the web app + Devpost, file in repo (Recommended)" /
   "Publish to Power BI web (needs a work/school account)" / "Open the .pbix live at the demo table"
3. Headline to test first? "Formula overstates runway for 1 in 3 (Recommended)" /
   "Share who can't last 6 months on EI" / "Show me the top 3 and I'll pick"

### Topic 10: Deployment (Vultr + servaai.us)
Card: Deployment.
- WHERE: one Vultr instance; nginx serves the built frontend and proxies `/api` to FastAPI.
- HOW: Docker Compose or systemd; HTTPS with Let's Encrypt; DNS A record for servaai.us -> the
  Vultr IP (change it where the domain's DNS is managed); `.env` for the Gemini key.
Questions:
1. Deploy when? "Sunday 7-9 AM after feature freeze (Recommended)" / "Tonight, then redeploy"
2. Process manager? "Docker Compose (Recommended)" / "systemd + venv"
3. Backup if deploy fails? "Run locally on the demo laptop (Recommended)" / "No backup"

### Topic 11: Demo, pitch, submission
Questions:
1. Presenter and driver? [Free text. Recommend different people.]
2. Freeze? "Feature freeze 9 AM, submit by 11:30 AM (Recommended)" / "Freeze 10 AM"
3. Video? "2-minute screen recording with voice-over (Recommended)" / "Slides + short clip"

### Topic 12: Risk flag (XGBoost classifier)
Card: Overdraft early warning.
- WHAT: risk tier (Watch / Act / Urgent) + top 3 reasons for each customer.
- WHY: Discovery, Impact; who Tangerine should contact first.
- WHERE: backend/risk.py; endpoint /risk/{account_id}; badge on the customer page; galaxy colour.
- HOW: label = any days_below_zero > 0 in months t+1..t+3 (about 2,180 positives); headline
  label y_new = same but only for rows with no negative days in t-2..t. Same time split and
  features as the forecast (no loans.status/defaulted, standing_orders or gender as features).
  XGBoost binary:logistic with scale_pos_weight; isotonic calibration on validation; SHAP
  TreeExplainer for reasons. Metrics: PR-AUC, recall and precision at top 5%, vs a rule
  baseline (buffer < 1 month of S) and the judge-runway baseline. Fairness: recall at top 5%
  by gender and age band.
1. Build it? "Yes, if the engine and forecast are green by 1 AM (Recommended)" /
   "Yes, in parallel now" / "No"

## Build phases (after CLAUDE.md is approved)

Suggested settings (the user sets these): Opus at xhigh for Phases 1 and 3; Opus at high for
2, 4 and 7; Sonnet at medium for 5, 6, 8 and 9; a fresh Opus session at xhigh for 10.
Gates are Saturday night / Sunday times. If a gate is missed, drop the latest optional phase
(3D first, then Power BI polish, then Vultr) before touching the core.

### Phase 0: Scaffold (about 20 min)
Folders `backend/`, `frontend/`, `powerbi/exports/`, `docs/`; `.env.example`; `.gitignore`
covering data/, .env, node_modules, *.parquet. Push to the public GitHub repo.
CHECK: "Is the repo public, and is the link in Devpost?"

### Phase 1: Judge engine + tests (gate: 10:30 PM)
`backend/engine.py`: precompute_profiles (cached parquet), profile, judge_runway, apply_shock
with a one-line arithmetic explanation. `backend/tests/independent_check.py` recomputes I, F,
S, B, H, P for ALL accounts without importing the engine: 100% match. README twists + edge cases.
CHECK:
- "Account <id>: B=<x>, I=<y>, S=<z>. Under EI 55%, what runway do you expect?" [let them
  compute it, then show the engine's answer]
- "Why mean of the last 6 rows for B but medians for I and S?"

### Phase 2: Realistic runway, forecast, plan (gate: 1 AM)
`realistic.py`, `forecast.py` (with backtest report in `docs/backtest.md`), `plan.py`, per the
decisions. Tests: realistic equals judge when EI is forever and uncapped; plans never cut fixed
costs; forecast backtest table vs flat baseline.
CHECK:
- "Forecast error vs the flat baseline is <a> vs <b>. Is that good enough to show, and how do
  we say it honestly?"
- "Read this customer's backup plan as you would to a judge."

### Phase 3: Event agent (gate: 2:30 AM)
`agent.py` with Gemini JSON schema, pydantic validation, fallback parser, `tests/test_agent.py`
with 20 phrasings including the 3 README twists and a scam. Key from `.env`.
CHECK: "Type 3 events of your own. Did each parse correctly? Which one confused it?"

### Phase 4: API (gate: 3 AM)
FastAPI: `/accounts/{id}`, `/shock`, `/forecast/{id}`, `/parse-event`, `/plan`, `/portfolio`.
Pydantic models, CORS for the dev server, response time under 300 ms (precomputed profiles).
CHECK: "Run the 3 README twists through the API. Same numbers as Phase 1?"

### Phase 5: 2D frontend core (gate: 5 AM)
React + Vite pages: Customer (lookup, cards, judge vs realistic runway, event chat with
confirm, sliders and presets, 3-month chart with band, plan cards), Portfolio (headline,
segments), Method (definitions, tests, sources). Works with 3D off.
CHECK: "Run a live twist yourself, timed. Under 30 seconds?"

### Phase 6: 3D layer (gate: 7 AM, or cut)
Per Topic 3: galaxy (InstancedMesh, hover tooltip, colour legend) and/or ribbon (trajectory
with event branches). 2D toggle; reduced-motion respected; lazy-load Three.js so the 2D page
paints first. Screenshot on a laptop viewport.
CHECK: "Does the 3D scene make the finding obvious in 5 seconds? If not, what should change?"

### Phase 7: Power BI exports (gate: 8 AM)
`backend/population.py` writes `powerbi/exports/*.csv` and `docs/findings.md` (headline with
bootstrap interval, segments, caveat). The team builds the .pbix pages from Topic 9.
CHECK: "Which single Power BI visual leads the Data Viz story?"

### Phase 8: Deploy (gate: 9 AM, else run locally)
Vultr + nginx + HTTPS + servaai.us DNS per Topic 10. Smoke test 5 accounts on the live URL.
CHECK: "Open servaai.us on a phone. Does it load and run a twist?"

### Phase 9: Write-up and Devpost (gate: 11:30 AM submit)
Replace every [X] in the Devpost story with confirmed numbers from `docs/findings.md` and
`docs/backtest.md`. Built-with tags: python, pandas, fastapi, react, three.js, gemini,
power-bi, vultr. Video script with timestamps. README with run steps and sources.
CHECK: "Say the 1-minute pitch out loud. Is the finding in the first 15 seconds?"

### Phase 10: Final review (fresh session)
Use a subagent as a skeptical judge: independent check, README twists through the live site,
5 random accounts by hand, every Devpost number traced to findings.md, no API key in git or
frontend bundle. Report only correctness problems, with file and line.

## CLAUDE.md template (fill from DECISIONS.md, under 70 lines)

```
# ServaAI (Sheridan Datathon 2026, Tangerine track)

## Goal
Any account_id + any life event -> judge runway (exact), realistic runway, 3-month balance
forecast, and a Tangerine plan. Gemini parses events; the Python engine makes every number.
3D web UI at servaai.us; Power BI for the portfolio story.

## Decisions (What / Why / Where / How cards live in DECISIONS.md)
<one line per decision>

## Judge definitions (match exactly)
<copy from Fixed facts>

## Hard rules
- IMPORTANT: numbers only from backend/engine + tests; the LLM never invents numbers.
- Judge number first, realistic beside it, both labelled.
- 2D core works with 3D off; cut 3D first if behind.
- Gemini key only in backend .env.
- Run pytest after every backend change and show the output.

## Commands
cd backend && pytest -q
cd backend && uvicorn app:app --reload
cd frontend && npm run dev
python -m backend.population
```
