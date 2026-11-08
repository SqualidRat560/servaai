import { useEffect, useState } from "react";
import { getStatement, money } from "../api.js";

const FILTERS = [["", "All"], ["in", "Money in"], ["out", "Money out"]];
const fmtDate = (d) => new Date(`${d}T12:00:00`).toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });

function Loan({ loan }) {
  const paid = Math.min(loan.paid_to_date / loan.amount, 1);
  return (
    <div className="rounded-md border border-line p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="display text-lg">Loan</h3>
        <span className="text-sm text-muted">{loan.status_meaning}</span>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-raised" role="img"
           aria-label={`About ${Math.round(paid * 100)}% paid`}>
        <div className="h-full bg-accent" style={{ width: `${paid * 100}%` }} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-[15px] sm:grid-cols-4">
        <div><dt className="text-sm text-muted">Paid so far</dt><dd className="m-0 tabular-nums">{money(loan.paid_to_date)}</dd></div>
        <div><dt className="text-sm text-muted">Remaining (estimate)</dt><dd className="m-0 tabular-nums">{money(loan.remaining)}</dd></div>
        <div><dt className="text-sm text-muted">Monthly payment</dt><dd className="m-0 tabular-nums">{money(loan.monthly_payment, 2)}</dd></div>
        <div><dt className="text-sm text-muted">Borrowed</dt><dd className="m-0 tabular-nums">{money(loan.amount)} over {loan.duration_months} months</dd></div>
      </dl>
      <p className="mt-2 text-xs text-muted">{loan.estimate_note}</p>
    </div>
  );
}

export default function AccountView({ accountId }) {
  const [head, setHead] = useState(null);
  const [rows, setRows] = useState([]);
  const [next, setNext] = useState(null);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load(reset, dir = filter) {
    setLoading(true); setError("");
    try {
      const d = await getStatement(accountId, { limit: 6, before: reset ? undefined : next, direction: dir || undefined });
      if (reset) setHead(d);
      setRows((r) => (reset ? d.transactions : [...r, ...d.transactions]));
      setNext(d.has_more ? d.next_before : null);
    } catch (e) { setError(e.message); }
    setLoading(false);
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { setFilter(""); load(true, ""); }, [accountId]);

  if (error && !head) return <p className="text-negative-ink">{error}</p>;
  if (!head) return <p className="text-muted">Loading the account…</p>;

  return (
    <section aria-label="My account" className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="display text-2xl">My account</h2>
          <p className="text-sm text-muted">Account {head.account_id}</p>
        </div>
        <div className="text-right">
          <div className="text-sm text-muted">Balance at the end of {head.balance_as_of}</div>
          <div className={`numeral text-5xl ${head.balance < 0 ? "text-negative-ink" : ""}`}>{money(head.balance, 2)}</div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        {head.loan ? <Loan loan={head.loan} /> : <div className="rounded-md border border-line p-4 text-muted">No loan on this account.</div>}
        <div className="rounded-md border border-line p-4">
          <h3 className="display text-lg">Cards</h3>
          {head.cards.length === 0 ? <p className="mt-2 text-muted">No card on this account.</p> : (
            <ul className="mt-2 space-y-1">
              {head.cards.map((c) => (
                <li key={`${c.card_type}${c.issued}`}><span className="capitalize">{c.card_type}</span> card <span className="text-muted">issued {fmtDate(c.issued)}</span></li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="display text-lg">Transactions</h3>
          <div role="group" aria-label="Filter transactions" className="flex overflow-hidden rounded-md border border-line text-sm">
            {FILTERS.map(([k, label]) => (
              <button key={k || "all"} aria-pressed={filter === k}
                      onClick={() => { setFilter(k); load(true, k); }}
                      className={`px-3 py-1.5 ${filter === k ? "bg-raised font-medium" : "text-muted hover:text-ink"}`}>{label}</button>
            ))}
          </div>
        </div>
        <ul className="mt-2 divide-y divide-line border-y border-line">
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
        <p className="mt-1 hidden text-right text-xs text-muted sm:block">Right column: balance at the end of that day.</p>
        {error && <p className="mt-2 text-negative-ink">{error}</p>}
        {next && (
          <button onClick={() => load(false)} disabled={loading}
                  className="mt-3 rounded-md border border-line px-4 py-2 hover:bg-raised disabled:opacity-60">
            {loading ? "Loading…" : "Load more"}
          </button>
        )}
      </div>
    </section>
  );
}
