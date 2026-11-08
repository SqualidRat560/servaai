import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { getPortfolio } from "../api.js";

const Galaxy = lazy(() => import("../three/Galaxy.jsx"));
export const SEG_COLOR = { Stable: "#5d77b3", "Hidden fragile": "#F28500", Fragile: "#FFC27A", "Already short": "#FF6B5B" };
const SEG_TEXT = {
  Stable: "lasts 6+ months even realistically",
  "Hidden fragile": "the formula says 6+ months, realistically under 6",
  Fragile: "under 6 months by either measure",
  "Already short": "no savings buffer left",
};

function Scatter2D({ points }) {
  const bySeg = useMemo(() => Object.keys(SEG_COLOR).map((s) => ({
    s, pts: points.filter((p) => p.segment === s).map((p) => ({ x: p.judge ?? 120, y: p.realistic ?? 120, id: p.id })),
  })), [points]);
  return (
    <ResponsiveContainer>
      <ScatterChart margin={{ top: 10, right: 10, bottom: 24, left: 4 }}>
        <CartesianGrid stroke="#24407e" strokeOpacity={0.4} />
        <XAxis type="number" dataKey="x" domain={[0, 30]} allowDataOverflow stroke="#a9b7d6" fontSize={12}
               label={{ value: "Judge formula, months", position: "insideBottom", offset: -14, fill: "#a9b7d6" }} />
        <YAxis type="number" dataKey="y" domain={[0, 30]} allowDataOverflow stroke="#a9b7d6" fontSize={12} width={36} />
        <Tooltip cursor={false} contentStyle={{ background: "#13285A", border: "1px solid #24407e", color: "#E8EEF9" }}
                 formatter={(v, n) => [`${Number(v).toFixed(1)} months`, n === "x" ? "Judge" : "Realistic"]} />
        {bySeg.map(({ s, pts }) => <Scatter key={s} data={pts} fill={SEG_COLOR[s]} fillOpacity={0.7} isAnimationActive={false} shape="circle" />)}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export default function Portfolio({ threeD }) {
  const [d, setD] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { getPortfolio().then(setD).catch((e) => setError(e.message)); }, []);
  if (error) return <p className="text-overdraft">{error}</p>;
  if (!d) return <p className="text-mist">Loading 4,500 customers…</p>;

  const h = d.headline.overstated_by_6plus;
  const total = Object.values(d.segments).reduce((a, b) => a + b, 0);
  const pct = (x) => `${(x * 100).toFixed(1)}%`;
  return (
    <div className="space-y-10">
      <section className="max-w-4xl">
        <h1 className="display text-[clamp(2rem,5vw,3.6rem)] leading-[1.02] font-bold">
          For {pct(h.share)} of customers, the standard runway formula is wrong by more than six months.
        </h1>
        <p className="mt-4 max-w-[64ch] text-mist">
          After a job loss with EI at 55%, the formula assumes EI pays forever with no cap. In reality EI stops after
          six months and pays at most $729 a week. Across all {total.toLocaleString()} customers
          (95% interval {pct(h.ci_low)} to {pct(h.ci_high)}),{" "}
          <span className="text-frost">{d.segments["Hidden fragile"].toLocaleString()} look safe but are not</span>.
        </p>
      </section>

      <section aria-label="Segments">
        <div className="flex h-4 w-full overflow-hidden rounded-full">
          {Object.entries(d.segments).map(([s, n]) => (
            <div key={s} style={{ width: `${(n / total) * 100}%`, background: SEG_COLOR[s] }} title={`${s}: ${n}`} />
          ))}
        </div>
        <dl className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-2">
          {Object.entries(d.segments).map(([s, n]) => (
            <div key={s} className="flex gap-3">
              <span className="mt-1.5 h-3 w-3 shrink-0 rounded-full" style={{ background: SEG_COLOR[s] }} />
              <div><dt className="font-semibold">{s}: {n.toLocaleString()} ({pct(n / total)})</dt><dd className="m-0 text-sm text-mist">{SEG_TEXT[s]}</dd></div>
            </div>
          ))}
        </dl>
      </section>

      <section aria-label="Every customer">
        <h2 className="display text-xl">Every customer, judge formula against realistic runway</h2>
        <p className="mt-1 max-w-[64ch] text-sm text-mist">
          {threeD ? "Drag to orbit. Height is the savings buffer. Click a customer to open them." :
            "Points below the diagonal are customers the formula overstates. Axes stop at 30 months."}
        </p>
        <div className="mt-3 h-[520px] w-full overflow-hidden rounded-2xl bg-deepwater/60">
          {threeD
            ? <Suspense fallback={<Scatter2D points={d.points} />}><Galaxy points={d.points} /></Suspense>
            : <Scatter2D points={d.points} />}
        </div>
      </section>
    </div>
  );
}
