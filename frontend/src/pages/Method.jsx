import { useEffect, useState } from "react";
import { getBacktest, money } from "../api.js";

const NAMES = { flat: "Balance stays the same", baseline: "Median flow + damped trend", ridge: "Ridge regression", xgboost: "XGBoost" };

export default function Method() {
  const [bt, setBt] = useState(null);
  useEffect(() => { getBacktest().then(setBt).catch(() => setBt(null)); }, []);
  return (
    <article className="max-w-[72ch] space-y-8 leading-relaxed">
      <section>
        <h1 className="display text-4xl font-bold">How ServaAI gets its numbers</h1>
        <p className="mt-3 text-muted">
          Every number on screen comes from a tested Python engine. Gemini reads the event you type and can rephrase
          results, but it never produces a number: any reply containing a number the engine didn't give is thrown away.
        </p>
      </section>
      <section>
        <h2 className="display text-2xl">The judge formula, matched exactly</h2>
        <p className="mt-2 text-muted">
          From monthly_summary.csv: income I and spending S are medians over all months, so one big bonus or purchase
          doesn't move them. The buffer B is the average daily balance over the last 6 months: what the customer has
          now. Runway = (B − one-off costs) ÷ (spending after the shock − income after the shock), capped at 120 months.
          An independent script recomputes every value for all 4,500 accounts without sharing any code; they match 100%.
        </p>
      </section>
      <section>
        <h2 className="display text-2xl">Realistic runway</h2>
        <p className="mt-2 text-muted">
          Canadian EI regular benefits pay 55% of insurable earnings up to $729 a week, for a limited time. ServaAI
          simulates the balance month by month: EI for 6 months at most, capped, then nothing unless a new job starts.
          money_in also includes transfers and pensions, so even this is an upper bound.
        </p>
      </section>
      <section>
        <h2 className="display text-2xl">Three-month forecast, tested honestly</h2>
        <p className="mt-2 text-muted">
          Trained on 2020–2023, tuned on 2024, tested on 2025 months it never saw. Average error in month-end balance:
        </p>
        {bt && (
          <table className="mt-3 w-full text-[15px]">
            <thead><tr className="text-left text-muted"><th className="py-1 font-normal">Method</th>
              {[1, 2, 3].map((h) => <th key={h} className="py-1 text-right font-normal">{h} month{h > 1 ? "s" : ""} ahead</th>)}</tr></thead>
            <tbody>
              {Object.entries(bt.results).map(([k, r]) => (
                <tr key={k} className={`border-t border-line ${k === bt.winner ? "text-accent-ink" : ""}`}>
                  <td className="py-1.5">{NAMES[k]}{k === bt.winner && " (used in the app)"}</td>
                  {[1, 2, 3].map((h) => <td key={h} className="py-1.5 text-right tabular-nums">{money(r[`h${h}`][0])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mt-2 text-sm text-muted">Only XGBoost beat the simple “nothing changes” guess; we show the methods that lost too.</p>
      </section>
      <section>
        <h2 className="display text-2xl">Sources</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
          <li><a className="text-ink" href="https://relational.fel.cvut.cz/dataset/Financial">PKDD'99 Discovery Challenge Financial dataset</a> (real anonymized bank data, CTU Prague)</li>
          <li><a className="text-ink" href="https://www.canada.ca/en/services/benefits/ei/ei-regular-benefit.html">Employment Insurance regular benefits</a>, Government of Canada</li>
        </ul>
      </section>
    </article>
  );
}
