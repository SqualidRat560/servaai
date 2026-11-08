import { useEffect, useRef, useState } from "react";
import { getCategories, getStatement, money } from "../api.js";

const FILTERS = [["", "All"], ["in", "Money in"], ["out", "Money out"]];
const fmtDate = (d) => new Date(`${d}T12:00:00`).toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
const monthName = (m) => new Date(`${m}-15T12:00:00`).toLocaleDateString("en-CA", { year: "numeric", month: "long" });

export const CLOSED = { open: false, title: "", category: "", purpose: "", month: "", nonce: 0 };

// ---- one labelled, clickable account item
function Item({ title, onClick, children, hint }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag onClick={onClick} className={`w-full rounded-md border border-line p-4 text-left ${onClick ? "hover:border-accent hover:bg-raised" : ""}`}>
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="display text-lg">{title}</h3>
        {onClick && <span className="text-xs text-accent-ink">{hint || "See transactions"}</span>}
      </div>
      {children}
    </Tag>
  );
}

function LoanBody({ loan }) {
  const paid = Math.min(loan.paid_to_date / loan.amount, 1);
  return (
    <>
      <div className="numeral mt-2 text-4xl">{money(loan.remaining)}</div>
      <div className="text-sm text-muted">left to pay (estimate)</div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-raised" role="img" aria-label={`About ${Math.round(paid * 100)}% paid`}>
        <div className="h-full bg-accent" style={{ width: `${paid * 100}%` }} />
      </div>
      <p className="mt-2 text-sm text-muted">
        {money(loan.paid_to_date)} paid · {money(loan.monthly_payment, 2)} a month · {loan.status_meaning}
      </p>
    </>
  );
}

