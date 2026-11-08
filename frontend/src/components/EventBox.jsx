import { useState } from "react";
import { parseEvent } from "../api.js";

const CARDS = [
  "This customer was laid off. EI pays 55% of their usual income for 6 months.",
  "The furnace dies, and the repair costs a full month of their typical spending.",
  "They lose their job (EI at 55%) and their household bills go up 15% in the same month.",
];

export default function EventBox({ onApply, busy }) {
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState(null);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState("");

  async function read(t = text) {
    if (!t.trim()) return;
    setReading(true); setError(""); setParsed(null);
    try { setParsed(await parseEvent(t)); } catch (e) { setError(e.message); }
    setReading(false);
  }

  return (
    <section aria-label="What happened">
      <label htmlFor="event" className="display mb-2 block text-xl">What happened?</label>
      <div className="flex gap-2">
        <input id="event" value={text} onChange={(e) => setText(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && read()}
               placeholder="Lost my job, EI pays 55%. Rent went up $200."
               className="min-w-0 flex-1 rounded-lg border border-line bg-paper px-3 py-2.5 text-ink placeholder:text-muted/70" />
        <button onClick={() => read()} disabled={reading}
                className="rounded-lg border border-accent px-4 font-semibold text-accent-ink hover:bg-accent hover:text-ink disabled:opacity-60">
          {reading ? "Reading" : "Read"}
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
        Twist cards:
        {CARDS.map((c, i) => (
          <button key={i} onClick={() => { setText(c); read(c); }} title={c}
                  className="text-muted underline decoration-line underline-offset-4 hover:text-ink">
            card {i + 1}
          </button>
        ))}
      </div>

      {error && <p className="mt-3 text-negative-ink">{error}</p>}
      {parsed && (
        <div className="mt-4">
          {parsed.chip.length === 0
            ? <p className="text-muted">No money event found in that sentence. Try “lost my job” or “rent up $200”.</p>
            : (
              <div className="flex flex-wrap items-center gap-2">
                {parsed.chip.map((c) => (
                  <span key={c} className="rounded-full bg-accent-soft px-3 py-1 text-[15px] text-accent-ink ring-1 ring-accent/50">{c}</span>
                ))}
                <button onClick={() => onApply(parsed.shock)} disabled={busy}
                        className="rounded-lg bg-accent px-4 py-1.5 font-semibold text-ink hover:bg-accent-soft disabled:opacity-60">
                  Apply
                </button>
              </div>
            )}
          <p className="mt-2 text-xs text-muted">
            Read by {parsed.source === "rules" ? "the built-in parser (Gemini unavailable)" : `Gemini (${parsed.model})`}.
            {parsed.notes.length > 0 && ` ${parsed.notes.join(". ")}.`} Numbers come from the engine, not the AI.
          </p>
        </div>
      )}
    </section>
  );
}
