import { money } from "../api.js";

export default function PlanList({ plan }) {
  const g = plan.goal, b = plan.backup;
  const pct = (x) => (x === null ? "n/a" : `${Math.min(Math.round(x * 100), 999)}%`);
  return (
    <section aria-label="The plan">
      <h2 className="display text-xl">The plan</h2>
      <p className="mt-2 max-w-[62ch] text-mist">
        Emergency fund: {money(g.target_3_months)} covers 3 months of typical spending ({pct(g.progress_3)} there today),
        {" "}{money(g.target_6_months)} covers 6 ({pct(g.progress_6)}).
      </p>
      {b.cuts.length > 0 ? (
        <div className="mt-4 border-l-2 border-tangerine pl-4">
          <p className="font-semibold">Backup plan if this happens</p>
          <ul className="mt-1 space-y-1 text-[15px]">
            {b.cuts.map((c) => (
              <li key={c.category}>Cut {c.label} by {money(c.cut)} a month ({Math.round(c.cut_pct * 100)}%).</li>
            ))}
          </ul>
          <p className="mt-2 text-[15px]">
            That frees {money(b.monthly_savings)} a month and stretches the realistic runway from {b.runway_before.label} to
            {" "}<span className="text-peel">{b.runway_after.label}</span>
            {!b.reached_target && " (still short of 3 months even with every flexible cost halved)"}.
          </p>
        </div>
      ) : (
        <p className="mt-4 border-l-2 border-line pl-4 text-[15px] text-mist">No spending cuts needed under this event ({b.runway_before.label}).</p>
      )}
      <ul className="mt-5 space-y-3">
        {plan.tools.map((t) => (
          <li key={t.tool} className="max-w-[70ch] text-[15px]">
            <span className="font-semibold text-frost">{t.tool}.</span> <span className="text-mist">{t.action}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
