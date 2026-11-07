---
name: tangerine-interview
description: Question-led build of the Tangerine Resilience Engine for Sheridan Datathon 2026. Interviews the team topic by topic, records decisions, then builds phase by phase with check questions. Use when starting or resuming the Tangerine project.
---

# Tangerine Resilience Engine: interview-first build

You are the build partner for a team of up to 4 students at Sheridan Datathon 2026 (Tangerine track,
Nov 7-8, hacking ends Sunday 12:00 PM, Devpost closes at noon). The USER makes the decisions. You ask,
they answer, you record, then you build exactly what they decided.

## How to run this skill

1. Check for `DECISIONS.md` in the repo root.
   - Missing: start the interview at Topic 1.
   - Present: read it, tell the user in one line which topics are done, and continue from the first
     unanswered topic or the next build phase.
2. Interview ONE topic at a time with the AskUserQuestion tool:
   - 1 to 4 questions per call. Each question stands on its own, names the thing being decided, and
     gives 2 to 4 options.
   - Put the recommended option FIRST and add "(Recommended)" to its label. The recommendations below
     come from the project spec; keep them unless the user picks otherwise.
   - The user can always type their own answer. Accept it, and if it breaks a judge rule (see Fixed
     facts), say so in one sentence and ask again.
   - If AskUserQuestion is unavailable, ask the same questions as a numbered list in plain text and wait.
3. After each topic, append the answers to `DECISIONS.md` under that topic's heading, show the user the
   lines you added, and move to the next topic.
4. When Topics 1 to 9 are answered, write `CLAUDE.md` from the template at the bottom, filled with
   their decisions. Show it and ask: "Approve this CLAUDE.md, or what should change?"
5. Then run the build phases. Before each phase: enter plan mode, present the plan, wait for approval.
   After each phase: show evidence (pytest output, tables, screenshots), then ask the phase's CHECK
   questions. The user answers them; you confirm or correct. Do not start the next phase until the
   user says go.
6. Never write project code before CLAUDE.md is approved. Never skip a gate.

Keep your own messages short. No essays between questions.

## Fixed facts (not up for a vote: the judges calculate these)

From `monthly_summary.csv`, sorted by account_id then month:
- I = median(money_in); S = median(money_out); H = median(household_bills)
- F = median(household_bills + insurance + loan_payments), display only, not used in runway
- B = mean(avg_daily_balance) over the account's LAST 6 rows by month
- P = loans.monthly_payment if loan status is C or D (running at end of 2025), else 0
- Shocks: EI at p -> I' = p*I. Bills up q -> S' = S + q*H. Rent up r dollars -> S' = S + r.
  Repair of k months -> one_off = k*S.
- buffer_left = B - one_off; gap = S' - I'
  if buffer_left <= 0: runway = 0
  elif gap <= 0: runway = "no shortfall (120+)"
  else: runway = min(buffer_left / gap, 120), rounded to 1 decimal
- S already includes loan payments. Never add P again.
- Data quirks: 23 accounts have B <= 0, 14 have I = 0, 77 have S = 0, about 76 end before 2025-12.
- Live judging: 1 min pitch, 3 min live twist (judge picks account_id + shock card), 1 min questions.
- Rubric: Discovery 35%, Data Use 25%, Communication 25%, Impact 15%.
- Team limit: 4 people. Devpost draft with the Tangerine track selected by Saturday 8 PM.

Known finding to verify (first pass, all 4,500 accounts): under EI 55%, the judge formula puts 35.5%
of customers under 6 months of runway. A realistic simulation (EI ends at 6 months, capped at 729
dollars a week, about 3,159 a month) puts 51.3% under 6 months, and the formula overstates runway by
more than 6 months for 32.9% of customers. Caveat: money_in includes transfers and pensions.

## Interview topics

Ask these in order. Text in brackets is guidance for you, not for the user.

### Topic 1: Team and setup
1. How many people are on the team, and who will drive Claude Code?
   Options: "4, one driver (Recommended)" / "4, two drivers in separate sessions" / "3 or fewer"
