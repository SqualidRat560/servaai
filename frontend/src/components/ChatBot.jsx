import { useEffect, useRef, useState } from "react";
import { advise, chat, speakText } from "../api.js";

const STARTERS = [
  { title: "I lost my job", text: "This customer was laid off. EI pays 55% of their usual income for 6 months." },
  { title: "Furnace broke", text: "The furnace dies, and the repair costs a full month of their typical spending." },
  { title: "Job loss and higher bills", text: "They lose their job (EI at 55%) and their household bills go up 15% in the same month." },
  { title: "I was scammed", text: "I got scammed out of $1,500" },
  { title: "Rent went up", text: "My rent went up $300" },
  { title: "Bills up 10%", text: "Household bills up 10%" },
  { title: "Car repair", text: "The car repair is $1,200" },
  { title: "New job in month 4", text: "Laid off with EI at 55%, but I start a new job in month 4" },
  { title: "How can I save more?", text: "How can I save more each month?" },
];

const months = (v) => (v === null || v === undefined ? "more than 10 years" : `${v.toFixed(1)} months`);
const Recognition = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

function Outcome({ m, onListen }) {
  const f = m.facts;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 border-y border-line py-3">
        <div>
          <div className="text-xs text-muted">Judge formula</div>
          <div className="numeral text-3xl">{months(f.judge_runway_months)}</div>
        </div>
        <div>
          <div className="text-xs text-accent-ink">Realistic, with EI limits</div>
          <div className="numeral text-3xl">{months(f.realistic_runway_months)}</div>
        </div>
      </div>
      <p>{m.summary}</p>
      <div>
        <p className="font-medium">Things you could do</p>
        <ul className="mt-1 list-disc space-y-1 pl-5">
          {m.suggestions.map((s) => <li key={s}>{s}</li>)}
        </ul>
      </div>
      <button onClick={() => onListen(`${m.summary} ${m.suggestions.join(" ")}`)}
              className="text-sm text-accent-ink underline underline-offset-4">Listen</button>
    </div>
  );
}

export default function ChatBot({ accountId, onApplied }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const endRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => { setMessages([{ role: "bot", text: "Hi! Tell me what's happening in your life, or ask how to save more. I'll show how long your money would last and what you could change." }]); }, [accountId]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [messages]);

  const push = (m) => setMessages((all) => [...all, m]);

  async function send(t = text) {
    if (!t.trim() || busy) return;
    setText(""); push({ role: "user", text: t }); setBusy(true);
    try {
      const d = await chat(accountId, t);
      if (d.kind === "event") push({ role: "bot", kind: "confirm", chip: d.chip, shock: d.shock, notes: d.notes });
      else push({ role: "bot", kind: "answer", summary: d.summary, suggestions: d.suggestions });
    } catch (e) { push({ role: "bot", text: e.message, error: true }); }
    setBusy(false);
  }

  async function confirm(shock, i) {
    setMessages((all) => all.map((m, j) => (j === i ? { ...m, done: true } : m)));
    push({ role: "user", text: "Yes, that's right." }); setBusy(true);
    try {
      const [d] = await Promise.all([advise(accountId, shock), onApplied?.(shock)]);
      push({ role: "bot", kind: "outcome", ...d });
    } catch (e) { push({ role: "bot", text: e.message, error: true }); }
    setBusy(false);
  }

  async function listen(t) {
    try {
      const url = await speakText(t);  // ElevenLabs when configured on the server
      audioRef.current?.pause(); audioRef.current = new Audio(url); audioRef.current.play();
    } catch {
      if ("speechSynthesis" in window) { window.speechSynthesis.cancel(); window.speechSynthesis.speak(new SpeechSynthesisUtterance(t)); }
    }
  }

  function talk() {
    if (!Recognition) return;
    const r = new Recognition(); r.lang = "en-CA"; r.interimResults = false;
    r.onresult = (e) => { const said = e.results[0][0].transcript; setText(said); send(said); };
    r.onend = () => setListening(false);
    setListening(true); r.start();
  }

  return (
    <section aria-label="Chat with ServaAI" className="flex min-w-0 flex-col rounded-md border border-line bg-paper">
      <div className="max-h-[540px] min-h-[260px] space-y-4 overflow-y-auto p-4" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
            <div className={`max-w-[92%] rounded-md px-4 py-3 ${m.role === "user" ? "bg-accent-soft" : "border border-line bg-raised"} ${m.error ? "text-negative-ink" : ""}`}>
              {m.text && <p>{m.text}</p>}
              {m.kind === "confirm" && (
                <div className="space-y-2">
                  <p>Here's what I understood. Is that right?</p>
                  <div className="flex flex-wrap gap-2">
                    {m.chip.map((c) => <span key={c} className="rounded-full border border-accent bg-paper px-3 py-0.5 text-[15px]">{c}</span>)}
                  </div>
                  {m.notes?.length > 0 && <p className="text-xs text-muted">{m.notes.join(". ")}.</p>}
                  {!m.done && (
                    <div className="flex gap-2 pt-1">
                      <button onClick={() => confirm(m.shock, i)} disabled={busy}
                              className="rounded-md bg-accent px-3 py-1.5 font-medium text-ink hover:bg-accent-soft disabled:opacity-60">Yes, show me</button>
                      <button onClick={() => setMessages((all) => all.map((x, j) => (j === i ? { ...x, done: true } : x)).concat({ role: "bot", text: "No problem. Tell me again in your own words." }))}
                              className="rounded-md border border-line px-3 py-1.5 hover:bg-paper">Not quite</button>
                    </div>
                  )}
                </div>
              )}
              {m.kind === "answer" && (
                <div className="space-y-2">
                  <p>{m.summary}</p>
                  <ul className="list-disc space-y-1 pl-5">{m.suggestions.map((s) => <li key={s}>{s}</li>)}</ul>
                  <button onClick={() => listen(`${m.summary} ${m.suggestions.join(" ")}`)} className="text-sm text-accent-ink underline underline-offset-4">Listen</button>
                </div>
              )}
              {m.kind === "outcome" && <Outcome m={m} onListen={listen} />}
            </div>
          </div>
        ))}
        {busy && <p className="text-sm text-muted">ServaAI is thinking…</p>}
        <div ref={endRef} />
      </div>

      <div className="border-t border-line p-3">
        <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
          {STARTERS.map((s) => (
            <button key={s.title} onClick={() => send(s.text)} disabled={busy}
                    className="shrink-0 rounded-full border border-line px-3 py-1 text-sm hover:border-accent hover:bg-raised disabled:opacity-60">{s.title}</button>
          ))}
        </div>
        <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2">
          <label htmlFor="chat-input" className="sr-only">Message</label>
          <input id="chat-input" value={text} onChange={(e) => setText(e.target.value)} disabled={busy}
                 placeholder="My hydro bill went up 20% and I lost my job"
                 className="min-w-0 flex-1 rounded-md border border-line bg-paper px-3 py-2.5 placeholder:text-muted/70" />
          {Recognition && (
            <button type="button" onClick={talk} aria-pressed={listening} title="Speak"
                    className={`rounded-md border px-3 ${listening ? "border-accent bg-accent-soft" : "border-line hover:bg-raised"}`}>
              {listening ? "Listening…" : "Speak"}
            </button>
          )}
          <button disabled={busy || !text.trim()} className="rounded-md bg-accent px-4 font-medium text-ink hover:bg-accent-soft disabled:opacity-60">Send</button>
        </form>
      </div>
    </section>
  );
}
