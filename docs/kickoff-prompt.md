# ServaAI build prompt (What / Where / When / Why / How)

Use the servaai-build skill (.claude/skills/servaai-build/SKILL.md), CLAUDE.md and DECISIONS.md
as your rules. Re-read them now. Then work through the plan below. For EVERY feature, before
building it, show me a 5-part card and ask me the open choices with AskUserQuestion
(recommended option first). Record the final card in DECISIONS.md. I make the decisions.

## The card format (use it for every feature and every plan)
- WHAT: what it does and what the judge sees on screen, in one or two sentences.
- WHERE: data files/columns it reads, backend file + function, API endpoint, frontend page +
  component, and the moment in the demo it appears.
- WHEN: which phase, its gate time (below), and what must be finished first.
- WHY: which score or prize it wins (Tangerine live twist, Discovery 35%, Data Use 25%,
  Communication 25%, Impact 15%, Data Viz prize, MLH Gemini, MLH Vultr, MLH GoDaddy domain),
  and what we lose without it.
- HOW: the algorithm step by step, libraries, and the test that proves it works.

## Current state (already done, do not redo)
- Devpost project "servaai" exists; tracks: Tangerine, Data Viz, Gemini, Vultr, GoDaddy.
  Pitch promises: 3-month balance forecast, instant updates from life events, Tangerine plan.
- backend/.env has GEMINI_API_KEY and GEMINI_MODEL=gemini-3.6-flash. Never print or log the key.
  Google Cloud project "ServaAI" is billed to the $25 event credit (ends Nov 8).
- Domain servaai.us registered (DNS will point to a Vultr server later).
- Data in data/ (9 CSVs + README.md). Judge formulas are fixed in the skill's "Fixed facts".

## WHEN: the clock (Saturday Nov 7 -> Sunday Nov 8)
| Gate | Time | Must be true |
|---|---|---|
| Phase 1 judge engine | 10:30 PM | 100% match vs independent check on all 4,500 accounts; 3 README twists pass |
| Phase 2 forecast + realistic runway + plan | 1:00 AM | Backtest table: flat baseline vs statistical baseline vs Ridge (XGBoost if on time) |
| Phase 3 Gemini event agent | 2:30 AM | One test call works; 18/20 test phrasings parse; 3 README twists parse; fallback parser works |
| Phase 4 FastAPI | 3:00 AM | Same numbers through the API as Phase 1 |
| Phase 5 2D frontend | 5:00 AM | A live twist runs in under 30 s with 3D switched off |
| Phase 6 3D layer | 7:00 AM | Or cut it |
| Phase 7 Power BI exports + findings.md | 8:00 AM | Headline number with bootstrap interval |
| Phase 8 Vultr deploy + servaai.us | 9:00 AM | Or run locally for the demo |
| Phase 9 Devpost + video | 11:30 AM | Submitted; every [X] in the story replaced |
If a gate is missed: cut 3D first, then Power BI polish, then Vultr. Never cut the engine,
forecast, agent or plan (they are promised on Devpost).

## WHAT / WHY / HOW of the core features (propose cards for each, ask me, then build)
1. Judge engine: exact I, F, S, B, H, P, shocks, runway (fixed formulas). Why: live twist.
2. 3-month forecast: regression ladder (statistical baseline -> Ridge -> XGBoost), one model per
   horizon, time split train 2020-07..2023-09 / validate 2024 / test 2025, honest backtest.
   Why: Devpost promise, Data Use.
3. Realistic runway: EI ends after 6 months, capped at 729 dollars/week, optional re-employment.
   Why: our Discovery finding (judge formula overstates runway for about 1 in 3 customers).
4. Gemini event agent: text -> JSON events (schema + pydantic), confirm before applying, numbers
   only from the engine, rule-based fallback. Why: Devpost promise, MLH Gemini.
5. Plan builder: Tangerine actions (Automatic Savings Program per week, Goals, Money Rules,
   Orange Alerts) from the customer's own numbers. Why: Impact.
6. XGBoost risk classifier (overdraft in next 3 months) with SHAP reasons, only if Phases 1-2
   are green by 1 AM. Why: Discovery, Impact.
7. Web UI: FastAPI + React + react-three-fiber; 2D core first; 3D galaxy + balance ribbon.
   Why: Communication, Data Viz.
8. Power BI portfolio pages from exported CSVs. Why: Data Viz prize.

## Rules
- Plan mode before each phase; show the plan as a 5-part card; wait for my approval.
- After each phase: show evidence (pytest output, tables, screenshots), ask 2 check questions
  I must answer, then wait for "go".
- Every number on screen comes from the tested Python engine; the judge number is shown first.
- Tell me the current time vs the next gate at the start of every phase.

Start now: tell me which phase we are in and how far we are from the next gate, then continue.
