import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
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
        <p className="text-sm text-mist">
          Month-end balance. Band shows the likely range (P10 to P90 from our 2025 backtest).
        </p>
      </div>
      <div className="mt-3 h-64 w-full">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="#24407e" strokeOpacity={0.5} vertical={false} />
            <XAxis dataKey="m" stroke="#a9b7d6" tickLine={false} axisLine={false} fontSize={13} />
            <YAxis stroke="#a9b7d6" tickLine={false} axisLine={false} fontSize={13} width={72}
                   tickFormatter={(v) => money(v)} />
            <Tooltip contentStyle={{ background: "#13285A", border: "1px solid #24407e", borderRadius: 8, color: "#E8EEF9" }}
                     formatter={(v, name) => [Array.isArray(v) ? `${money(v[0])} to ${money(v[1])}` : money(v),
                       { base: "If nothing changes", band: "Likely range", shocked: "After the event" }[name]]} />
            <Area dataKey="band" stroke="none" fill="#FFC27A" fillOpacity={0.2} isAnimationActive={false} />
            <ReferenceLine y={0} stroke="#FF6B5B" strokeDasharray="5 5" />
            <Line dataKey="base" stroke="#E8EEF9" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
            {f.shocked && <Line dataKey="shocked" stroke={lowest < 0 ? "#FF6B5B" : "#F28500"} strokeWidth={3}
                                dot={{ r: 4 }} isAnimationActive={false} />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-sm text-mist">
        White: if nothing changes. {f.shocked && <>{lowest < 0 ? <span className="text-overdraft">Red</span> : "Orange"}: after the event{lowest < 0 && `, dropping to ${money(lowest)}`}.</>}
        {" "}Model: {f.model === "xgboost" ? "XGBoost, 12.6% more accurate than assuming no change" : f.model}.
      </p>
    </section>
  );
}
