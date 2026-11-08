import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { explain, getAccount, money, runScenario } from "../api.js";
import CoinStack2D from "../components/CoinStack2D.jsx";
import EventBox from "../components/EventBox.jsx";
import ForecastChart from "../components/ForecastChart.jsx";
import PlanList from "../components/PlanList.jsx";
import RunwayPair from "../components/RunwayPair.jsx";
import ShockControls, { EMPTY } from "../components/ShockControls.jsx";

const HeroStack = lazy(() => import("../three/HeroStack.jsx"));
const EXAMPLES = [["63816", "typical"], ["32078", "no savings"], ["99477", "account closed early"]];

export default function Customer({ initialId, threeD }) {
  const [input, setInput] = useState(initialId || "63816");
  const [profile, setProfile] = useState(null);
  const [shock, setShock] = useState(EMPTY);
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [story, setStory] = useState(null);

  const apply = useCallback(async (s, id = profile?.account_id) => {
    if (!id) return;
    setBusy(true); setError(""); setStory(null);
    const full = { ...EMPTY, ...s };
    setShock(full);
    try { setData(await runScenario(id, full)); } catch (e) { setError(e.message); }
    setBusy(false);
  }, [profile]);

  const lookup = useCallback(async (id) => {
    setBusy(true); setError(""); setStory(null);
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

  async function tellStory() {
    setStory({ text: "Writing…" });
    try { setStory(await explain(profile.account_id, shock)); } catch (e) { setStory({ text: e.message }); }
  }

  const r = data?.result;
  const backup = data?.plan?.backup?.runway_after;
  const stackProps = r && { judge: r.judge_runway.value, realistic: r.realistic_runway.value, backup: backup?.value,
                            buffer: profile.B, bufferLeft: r.judge_runway.buffer_left };

  return (
    <div className="space-y-12">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,11fr)_minmax(0,9fr)]">
        <figure className="relative order-2 m-0 h-[380px] overflow-hidden rounded-2xl bg-deepwater/60 sm:h-[460px] lg:order-1 lg:h-[560px]">
          {stackProps && (threeD
            ? <Suspense fallback={<div className="h-full p-6"><CoinStack2D {...stackProps} /></div>}><HeroStack {...stackProps} /></Suspense>
            : <div className="h-full p-6"><CoinStack2D {...stackProps} /></div>)}
          <figcaption className="absolute bottom-3 left-4 right-4 text-sm text-mist">
            One coin is one month of runway.{" "}
            <span className="text-tangerine">Orange</span>: realistic.{" "}
            <span className="text-peel">Light</span>: added by the backup plan. Outline: extra months the judge formula promises.
          </figcaption>
        </figure>

        <div className="order-1 space-y-8 lg:order-2">
          <form onSubmit={(e) => { e.preventDefault(); lookup(input); }} className="space-y-2">
            <label htmlFor="acct" className="block text-sm text-mist">Customer account</label>
            <div className="flex gap-2">
              <input id="acct" value={input} inputMode="numeric" onChange={(e) => setInput(e.target.value)}
                     className="w-40 rounded-lg border border-line bg-deepwater px-3 py-2 text-lg tabular-nums" />
              <button className="rounded-lg border border-line px-4 text-mist hover:text-frost" disabled={busy}>Look up</button>
            </div>
            <div className="flex flex-wrap gap-x-4 text-sm text-mist">
              {EXAMPLES.map(([id, what]) => (
                <button type="button" key={id} onClick={() => { setInput(id); lookup(id); }}
                        className="underline decoration-line underline-offset-4 hover:text-frost">{id} ({what})</button>
              ))}
            </div>
          </form>

          {profile && (
            <p className="max-w-[58ch] text-[15px] leading-relaxed text-mist">
              In a typical month this customer brings in <span className="text-frost">{money(profile.I)}</span> and
              spends <span className="text-frost">{money(profile.S)}</span>, including fixed costs of {money(profile.F)}
              {profile.P > 0 && <> (a {money(profile.P)} loan payment)</>}. Their savings buffer is
              {" "}<span className={profile.B > 0 ? "text-tangerine" : "text-overdraft"}>{money(profile.B)}</span>.
            </p>
          )}

          <EventBox onApply={(s) => apply(s)} busy={busy} />
          {error && <p role="alert" className="text-overdraft">{error}</p>}
        </div>
      </div>

      {r && (
        <div className="grid gap-10 lg:grid-cols-[minmax(0,11fr)_minmax(0,9fr)]">
          <div className="space-y-4">
            <RunwayPair judge={r.judge_runway} realistic={r.realistic_runway} />
            <p className="max-w-[70ch] text-xs text-mist">Judge formula: {r.judge_runway.explanation}</p>
            <div>
              <button onClick={tellStory} className="text-sm text-tangerine underline underline-offset-4 hover:text-peel">
                Explain this in plain English
              </button>
              {story && <p className="mt-2 max-w-[62ch] text-[15px]">{story.text}
                {story.source === "template" && <span className="text-mist"> (written from the engine's numbers; Gemini was unavailable)</span>}</p>}
            </div>
          </div>
          <ShockControls shock={shock} setShock={setShock} onApply={apply} busy={busy} />
        </div>
      )}

      {data && (
        <div className="grid gap-10 lg:grid-cols-2">
          <ForecastChart f={data.forecast} />
          <PlanList plan={data.plan} />
        </div>
      )}
    </div>
  );
}
