import { useEffect, useState } from "react";
import { getPortfolio } from "../api.js";
import { C } from "../theme.js";

// Set VITE_POWERBI_URL at build time to embed the published report; unset = native summary only.
const POWERBI_URL = (import.meta.env.VITE_POWERBI_URL || "").trim();
const SEG = { Stable: C.positive, "Hidden fragile": C.accent, Fragile: C.fragile, "Already short": C.negative };
const SEG_TEXT = { Stable: "would be fine", "Hidden fragile": "look fine but aren't", Fragile: "would struggle", "Already short": "have no savings left" };

export default function PowerBIPanel() {
  const [d, setD] = useState(null);
  useEffect(() => { getPortfolio().then(setD).catch(() => setD(null)); }, []);
  const total = d ? Object.values(d.segments).reduce((a, b) => a + b, 0) : 0;
  return (
    <section aria-label="How everyone compares" className="space-y-4">
      <h2 className="display text-2xl">How everyone compares</h2>
      {POWERBI_URL ? (
        <iframe title="ServaAI Power BI report" src={POWERBI_URL} allowFullScreen loading="lazy"
                className="h-[600px] w-full rounded-md border border-line bg-paper" />
      ) : d && (
        <div className="space-y-3">
          <p className="max-w-[62ch] text-[17px]">
            If they lost their job, out of {total.toLocaleString()} customers:
          </p>
          <div className="flex h-3 w-full overflow-hidden rounded-full">
            {Object.entries(d.segments).map(([s, n]) => <div key={s} style={{ width: `${(n / total) * 100}%`, background: SEG[s] }} />)}
          </div>
          <ul className="grid gap-2 sm:grid-cols-2">
            {Object.entries(d.segments).map(([s, n]) => (
              <li key={s} className="flex items-center gap-2">
                <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: SEG[s] }} />
                <span><span className="font-medium tabular-nums">{Math.round((n / total) * 100)}%</span> {SEG_TEXT[s]}</span>
              </li>
            ))}
          </ul>
          <a href="#/portfolio" className="inline-block text-accent-ink underline underline-offset-4">Explore every customer</a>
        </div>
      )}
    </section>
  );
}
