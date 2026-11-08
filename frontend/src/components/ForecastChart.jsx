import { Area, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { C } from "../theme.js";
import { money } from "../api.js";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const label = (ym) => `${MONTHS[Number(ym.slice(5, 7)) - 1]} ${ym.slice(0, 4)}`;

export default function ForecastChart({ f }) {
  const data = [
    { m: label(f.start_month), base: f.start_balance, band: [f.start_balance, f.start_balance], shocked: f.shocked ? f.start_balance : undefined },
    ...f.months.map((m, i) => ({ m: label(m), base: f.base[i], band: [f.p10[i], f.p90[i]], shocked: f.shocked?.[i] })),
  ];
  const lowest = Math.min(...(f.shocked ?? f.base));
  return (
    <section aria-label="Next 3 months">
      <div className="flex flex-wrap items-baseline gap-x-4">
        <h2 className="display text-xl">Next 3 months</h2>
        <p className="text-sm text-muted">
          Month-end balance. Band shows the likely range (P10 to P90 from our 2025 backtest).
        </p>
      </div>
      <div className="mt-3 h-64 w-full">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
            <XAxis dataKey="m" stroke={C.muted} tickLine={false} axisLine={false} fontSize={13} />
            <YAxis stroke={C.muted} tickLine={false} axisLine={false} fontSize={13} width={72}
                   tickFormatter={(v) => money(v)} />
            <Tooltip contentStyle={{ background: C.paper, border: `1px solid ${C.line}`, borderRadius: 8, color: C.stone }}
                     formatter={(v, name) => [Array.isArray(v) ? `${money(v[0])} to ${money(v[1])}` : money(v),
                       { base: "If nothing changes", band: "Likely range", shocked: "After the event" }[name]]} />
            <Area dataKey="band" stroke="none" fill={C.accentSoft} fillOpacity={0.7} isAnimationActive={false} />
            <ReferenceLine y={0} stroke={C.line} strokeDasharray="4 4" />
            <Line dataKey="base" stroke={C.stone} strokeWidth={1.5} dot={{ r: 2.5, fill: C.stone }} isAnimationActive={false} />
            {f.shocked && <Line dataKey="shocked" stroke={C.accent} strokeWidth={2}
                                dot={{ r: 3, fill: C.accent }} isAnimationActive={false} />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-sm text-muted">
        Grey: if nothing changes. {f.shocked && <>Tangerine: after the event{lowest < 0 && <>, <span className="text-negative-ink">dropping below zero to {money(lowest)}</span></>}.</>}
        {" "}Model: {f.model === "xgboost" ? "XGBoost, 12.6% more accurate than assuming no change" : f.model}.
      </p>
    </section>
  );
}
