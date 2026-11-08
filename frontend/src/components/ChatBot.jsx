import { useEffect, useRef, useState } from "react";
import { advise, askMoney, parseEvent, speakText } from "../api.js";

// Free-form questions go to the tool-using assistant. The twist cards keep the confirm-first flow.
const QUESTIONS = [
  "How much do I spend on bills?",
  "Can I afford a $400 car payment?",
  "If I join a $60 gym, how long does my buffer last if I lose my job?",
  "Where did my money go in March?",
  "What happens if I buy a $1,500 laptop?",
];
const TWIST_CARDS = [
  { title: "Laid off, EI at 55%", text: "This customer was laid off. EI pays 55% of their usual income for 6 months." },
  { title: "Furnace repair", text: "The furnace dies, and the repair costs a full month of their typical spending." },
  { title: "Job loss and bills up 15%", text: "They lose their job (EI at 55%) and their household bills go up 15% in the same month." },
  { title: "Scam", text: "I got scammed out of $1,500" },
  { title: "Rent hike", text: "My rent went up $300" },
  { title: "Bills up 10%", text: "Household bills up 10%" },
  { title: "Car repair", text: "The car repair is $1,200" },
  { title: "New job in month 4", text: "Laid off with EI at 55%, but I start a new job in month 4" },
];

const months = (v) => (v === null || v === undefined ? "more than 10 years" : `${v.toFixed(1)} months`);
const Recognition = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

function Outcome({ m, onListen }) {
  const f = m.facts;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 border-y border-line py-3">
        <div><div className="text-xs text-muted">Judge formula</div><div className="numeral text-3xl">{months(f.judge_runway_months)}</div></div>
        <div><div className="text-xs text-accent-ink">Realistic, with EI limits</div><div className="numeral text-3xl">{months(f.realistic_runway_months)}</div></div>
      </div>
      <p>{m.summary}</p>
      <div>
        <p className="font-medium">Things you could do</p>
        <ul className="mt-1 list-disc space-y-1 pl-5">{m.suggestions.map((s) => <li key={s}>{s}</li>)}</ul>
      </div>
      <button onClick={() => onListen(`${m.summary} ${m.suggestions.join(" ")}`)} className="text-sm text-accent-ink underline underline-offset-4">Listen</button>
    </div>
  );
}

export default function ChatBot({ accountId, onApplied, onLink }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const endRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => { setMessages([{ role: "bot", text: "Hi! Ask me anything about your money: bills, your loan, what a purchase would do, or what happens if you lose your job. I only read your own numbers." }]); }, [accountId]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [messages]);

  const push = (m) => setMessages((all) => [...all, m]);

  // the conversation sent to the server: plain text turns only, the last 8
  const turns = (extra) => [...messages, extra]
    .filter((m) => m.text || m.summary)
    .map((m) => ({ role: m.role === "user" ? "user" : "assistant", content: (m.text || m.summary).slice(0, 500) }))
    .slice(-8);

  async function ask(t = text) {
    if (!t.trim() || busy) return;
    const mine = { role: "user", text: t };
    setText(""); push(mine); setBusy(true);
    try {
      const d = await askMoney(accountId, turns(mine));
      push({ role: "bot", kind: "answer", text: d.text, links: d.links, source: d.source, note: d.note, tools: d.used_tools });
      if (d.scenario) onApplied?.(d.scenario);  // the runway numbers and coin stack follow the chat
    } catch (e) { push({ role: "bot", text: e.message, error: true }); }
    setBusy(false);
  }

  async function twist(t) {
    if (busy) return;
    push({ role: "user", text: t }); setBusy(true);
    try {
      const d = await parseEvent(t);
      if (d.chip.length) push({ role: "bot", kind: "confirm", chip: d.chip, shock: d.shock, notes: d.notes });
      else push({ role: "bot", text: "I couldn't find a money event in that. Try “I lost my job” or “rent went up $200”." });
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
      const url = await speakText(t);
      audioRef.current?.pause(); audioRef.current = new Audio(url); audioRef.current.play();
    } catch {
      if ("speechSynthesis" in window) { window.speechSynthesis.cancel(); window.speechSynthesis.speak(new SpeechSynthesisUtterance(t)); }
    }
  }

  function talk() {
    if (!Recognition) return;
    const r = new Recognition(); r.lang = "en-CA"; r.interimResults = false;
    r.onresult = (e) => ask(e.results[0][0].transcript);
    r.onend = () => setListening(false);
    setListening(true); r.start();
  }

  return (
    <section aria-label="Chat with ServaAI" className="flex min-w-0 flex-col rounded-md border border-line bg-paper">
      <div className="max-h-[560px] min-h-[260px] space-y-4 overflow-y-auto p-4" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
            <div className={`max-w-[92%] rounded-md px-4 py-3 ${m.role === "user" ? "bg-accent-soft" : "border border-line bg-raised"} ${m.error ? "text-negative-ink" : ""}`}>
              {m.text && <p className="whitespace-pre-line">{m.text}</p>}
              {m.kind === "answer" && (
                <div className="mt-2 space-y-2">
                  {m.links?.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {m.links.map((l) => (
                        <button key={l.label} onClick={() => onLink?.(l)}
                                className="rounded-md border border-accent-ink px-3 py-1 text-sm text-accent-ink hover:bg-accent-soft">{l.label}</button>
                      ))}
                    </div>
                  )}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
                    <button onClick={() => listen(m.text)} className="text-sm text-accent-ink underline underline-offset-4">Listen</button>
                    {m.source === "simple" && <span>Simple mode: Gemini was unavailable, so this answer uses keyword matching on your own numbers.</span>}
                    {m.source === "template" && <span>Shown as a plain summary of your data.</span>}
                  </div>
                </div>
              )}
              {m.kind === "confirm" && (
                <div className="space-y-2">
                  <p>Here's what I understood. Is that right?</p>
                  <div className="flex flex-wrap gap-2">{m.chip.map((c) => <span key={c} className="rounded-full border border-accent bg-paper px-3 py-0.5 text-[15px]">{c}</span>)}</div>
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
              {m.kind === "outcome" && <Outcome m={m} onListen={listen} />}
            </div>
          </div>
        ))}
        {busy && <p className="text-sm text-muted">ServaAI is working it out…</p>}
        <div ref={endRef} />
      </div>

      <div className="space-y-2 border-t border-line p-3">
        <div>
          <p className="mb-1 text-xs text-muted">Ask</p>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {QUESTIONS.map((q) => (
              <button key={q} onClick={() => ask(q)} disabled={busy}
                      className="shrink-0 rounded-full border border-line px-3 py-1 text-sm hover:border-accent hover:bg-raised disabled:opacity-60">{q}</button>
            ))}
          </div>
        </div>
        <div>
          <p className="mb-1 text-xs text-muted">Or try a twist card</p>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {TWIST_CARDS.map((c) => (
              <button key={c.title} onClick={() => twist(c.text)} disabled={busy} title={c.text}
                      className="shrink-0 rounded-full border border-line px-3 py-1 text-sm hover:border-accent hover:bg-raised disabled:opacity-60">{c.title}</button>
            ))}
          </div>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); ask(); }} className="flex gap-2">
          <label htmlFor="chat-input" className="sr-only">Ask about your money</label>
          <input id="chat-input" value={text} maxLength={500} onChange={(e) => setText(e.target.value)} disabled={busy}
                 placeholder="Should I pay down my loan or save?"
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
