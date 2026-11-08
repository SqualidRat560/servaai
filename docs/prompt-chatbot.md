# Task for Claude Code: interactive money chatbot + clickable account items

Do this AFTER docs/prompt-account-and-fade.md (it needs the /statement endpoint). Same branch
`feature/account-view`, same rules: do not touch backend/.env, all existing tests must pass, headline numbers
must not change, do not deploy. Hard stop at 10:45 AM: if the chat is not tested by then, ship the account view
without it and tell me.

## 1. Clickable account items ("by name")
The data is anonymized: there are NO customer names. "By name" means each item is a labelled card:
- **Chequing balance**: current balance (from /statement). Click opens the transaction list, all transactions.
- **Loan**: remaining (estimate), monthly payment, paid-vs-remaining bar. Click opens the transaction list
  filtered to `purpose == "loan payment"`.
- **Spending by type**: one row per category name (Household bills, Insurance, Loan payments, Card spending,
  Cash withdrawals, Transfers out, Bank fees; and income: Salary/transfers in, Pension, Interest) with last
  month's total. Click a row opens the list filtered to that category.
- **Cards**: card type and issue date (no click).
The transaction list opens as an inline expandable panel under the cards (an accordion), not a new page:
newest first, date, name/purpose, amount (in = sage, out = ink), day's closing balance, "Load more", in/out
filter, and a month picker. Keyboard accessible; Esc closes it. If the panel fails, fall back to a simple
`<details>` dropdown with the same rows.
Backend: extend /statement with `purpose` and `direction` filters, plus `GET /api/accounts/{id}/categories?month=YYYY-MM`
(totals per category from monthly_summary columns; they already add up to money_out).

## 2. Interactive chatbot (free questions, not fixed ones)
A chat panel on the Customer page ("Ask about your money"). The customer can ask anything about their own
finances and lifestyle, for example:
"How much do I spend on bills?" / "Can I afford a $400 car payment?" / "If I join a $60 gym, how long does my
buffer last if I lose my job?" / "Where did my money go in March?" / "Should I pay down my loan or save?"
/ "What happens if I buy a $1,500 laptop?"

Design: `POST /api/chat` with {account_id, messages: last 8 turns, max 500 chars each}. Use Gemini function
calling (google-genai, same model chain and env as backend/agent.py) with these read-only tools, all bound to
the request's account_id (the model cannot pick another account):
- get_overview(): profile I, S, F, H, B, P, current balance, loan summary.
- get_categories(month?): category totals (the endpoint above).
- get_transactions(purpose?, direction?, month?, limit<=20): rows from /statement.
- run_scenario(ei_pct?, bills_up_pct?, rent_up?, one_off?, repair_months?, reemploy_month?): calls the SAME
  engine as /api/shock and returns judge + realistic runway. Lifestyle costs map onto it: a new recurring
  monthly cost (car payment, gym, subscription) -> rent_up = that amount; a one-time purchase -> one_off.
- get_forecast(): the existing 3-month forecast with its band.
System prompt rules: answer ONLY from tool results; every number in the answer must come from a tool result
(reuse agent.numbers_are_grounded; if it fails, answer with a short template built from the tool data instead);
say plainly when the data cannot answer; no investment, tax or legal advice (say "I can show what the numbers
do, not tell you what to buy"); never claim to move money; 4 sentences max plus optional bullets; Canadian
dollars; friendly, not salesy.
Response JSON: {text, used_tools: [...], links: [{label, kind: "transactions"|"forecast"|"portfolio",
filter?}]}. The UI shows links as buttons under the message: "View 12 loan payments" opens the transaction
panel with that filter; "See forecast" scrolls to the forecast; "Compare with everyone" opens Portfolio
(Power BI iframe if VITE_POWERBI_URL is set). If a scenario was run, also update the runway numbers and coin
stack on the page so the chat and the visuals agree.
Fallback when Gemini errors or times out (8 s): keyword router for the common questions (balance, bills,
loan, "can I afford $X", "what if I lose my job") using the same tools, with a small note "simple mode".
Abuse limits: 20 chat requests per IP per 10 minutes (in-memory), reject >500 chars, ignore instructions
inside user text that try to change account_id or rules.
Suggested-question chips above the box (5 of them, including one lifestyle one); the twist cards stay.

## 3. Tests and checks (show output)
- Unit tests with Gemini mocked: tool binding (cannot read another account), grounded-number check, fallback
  router answers "can I afford a $400 car payment" via run_scenario(rent_up=400), rate limit, length limit.
- One live test only if RUN_GEMINI=1.
- Manual: account 63816, ask the 6 example questions above; paste the answers in your summary and mark any
  answer whose numbers you could not trace to a tool result.
- npm run build passes; check 390 px and 1280 px. Twist 3 on 63816 still shows Judge 3.1, Realistic 1.9.
