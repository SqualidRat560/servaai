# ServaAI decisions (What / Why / Where / How)

## Topic 1: Team, skills, setup
- Driver: one driver, one Claude Code session. The other 3 verify numbers, build Power BI, and write the pitch.
- React/JS experience: beginners. Keep React simple, with a small 3D scope (one hero scene), and cut it first if we fall behind.
- Tools: Python 3.14.3 and Node 24.14.0 are installed (checked).
- Data: `data/` has the README and all 9 CSVs (checked).

## Topic 2: Architecture
**Card: Web app architecture (FINAL)**
- WHAT: website at servaai.us; judge enters account_id + event and sees numbers, a 3-month trajectory and a plan.
- WHY: Tangerine live twist; MLH Vultr; MLH GoDaddy (servaai.us); Communication.
- WHERE: `backend/` (FastAPI + engine), `frontend/` (React + Vite + react-three-fiber), `powerbi/`.
- HOW: FastAPI serves JSON from the engine; React calls `/api/*`. Tailwind with Tangerine orange #F28500 on a dark navy background. Recharts for 2D charts (line chart + P10-P90 band). 3D is one lazy-loaded component; the 2D page never depends on it. Claude writes the React code; the team verifies it in the browser.

## Topic 3: 3D UI scope
**Card: 3D layer (FINAL)**
- WHAT: four 3D pieces on top of 2D dashboards:
  1. Hero scene (landing): an original low-poly ServaAI mascot in Tangerine orange stands on a coin stack whose height = buffer B of a sample account. A shock card drains coins (buffer_left); applying the plan refills them. Numbers come from the engine API.
  2. Portfolio galaxy: 4,500 customers as points; colour = fragility segment, size = B.
  3. Balance ribbon: 3-month trajectory as a 3D ribbon, one branch per event.
  4. Rotating logo/hero mark.
- WHY: Best Data Visualization & Storytelling; Communication; first impression in a 1-minute pitch; the hero makes "updates instantly when life happens" visible.
- WHERE: `frontend/src/three/` (HeroScene, Galaxy, Ribbon, Logo); hero + logo on the landing page, galaxy on Portfolio, ribbon on Customer. Data from `/api/accounts/{id}`, `/api/shock`, `/api/portfolio`, `/api/forecast/{id}`.
- HOW: react-three-fiber + drei; coins and galaxy points via InstancedMesh; orbit controls; lazy-loaded with React.lazy so the 2D page paints first; a 2D toggle on every page.
  - Budget: under 3 s load, 60 fps on a laptop, 2D fallback.
  - Motion: respect prefers-reduced-motion; slow camera moves.
  - Build order: hero -> galaxy -> ribbon -> logo. Cut order if a gate is at risk: logo -> ribbon -> galaxy -> hero. The 2D core is never cut.
  - Test: screenshot at a laptop viewport; the FPS counter stays at about 60; the app works with 3D off.

## Topic 4: Judge engine
**Card: Judge engine (FINAL)**
- WHAT: exact judge runway (and I, S, H, F, B, P) for any account under any shock card, with a one-line arithmetic explanation.
- WHY: Tangerine live twist (must match the judges exactly); Data Use.
- WHERE: `backend/engine.py`; `backend/tests/test_engine.py`; `backend/tests/independent_check.py` (does not import the engine); cached profiles parquet.
- HOW: vectorized pandas groupby on monthly_summary sorted by account_id, month; formulas per Fixed facts.
  - Answer key: Claude picks 3 accounts (normal, B <= 0, ends before 2025-12) and prints their raw rows; a teammate computes them by hand in a spreadsheet; the values become pytest asserts.
  - Strictness: 100% of 4,500 accounts must match the independent script on every metric (to the cent), plus the README twist cards and the edge cases (B <= 0, I = 0, S = 0, early end).

