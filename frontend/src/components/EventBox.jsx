import { useState } from "react";
import { parseEvent } from "../api.js";

// The 3 README twist cards first, then 5 phrasings from backend/tests/test_agent.py.
const CARDS = [
  { title: "Laid off, EI at 55%", text: "This customer was laid off. EI pays 55% of their usual income for 6 months." },
  { title: "Furnace repair", text: "The furnace dies, and the repair costs a full month of their typical spending." },
  { title: "Job loss and bills up 15%", text: "They lose their job (EI at 55%) and their household bills go up 15% in the same month." },
  { title: "Scam", text: "I got scammed out of $1,500" },
  { title: "Rent hike", text: "My rent went up $300" },
  { title: "Bills up 10%", text: "Household bills up 10%" },
  { title: "Car repair", text: "The car repair is $1,200" },
  { title: "Job loss, new job in month 4", text: "Laid off with EI at 55%, but I start a new job in month 4" },
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
      <label htmlFor="event" className="display mb-2 block text-2xl">What happened?</label>
      <div className="flex gap-2">
        <input id="event" value={text} onChange={(e) => setText(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && read()}
               placeholder="My hydro bill went up 20% and I lost my job"
               className="min-w-0 flex-1 rounded-md border border-line bg-paper px-3 py-2.5 text-ink placeholder:text-muted/70" />
        <button onClick={() => read()} disabled={reading}
                className="rounded-md border border-accent-ink px-4 font-medium text-accent-ink hover:bg-accent-soft disabled:opacity-60">
          {reading ? "Reading…" : "Read"}
        </button>
      </div>

      <p className="mt-4 mb-2 text-sm text-muted">Or pick a twist card:</p>
      <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {CARDS.map((c) => (
          <li key={c.title}>
            <button onClick={() => { setText(c.text); read(c.text); }} disabled={reading}
                    className="h-full w-full rounded-md border border-line px-3 py-2 text-left hover:border-accent hover:bg-raised disabled:opacity-60">
              <span className="block font-medium">{c.title}</span>
              <span className="block text-sm text-muted">{c.text}</span>
            </button>
          </li>
        ))}
      </ul>

      {error && <p role="alert" className="mt-3 text-negative-ink">{error}</p>}
      {parsed && (
        <div className="mt-5 border-t border-line pt-4">
          {parsed.chip.length === 0
            ? <p className="text-muted">No money event found in that sentence. Try “lost my job” or “rent up $200”.</p>
            : (
              <>
                <p className="mb-2 text-sm text-muted">ServaAI read this. Is it right?</p>
                <div className="flex flex-wrap items-center gap-2">
                  {parsed.chip.map((c) => (
                    <span key={c} className="rounded-full border border-accent bg-accent-soft px-3 py-1 text-[15px]">{c}</span>
                  ))}
                  <button onClick={() => onApply(parsed.shock)} disabled={busy}
                          className="rounded-md bg-accent px-4 py-1.5 font-medium text-ink hover:bg-accent-soft disabled:opacity-60">
                    {busy ? "Working…" : "Yes, apply it"}
                  </button>
                </div>
              </>
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
