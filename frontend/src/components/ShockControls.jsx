function Slider({ id, label, value, min, max, step, fmt, onChange, disabled }) {
  return (
    <div className={disabled ? "opacity-40" : ""}>
      <div className="flex justify-between text-sm"><label htmlFor={id}>{label}</label><span className="tabular-nums text-mist">{fmt(value)}</span></div>
      <input id={id} type="range" min={min} max={max} step={step} value={value} disabled={disabled}
             onChange={(e) => onChange(Number(e.target.value))} className="w-full" />
    </div>
  );
}

export const EMPTY = { ei_pct: null, bills_up_pct: 0, rent_up: 0, repair_months: 0, one_off: 0, ei_cap: true, reemploy_month: null };

export default function ShockControls({ shock, setShock, onApply, busy }) {
  const set = (k) => (v) => setShock({ ...shock, [k]: v });
  const jobLoss = shock.ei_pct !== null;
  return (
    <section aria-label="Fine-tune the event">
      <h2 className="display text-xl">Fine-tune</h2>
      <div className="mt-3 space-y-4">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={jobLoss} onChange={(e) => set("ei_pct")(e.target.checked ? 0.55 : null)} />
          Job loss with EI
        </label>
        <Slider id="ei" label="EI pays" value={Math.round((shock.ei_pct ?? 0.55) * 100)} min={0} max={100} step={5}
                fmt={(v) => `${v}% of income`} onChange={(v) => set("ei_pct")(v / 100)} disabled={!jobLoss} />
        <Slider id="bills" label="Household bills up" value={Math.round(shock.bills_up_pct * 100)} min={0} max={50} step={1}
                fmt={(v) => `${v}%`} onChange={(v) => set("bills_up_pct")(v / 100)} />
        <Slider id="rent" label="Rent up" value={shock.rent_up} min={0} max={1000} step={25}
                fmt={(v) => `$${v}/month`} onChange={set("rent_up")} />
        <Slider id="repair" label="Repair costing" value={shock.repair_months} min={0} max={6} step={0.5}
                fmt={(v) => `${v} months of spending`} onChange={set("repair_months")} />
        <Slider id="oneoff" label="Scam or one-off cost" value={shock.one_off} min={0} max={20000} step={250}
                fmt={(v) => `$${v.toLocaleString("en-CA")}`} onChange={set("one_off")} />
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={shock.ei_cap} onChange={(e) => set("ei_cap")(e.target.checked)} />
            EI weekly cap ($729)
          </label>
          <label className="flex items-center gap-2">
            New job in month
            <input type="number" min={1} max={120} value={shock.reemploy_month ?? ""} placeholder="none"
                   onChange={(e) => set("reemploy_month")(e.target.value ? Number(e.target.value) : null)}
                   className="w-20 rounded border border-line bg-deepwater px-2 py-0.5" />
          </label>
        </div>
        <div className="flex gap-3">
          <button onClick={() => onApply(shock)} disabled={busy}
                  className="rounded-lg bg-tangerine px-4 py-2 font-semibold text-harbour hover:bg-peel disabled:opacity-60">
            Recalculate
          </button>
          <button onClick={() => { setShock(EMPTY); onApply(EMPTY); }} disabled={busy}
                  className="rounded-lg border border-line px-4 py-2 text-mist hover:text-frost">
            Clear event
          </button>
        </div>
      </div>
    </section>
  );
}
