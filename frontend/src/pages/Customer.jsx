import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { explain, getAccount, money, runScenario } from "../api.js";
import AccountView from "../components/AccountView.jsx";
import CoinStack2D from "../components/CoinStack2D.jsx";
import EventBox from "../components/EventBox.jsx";
import ForecastChart from "../components/ForecastChart.jsx";
import PlanList from "../components/PlanList.jsx";
import RunwayPair from "../components/RunwayPair.jsx";
import ShockControls, { EMPTY } from "../components/ShockControls.jsx";

const HeroStack = lazy(() => import("../three/HeroStack.jsx"));
const EXAMPLES = [["63816", "typical"], ["32078", "no savings"], ["99477", "account closed early"]];
const isEmpty = (s) => s.ei_pct === null && !s.bills_up_pct && !s.rent_up && !s.repair_months && !s.one_off;

export default function Customer({ initialId, threeD }) {
  const [input, setInput] = useState(initialId || "63816");
  const [profile, setProfile] = useState(null);
  const [shock, setShock] = useState(EMPTY);
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [story, setStory] = useState(null);
  const [showForecast, setShowForecast] = useState(false);
  const outcomeRef = useRef(null);
  const forecastRef = useRef(null);

  const apply = useCallback(async (s, id = profile?.account_id) => {
    if (!id) return;
    setBusy(true); setError(""); setStory(null);
    const full = { ...EMPTY, ...s };
    setShock(full);
    try {
      setData(await runScenario(id, full));
      outcomeRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      if (!isEmpty(full)) {
        setStory({ text: "Writing a plain-English summary…", pending: true });
        explain(id, full).then(setStory).catch((e) => setStory({ text: e.message }));
      }
    } catch (e) { setError(e.message); }
    setBusy(false);
  }, [profile]);

  const lookup = useCallback(async (id) => {
    setBusy(true); setError(""); setStory(null); setShowForecast(false);
    try {
      const a = await getAccount(id.trim());
      setProfile(a.profile);
      window.history.replaceState(null, "", `#/customer/${a.profile.account_id}`);
      setShock(EMPTY);
      setData(await runScenario(a.profile.account_id, EMPTY));
    } catch (e) { setError(e.message); }
    setBusy(false);
  }, []);

  useEffect(() => { lookup(initialId || "63816"); }, [initialId, lookup]);

  function openForecast() {
    setShowForecast(true);
    setTimeout(() => forecastRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  const r = data?.result;
  const backup = data?.plan?.backup?.runway_after;
  const stackProps = r && { judge: r.judge_runway.value, realistic: r.realistic_runway.value, backup: backup?.value };
  const applied = !isEmpty(shock);

  return (
    <div className="space-y-14">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,10fr)_minmax(0,11fr)]">
        <div className="space-y-6">
          <form onSubmit={(e) => { e.preventDefault(); lookup(input); }} className="space-y-2">
            <label htmlFor="acct" className="block text-sm text-muted">Customer account</label>
            <div className="flex gap-2">
              <input id="acct" value={input} inputMode="numeric" onChange={(e) => setInput(e.target.value)}
                     className="w-40 rounded-md border border-line bg-paper px-3 py-2 text-lg tabular-nums" />
              <button className="rounded-md border border-line px-4 hover:bg-raised" disabled={busy}>Look up</button>
            </div>
            <div className="flex flex-wrap gap-x-4 text-sm text-muted">
              {EXAMPLES.map(([id, what]) => (
                <button type="button" key={id} onClick={() => { setInput(id); lookup(id); }}
                        className="underline decoration-line underline-offset-4 hover:text-ink">{id} ({what})</button>
              ))}
            </div>
          </form>
          {profile && (
            <p className="max-w-[58ch] text-[15px] leading-relaxed text-muted">
              In a typical month this customer brings in <span className="text-ink tabular-nums">{money(profile.I)}</span> and
              spends <span className="text-ink tabular-nums">{money(profile.S)}</span>, including fixed costs of {money(profile.F)}
              {profile.P > 0 && <> (a {money(profile.P)} loan payment)</>}. Their savings buffer is
              {" "}<span className={`tabular-nums ${profile.B > 0 ? "text-ink" : "text-negative-ink"}`}>{money(profile.B)}</span>.
              {" "}<a href="#my-account" className="text-accent-ink underline underline-offset-4">See my account</a>
            </p>
          )}
          <figure className="m-0 overflow-hidden rounded-md border border-line bg-raised">
            <div className="h-[300px] sm:h-[380px]">
              {stackProps && (threeD
                ? <Suspense fallback={<div className="h-full p-6"><CoinStack2D {...stackProps} /></div>}><HeroStack {...stackProps} /></Suspense>
                : <div className="h-full p-6"><CoinStack2D {...stackProps} /></div>)}
            </div>
            <figcaption className="border-t border-line px-4 py-3 text-sm text-muted">
              One coin is one month of runway. Solid: realistic. Light: added by the backup plan. Outline: extra months the judge formula promises.
            </figcaption>
          </figure>
        </div>

        <div className="space-y-6">
          <EventBox onApply={(s) => apply(s)} busy={busy} />
          {error && <p role="alert" className="text-negative-ink">{error}</p>}
        </div>
      </div>

      {r && (
        <section ref={outcomeRef} aria-label="Outcome" className="scroll-mt-6 space-y-6 border-t border-line pt-10">
          <h2 className="display text-2xl">{applied ? "What this event does" : "Today, with no event"}</h2>
          <RunwayPair judge={r.judge_runway} realistic={r.realistic_runway} />
          <p className="max-w-[70ch] text-xs text-muted">Judge formula: {r.judge_runway.explanation}</p>
          {story && (
            <p className={`max-w-[62ch] text-[17px] leading-relaxed ${story.pending ? "text-muted" : ""}`}>
              {story.text}
              {story.source === "template" && <span className="text-sm text-muted"> (written from the engine's numbers; Gemini was unavailable)</span>}
            </p>
          )}
          <div className="flex flex-wrap gap-3 pt-2">
            <button onClick={openForecast} className="rounded-md bg-accent px-4 py-2 font-medium text-ink hover:bg-accent-soft">
              See my 3-month forecast
            </button>
            <a href="#/portfolio" className="rounded-md border border-line px-4 py-2 no-underline text-ink hover:bg-raised">
              See how everyone compares
            </a>
          </div>
        </section>
      )}

      {data && showForecast && (
        <div ref={forecastRef} className="scroll-mt-6">
          <ForecastChart f={data.forecast} />
        </div>
      )}

      {data && (
        <div className="grid gap-10 border-t border-line pt-10 lg:grid-cols-2">
          <PlanList plan={data.plan} />
          <ShockControls shock={shock} setShock={setShock} onApply={apply} busy={busy} />
        </div>
      )}

      {profile && (
        <div id="my-account" className="scroll-mt-6 border-t border-line pt-10">
          <AccountView accountId={profile.account_id} />
        </div>
      )}
    </div>
  );
}