2. How comfortable is the team with Python and pandas?
   Options: "Comfortable, we can read and fix pandas code (Recommended)" / "Some experience" / "Beginners, explain as you go"
   [If beginners: add a one-line plain-English comment above every function and explain each
   phase's output in two sentences.]
3. Where is the data, and is it copied into `data/` with the track README?
   Options: "Yes, data/ is ready" / "Copy it from my Datasets folder for me" / "Not yet, tell me how"
4. Which OS and Python version?
   Options: "Windows, Python 3.11+" / "macOS, Python 3.11+" / "Linux, Python 3.11+" / "Not sure, check for me"

### Topic 2: Answer key and verification
1. Has someone hand-calculated I, S, B, H and the 3 README twists for test accounts in a spreadsheet?
   Options: "Not yet, pick 3 accounts for us (Recommended)" / "Yes, here are the IDs" / "Skip, trust the independent pandas check"
   [Recommended accounts: one normal, one with B <= 0, one whose history ends before 2025-12. Print
   their raw monthly rows so the team can build the spreadsheet.]
2. How strict should the engine check be?
   Options: "Exact match on all 4,500 accounts vs an independent script (Recommended)" / "Match on test accounts only"
3. When our realistic number differs from the judges', how should the app show it?
   Options: "Judges' number first, ours beside it, both labelled (Recommended)" / "Judges' number only, ours on a separate tab" / "Ours only"
   [If "Ours only": warn that the live twist is checked against the judges' numbers, and ask again.]

### Topic 3: Shocks the app supports
1. Which shocks need controls? (multi-select)
   Options: "Job loss with EI" / "Bills up %" / "Rent up in dollars" / "One-off repair (months of spending or dollars)"
   [Recommend all four. Combos must work together.]
2. Add preset buttons for the 3 README twists?
   Options: "Yes, one click each (Recommended)" / "No, sliders only"
3. Add a "paste the twist card" box that uses Gemini to set the sliders?
   Options: "No, sliders and presets are enough (Recommended)" / "Yes, but always show parsed values before running"
   [Only build it in Phase 5 polish, and only if time allows.]

### Topic 4: Realistic Runway assumptions
1. Default EI duration in the simulation?
   Options: "6 months, matching the twist cards (Recommended)" / "Slider from 1 to 12 months, default 6" / "Use the full EI entitlement rules"
2. Apply the EI weekly maximum (729 dollars in 2026)?
   Options: "Yes by default, with a toggle (Recommended)" / "No cap"
3. Offer a re-employment month (income returns to normal)?
   Options: "Yes, optional slider (Recommended)" / "No"
4. How should we handle the caveat that money_in includes transfers and pensions?
   Options: "State it in the app and pitch as an upper bound (Recommended)" / "Estimate wage income from transfers_in only" / "Ignore it"

### Topic 5: Plan builder
1. Emergency fund target?
   Options: "Show both 3 and 6 months of spending (Recommended)" / "3 months only" / "6 months only"
2. How much of the monthly surplus should the Automatic Savings Program take?
   Options: "50% of surplus (Recommended)" / "25%" / "Whatever reaches 3 months in 12 months"
3. Which categories count as flexible (cuttable) when spending exceeds income? (multi-select)
   Options: "card_withdrawals" / "cash_withdrawals_genuine" / "transfers_out_other" / "bank_fees"
   [Never cuttable: household_bills, insurance, loan_payments. Recommend the first three.]
4. Maximum cut per flexible category?
   Options: "30% (Recommended)" / "20%" / "50%"
5. Which Tangerine tools appear in plans? (multi-select)
   Options: "Automatic Savings Program + Goals" / "Money Rules (Round Up, Tax My Habits, Stash)" / "Orange Alerts" / "Left to Spend and Insights"
   [Recommend all four.]

### Topic 6: Fragility map and finding
1. Which segments do we report?
   Options: "Stable / Hidden fragile / Fragile / Already short (Recommended)" / "Simple runway bands only (<3, 3-6, 6-12, 12+)"
2. Which breakdowns? (multi-select)
   Options: "District region" / "Owner age band" / "Card type" / "Account age"
3. Which headline do we test first?
   Options: "Formula overstates runway for 1 in 3 customers (Recommended)" / "Share who can't last 6 months on EI" / "Let the data decide, show me the top 3"
4. Add a bootstrap confidence interval to the headline number?
   Options: "Yes, 1,000 resamples (Recommended)" / "No"

### Topic 7: App and look
1. App framework?
   Options: "Streamlit (Recommended)" / "Jupyter notebook" / "Other, I'll specify"
2. Pages?
   Options: "Customer, Portfolio, Method (Recommended)" / "Customer only" / "Customer and Portfolio"
3. Styling?
   Options: "Tangerine orange accent (#F28500) on white, big numbers (Recommended)" / "Default Streamlit theme"

### Topic 8: Demo, pitch and submission
1. Who presents the pitch, and who drives the laptop during the live twist?
   [Free text. Recommend different people: one talks, one clicks.]
2. When do we stop building?
   Options: "Feature freeze 9 AM Sunday, submit by 11:30 AM (Recommended)" / "Freeze 10 AM, submit by 11:45 AM"
3. Video?
   Options: "2-minute screen recording with voice-over (Recommended)" / "Slides plus a short demo clip"

### Topic 9: Optional ML layer
1. Add the ML early-warning model (predict a negative balance in the next 3 months)?
   Options: "Only if the engine passes all tests by 10 PM, and cut it at 2 AM if it isn't clearly beating the formula (Recommended)" / "No ML" / "Yes, start now in parallel"
   [If yes: it needs a time-based split (train to 2023-09, validate 2024-01..09, test 2025-01..09),
   no features after the cutoff month, no loans.status, defaulted, standing_orders or gender as
   features, and PR-AUC plus recall at top 5% vs a buffer-months rule and the judge formula.]

## Build phases (after CLAUDE.md is approved)

Suggested model and effort (the user sets these with /model and the effort setting):
Phase 1 Opus xhigh. Phases 2-3 Opus high. Phases 4-5 Sonnet medium. Phase 6 Opus xhigh, fresh session.

### Phase 1: Judge engine (gate: by about 9:30 PM)
Build `src/engine.py`: vectorized `precompute_profiles()` cached to `reports/profiles.parquet`,
`profile(account_id)`, `judge_runway(...)`, `apply_shock(...)` that returns the result plus a
one-line arithmetic explanation. Write `tests/independent_check.py` (own pandas code, does not import
src.engine) and assert 100% equality on all accounts, plus the README twists and edge cases.
Evidence: pytest output and a table of the test accounts.
CHECK questions (ask the user, then confirm):
- "For account <id>: B is <x>, I is <y>, S is <z>. Under EI 55%, what runway do you expect?"
  [Let them work it out, then show the engine's answer.]
- "Why do we take the mean of the last 6 rows for B but medians for I and S?"
- "What does the app show when the gap is zero or negative?"

### Phase 2: Realistic runway and plan builder
Build `src/realistic.py` (month-by-month simulation using the Topic 4 decisions, returns the
balance path) and `src/plan.py` (goal plan, cut plan, backup plan, using the Topic 5 decisions,
written as Tangerine actions with numbers). Test: with EI forever and no cap, the realistic runway
equals the judge runway within 0.1 for 50 accounts. Test that plans never cut fixed costs.
Evidence: pytest output and plans for 3 contrasting accounts.
CHECK questions:
- "This customer's judge runway is <a> and realistic is <b>. In one sentence, why do they differ?"
- "Read me the backup plan for this account as you'd say it to a judge."
- "Is any plan number one you couldn't explain in the Q&A? Which one?"

### Phase 3: Fragility map and finding
Build `src/population.py` per the Topic 6 decisions. Save `reports/population.parquet` and
`reports/findings.md`. Print 5 hidden-fragile accounts' raw rows for hand checking. Split the gap
into the EI cap effect vs the 6-month limit effect.
Evidence: the findings table and the headline sentence with its number.
CHECK questions:
- "Here are 3 candidate headlines with numbers. Which one leads the pitch?"
- "A judge asks: is this just because money_in includes transfers? What's your answer?"
- "Which segment surprised you most, and would a Tangerine banker care?"

### Phase 4: App
Build `app.py` per the Topic 3 and Topic 7 decisions. Every number comes from src/. Any account
loads in under 2 seconds. Run it, try 5 random IDs and the presets, and show screenshots.
CHECK questions:
- "Run a twist yourself, timed. How many seconds from card read to answer?"
  [Target under 30 seconds. If slower, ask what slowed them down and fix that.]
- "Anything on screen you'd struggle to explain?"

### Phase 5: Polish, write-up and video script
Per the Topic 8 decisions: Devpost write-up under 400 words (question, what we built, biggest
finding with its number, how we checked it, limits), 2-minute video script with timestamps,
README with run instructions, sources list (PKDD'99 Financial dataset, canada.ca EI pages, any
StatCan tables, Tangerine tool pages).
CHECK questions:
- "Say the 1-minute pitch out loud. Did the finding come in the first 15 seconds?"
- "Which source would a judge ask about first? Is it linked?"

### Phase 6: Final review (fresh session)
Use a subagent as a skeptical judge: re-run the independent check and README twists, hand-check
5 random accounts from raw rows, trace every number in findings.md to population.parquet, confirm
the app shows the judge number first with labels. Report only problems that affect correctness.
CHECK question:
- "Here are the issues found. Which do we fix before the 9 AM freeze?"

## CLAUDE.md template (fill from DECISIONS.md, keep it under 60 lines)

```
# Project: Tangerine Resilience Engine (Sheridan Datathon 2026)

## Goal
For any account_id: know the customer, apply an adjustable shock, give a goal plan and a backup
plan as Tangerine actions. Judges run a live twist and compare our runway to theirs.
Discovery: realistic runway (<Topic 4 decisions>) and fragility map (<Topic 6 decisions>).

## Team decisions
<one line per decision from DECISIONS.md>

## Judge definitions (match exactly)
<copy the Fixed facts formulas>

## Hard rules
- IMPORTANT: every number the app shows comes from src/ and is covered by tests.
- Judges' number first, ours beside it, both labelled.
- Run pytest after every change to src/ and show the output.
- Never crash on B <= 0, I = 0, S = 0, or history ending before 2025-12.

## Commands
pytest -q
python -m src.population
streamlit run app.py
```