function CategoryList({ title, rows, month, onPick }) {
  return (
    <div>
      <h4 className="mb-1 font-medium">{title}</h4>
      <ul className="divide-y divide-line border-y border-line">
        {rows.map((r) => (
          <li key={r.key}>
            <button onClick={() => onPick(r)} className="flex w-full items-center justify-between gap-3 py-2 text-left hover:bg-raised">
              <span>{r.label}</span>
              <span className="tabular-nums">{money(r.amount, 2)}</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-1 text-xs text-muted">{monthName(month)}. Select a row to see its transactions.</p>
    </div>
  );
}

// ---- the transaction list: an inline panel under the cards (a native <details>, so it is also the plain dropdown)
function TransactionPanel({ accountId, panel, setPanel, months }) {
  const [rows, setRows] = useState([]);
  const [next, setNext] = useState(null);
  const [total, setTotal] = useState(null);
  const [direction, setDirection] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const ref = useRef(null);
  const filter = { category: panel.category, purpose: panel.purpose, month: panel.month };

  async function load(reset, before) {
    setLoading(true); setError("");
    try {
      const d = await getStatement(accountId, { limit: 15, before, direction, ...filter });
      setRows((r) => (reset ? d.transactions : [...r, ...d.transactions]));
      setNext(d.has_more ? d.next_before : null);
      if (reset) setTotal({ n: d.total_matching, amount: d.total_amount });
    } catch (e) { setError(e.message); }
    setLoading(false);
  }

  useEffect(() => { if (panel.open) load(true); },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [accountId, panel.open, panel.category, panel.purpose, panel.month, panel.nonce, direction]);
  useEffect(() => { if (panel.open) ref.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [panel.nonce]); // eslint-disable-line

  const close = () => setPanel((p) => ({ ...p, open: false }));
  return (
    <details ref={ref} open={panel.open} id="transactions"
             onToggle={(e) => setPanel((p) => (p.open === e.currentTarget.open ? p : { ...p, open: e.currentTarget.open }))}
             onKeyDown={(e) => { if (e.key === "Escape") { close(); e.currentTarget.querySelector("summary")?.focus(); } }}
             className="rounded-md border border-line">
      <summary className="cursor-pointer px-4 py-3 font-medium">
        {panel.title || "Transactions"}{panel.month ? `, ${monthName(panel.month)}` : ", all months"}
        {panel.open && total && <span className="font-normal text-muted"> · {total.n.toLocaleString()} {total.n === 1 ? "transaction" : "transactions"}, {money(total.amount, 2)} in total</span>}
      </summary>
      <div className="space-y-3 border-t border-line p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div role="group" aria-label="Filter transactions" className="flex overflow-hidden rounded-md border border-line text-sm">
            {FILTERS.map(([k, label]) => (
              <button key={k || "all"} aria-pressed={direction === k} onClick={() => setDirection(k)}
                      className={`px-3 py-1.5 ${direction === k ? "bg-raised font-medium" : "text-muted hover:text-ink"}`}>{label}</button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm">
            Month
            <select value={panel.month} onChange={(e) => setPanel((p) => ({ ...p, month: e.target.value }))}
                    className="rounded-md border border-line bg-paper px-2 py-1.5">
              <option value="">All months</option>
              {[...months].reverse().map((m) => <option key={m} value={m}>{monthName(m)}</option>)}
            </select>
          </label>
          <button onClick={close} className="ml-auto text-sm text-muted underline underline-offset-4 hover:text-ink">Close (Esc)</button>
        </div>
        {error && <p role="alert" className="text-negative-ink">{error}</p>}
        {rows.length === 0 && !loading && !error && <p className="text-muted">No transactions match these filters.</p>}
        <ul className="divide-y divide-line border-y border-line">
          {rows.map((t) => (
            <li key={t.id} className="grid grid-cols-[1fr_auto] gap-x-4 py-2.5 sm:grid-cols-[8rem_1fr_auto_8rem]">
              <span className="text-sm text-muted sm:text-[15px]">{fmtDate(t.date)}</span>
              <span className="col-start-1 row-start-2 sm:col-start-auto sm:row-start-auto">
                {t.purpose} <span className="text-sm text-muted">({t.operation})</span>
              </span>
              <span className={`row-span-2 self-center text-right tabular-nums sm:row-span-1 ${t.direction === "in" ? "text-positive-ink" : ""}`}>
                {t.direction === "in" ? "+" : "−"}{money(t.amount, 2)}
              </span>
              <span className="hidden text-right text-sm text-muted tabular-nums sm:block">{money(t.day_close_balance, 2)}</span>
            </li>
          ))}
        </ul>
        <p className="hidden text-right text-xs text-muted sm:block">Right column: balance at the end of that day.</p>
        {next && (
          <button onClick={() => load(false, next)} disabled={loading}
                  className="rounded-md border border-line px-4 py-2 hover:bg-raised disabled:opacity-60">
            {loading ? "Loading…" : "Load more"}
          </button>
        )}
      </div>
    </details>
  );
}

export default function AccountView({ accountId, panel, setPanel }) {
  const [head, setHead] = useState(null);
  const [cats, setCats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setHead(null); setCats(null); setError("");
    Promise.all([getStatement(accountId, { limit: 1 }), getCategories(accountId)])
      .then(([h, c]) => { setHead(h); setCats(c); })
      .catch((e) => setError(e.message));
  }, [accountId]);

  const open = (p) => setPanel({ ...CLOSED, ...p, open: true, nonce: Date.now() });
  if (error) return <p className="text-negative-ink">{error}</p>;
  if (!head || !cats) return <p className="text-muted">Loading the account…</p>;

  return (
    <section aria-label="My account" className="space-y-6">
      <div>
        <h2 className="display text-2xl">My account</h2>
        <p className="text-sm text-muted">Account {head.account_id}. Select an item to see the transactions behind it.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Item title="Chequing balance" onClick={() => open({ title: "All transactions" })}>
          <div className={`numeral mt-2 text-4xl ${head.balance < 0 ? "text-negative-ink" : ""}`}>{money(head.balance, 2)}</div>
          <div className="text-sm text-muted">at the end of {monthName(head.balance_as_of)}</div>
        </Item>
        {head.loan
          ? <Item title="Loan" onClick={() => open({ title: "Loan payments", category: "loan_payments" })} hint="See loan payments">
              <LoanBody loan={head.loan} />
            </Item>
          : <Item title="Loan"><p className="mt-2 text-muted">No loan on this account.</p></Item>}
        <Item title="Cards">
          {head.cards.length === 0 ? <p className="mt-2 text-muted">No card on this account.</p> : (
            <ul className="mt-2 space-y-1">
              {head.cards.map((c) => (
                <li key={`${c.card_type}${c.issued}`}><span className="capitalize">{c.card_type}</span> card <span className="text-sm text-muted">issued {fmtDate(c.issued)}</span></li>
              ))}
            </ul>
          )}
        </Item>
      </div>

      {head.loan && <p className="max-w-[70ch] text-xs text-muted">{head.loan.estimate_note}</p>}

      <div>
        <h3 className="display text-lg">Spending by type</h3>
        <div className="mt-2 grid gap-6 md:grid-cols-2">
          <CategoryList title="Money out" rows={cats.out} month={cats.month}
                        onPick={(r) => open({ title: r.label, category: r.key, month: cats.month })} />
          <CategoryList title="Money in" rows={cats.in} month={cats.month}
                        onPick={(r) => open({ title: r.label, category: r.key, month: cats.month })} />
        </div>
      </div>

      <TransactionPanel accountId={accountId} panel={panel} setPanel={setPanel} months={cats.months} />
    </section>
  );
}