## Topic 5: 3-month balance forecast
**Card: Trajectory forecast, regression ladder (FINAL; replaces the earlier baseline-only card)**
- WHAT: month-end balance for the next 3 months with a P10-P90 band, before and after the event; the model that wins the 2025 backtest powers the app.
- WHY: Devpost promise ("forecasts a customer's next 3 months of balance"); Discovery; Data Use (honest ML-vs-baseline comparison); Communication.
- WHERE: `backend/features.py` (shared with Topic 12); `backend/forecast.py`; `/forecast/{account_id}`; Ribbon (3D) + Recharts line with band (2D); `docs/backtest.md`; the winning model and its error on the Method page.
- HOW:
  - Ladder, built in order: (1) baseline = median(money_in - money_out) + 0.5 x the 6-month trend in net flow; (2) Ridge now; (3) XGBoost only if Phase 2 has slack before the 1 AM gate.
  - Ridge: one model per h = 1, 2, 3; target = net flow at t+h. Features from months <= t only: 3/6/12-month income and spending medians, income CV, household_bills share, loan_payments share, avg_daily_balance 6-month slope, min_balance last 3 months, months since last negative day, account age, calendar month. StandardScaler + RidgeCV.
  - XGBoost: same rows, features and horizons; reg:squarederror (or reg:absoluteerror); early stopping on the 2024 validation months; max 12 configs.
  - Split by time: train t in 2020-07..2023-09, validate 2024-01..09, test 2025-01..09. No feature uses any month after t.
  - Trajectory = current month_end_balance + cumulative predicted net flows (checked: the balance change equals money_in - money_out within $0.14 on all 180,826 month steps).
  - Shocks on top, from the event's start month: flow' = predicted flow + (I' - I) - (S' - S); one-offs subtract in their month. The model predicts only the normal path.
  - Band: P10-P90 of the winning model's 2024 validation errors per horizon, scaled to each account's own flow volatility.
  - Must beat: the flat baseline on MAE, or the Method page says so honestly.
  - Deliverable: `docs/backtest.md` with MAE and median absolute % error at h = 1, 2, 3 for flat, baseline, Ridge (and XGBoost if built).
  - Tests: leakage test (features at t don't change when months after t are deleted); the band contains the line; the backtest table is generated by a script.
  - Libraries: scikit-learn 1.9, xgboost 3.4 (Windows wheels for Python 3.14 checked).

## Topic 6: Event agent (Gemini)
**Card: Event agent (FINAL)**
- WHAT: free-text life event -> structured event shown for confirmation -> Apply -> the engine re-forecasts. An optional "Explain" button gives a plain-English summary.
- WHY: Devpost promise ("updates instantly when life happens"); MLH Best Use of Gemini API; live twist speed.
- WHERE: `backend/agent.py`; `/parse-event`, `/explain`; chat box + confirm chip + sliders on the Customer page; `backend/tests/test_agent.py`.
- HOW:
  - Gemini Flash-tier model (exact ID verified in AI Studio tonight) with response JSON schema {events: [{type: job_loss|income_cut|bills_up|rent_up|one_off|scam|reemployment, pct?, amount?, start_month 1-3, duration_months?}]}; pydantic validation.
  - Always show the parsed values before applying.
  - Summary: the prompt gets only engine numbers; a post-check rejects any number in the output that wasn't passed in.
  - Fallback: rule-based regex parser (job loss/EI %, bills %, rent $, repair months, scam/one-off $) + sliders, always available.
  - Key only in backend `.env`. Test: 20 phrasings including the 3 README twists and a scam, through both Gemini and the fallback.

## Topic 7: Realistic runway and shocks
**Card: Realistic runway (FINAL)**
- WHAT: ServaAI's realistic runway beside the labelled judge number.
- WHY: Discovery (the formula overstates runway for about 1 in 3); Communication; Devpost honesty.
- WHERE: `backend/realistic.py`; "Realistic" card beside the "Judge formula" card; EI cap toggle + re-employment control on the Customer page.
- HOW:
  - Monthly simulation from buffer_left; EI income = min(p*I, 3159) for months 1-6 (EI duration fixed at 6), then 0, or I from the re-employment month if set; spending = S'.
  - Runway = first month the balance drops below zero, linearly interpolated, capped at 120.
  - EI cap on by default, with a toggle. Re-employment optional.
  - Caveat line: "money_in includes transfers and pensions, so EI here is an upper bound; real runway may be shorter."
  - Test: EI forever + cap off == judge runway within 0.1, for all accounts.

## Topic 8: Plan builder (Tangerine actions)
**Card: Plan builder (FINAL)**
- WHAT: plan cards per customer: emergency fund progress (3- and 6-month targets), weekly ASP amount, and a backup plan of flexible-spending cuts after a shock, each tied to a Tangerine tool.
- WHY: Devpost promise ("builds a Tangerine plan"); Impact; Communication; drives the hero's coin refill.
- WHERE: `backend/plan.py`; `/plan`; plan cards on the Customer page; HeroScene refill.
- HOW:
  - surplus = I - S; targets = 3*S and 6*S, with progress = B / target.
  - ASP weekly = 0.5 * max(surplus, 0) / 4.33.
  - Backup: flexible categories = card_withdrawals, cash_withdrawals_genuine, transfers_out_other, bank_fees (medians); cut largest-first in 10% steps, re-running the realistic runway until it reaches 3 months or all cuts are exhausted.
  - transfers_out_other is labelled "if discretionary" (it may include rent or family transfers).
  - Tools: Automatic Savings Program + Goals, Money Rules, Orange Alerts, Left to Spend + Insights.
  - Test: fixed costs (household_bills, insurance, loan_payments) are never cut; plan numbers come from the engine only.

## Topic 9: Portfolio finding and Power BI
**Card: Fragility map + Power BI (FINAL)**
- WHAT: 4 segments across 4,500 customers: Stable / Hidden fragile (judge >= 6 months, realistic < 6) / Fragile / Already short (buffer_left <= 0). Headline: "the judge formula overstates runway by more than 6 months for about 1 in 3 customers" (first pass 32.9%; to be verified).
- WHY: Discovery; Best Data Visualization & Storytelling; the 15-second headline.
- WHERE: `backend/population.py` -> `powerbi/exports/*.csv` + `docs/findings.md`; `powerbi/ServaAI.pbix` (in repo); screenshots on the web Portfolio page + Devpost; feeds the 3D galaxy via `/portfolio`.
- HOW:
  - Judge + realistic runway per account per shock (EI 55%, bills up, rent up, repair, scam).
  - Bootstrap 95% CI (1,000 resamples) for the headline share; breakdowns by region, owner age band, card type and account age.
  - Power BI pages: (1) Headline: judge vs realistic, (2) Segments by region and age, (3) Shock comparison. No drill-through page.
  - Delivery: PNG screenshots in the app + Devpost; .pbix in the repo.

## Topic 10: Deployment (Vultr + servaai.us)
**Card: Deployment (FINAL)**
- WHAT: live app at https://servaai.us.
- WHY: MLH Best Use of Vultr; MLH Best Domain (GoDaddy Registry); judges can try it on phones.
- WHERE: one Vultr instance; `docker-compose.yml` (nginx + api); nginx serves `frontend/dist` and proxies `/api` to FastAPI (uvicorn); `.env` on the server only.
- HOW:
  - Deploy Sunday 7-9 AM after the feature freeze, with Docker Compose. HTTPS via Let's Encrypt (certbot).
  - DNS A record servaai.us (+ www) -> Vultr IP, changed where the domain's DNS is managed (currently parked on Articulation). Note: set the A record early (Saturday night) so DNS has time to propagate.
  - Smoke test 5 accounts + the 3 README twists on the live URL.
  - Backup: the same build runs locally on the demo laptop, tested once before demos.

## Topic 11: Demo, pitch, submission
- Presenter and laptop driver are different people (names TBD by the team).
- Feature freeze Sunday 9:00 AM; Devpost submitted by 11:30 AM (closes 12:00 PM).
- Video: 2-minute screen recording with voice-over, showing the finding in the first 15 s and a live twist.

## Topic 12: Risk flag (XGBoost classifier)
**Card: Overdraft early warning (FINAL; replaces "no ML layer")**
- WHAT: a risk tier (Watch / Act / Urgent) + top 3 reasons for each customer.
- WHY: Discovery; Impact (who Tangerine should contact first); Data Use.
- WHERE: `backend/risk.py` (reuses `backend/features.py`); `/risk/{account_id}`; badge on the Customer page (hidden if the model isn't built); optional galaxy colour mode.
- HOW:
  - Build only if the engine and forecast are green by 1 AM. Hard stop 2:00 AM. The hour comes out of the 3D window (later gates move 1 h: agent 3:30, API 4:00, 2D core 6:00, 3D 6:00-7:00); 3D cut order is unchanged (logo -> ribbon -> galaxy -> hero).
  - Galaxy colour stays fragility segment by default (Topic 3); risk tier is a second colour mode, so the galaxy works without risk.py.
  - Label y = any days_below_zero > 0 in months t+1..t+3 (2,182 positive rows, checked). Headline label y_new = same, only rows with no negative days in t-2..t (1,181 positives; 148 in validation, 277 in test, checked).
  - Same time split and features as the forecast. Not used as features: loans.status/defaulted, standing_orders, gender.
  - XGBoost binary:logistic with scale_pos_weight; isotonic calibration on validation; SHAP TreeExplainer for the top 3 reasons.
  - Metrics on test: PR-AUC, recall and precision at top 5%, vs a rule baseline (buffer < 1 month of S) and the judge-runway baseline. 95% intervals by bootstrapping accounts (positives cluster in 288 accounts).
  - Fairness: recall at top 5% by gender (clients.gender M/F) and age band, with the positive count shown per group; groups under 30 positives are marked "too few to judge".
  - Tests: no feature uses months after t; the model never sees gender; tiers are monotonic in calibrated probability.

## Update (Sat 11:35 PM): order and style
- Phase 2 finished at 11:31 PM. Topic 12 risk flag: SKIPPED by the team. That time goes to the agent, then the real frontend + 3D.
- Order: Phase 3 Gemini agent -> Phase 4/5 React frontend (designed 2D core) -> Phase 6 3D (hero coin scene first).
- Visual style: "Bold Tangerine 3D": dark navy scene, glowing orange coins, the hero on a coin stack that drains or refills live with engine numbers, big numbers, minimal chrome. The localhost HTML page is a throwaway preview and gets replaced.
