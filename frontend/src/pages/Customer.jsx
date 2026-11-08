import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { getAccount, runScenario } from "../api.js";
import AccountView, { CLOSED } from "../components/AccountView.jsx";
import ChatBot from "../components/ChatBot.jsx";
import CoinStack2D from "../components/CoinStack2D.jsx";
import ForecastChart from "../components/ForecastChart.jsx";
import PlanList from "../components/PlanList.jsx";
import PowerBIPanel from "../components/PowerBIPanel.jsx";
import RunwayPair from "../components/RunwayPair.jsx";
import ShockControls, { EMPTY } from "../components/ShockControls.jsx";

const HeroStack = lazy(() => import("../three/HeroStack.jsx"));
const EXAMPLES = [["63816", "typical"], ["32078", "no savings"], ["99477", "account closed early"]];

export default function Customer({ initialId, threeD }) {
  const [input, setInput] = useState(initialId || "63816");
  const [profile, setProfile] = useState(null);
  const [shock, setShock] = useState(EMPTY);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [panel, setPanel] = useState(CLOSED);          // the inline transaction list under the account cards
  const [detailsOpen, setDetailsOpen] = useState(false); // forecast, plan and formulas

  // buttons under chatbot answers: open the transaction list, show the forecast, or compare with everyone
  const onLink = useCallback((l) => {
    if (l.kind === "transactions") {
      const f = l.filter || {};
      setPanel({ ...CLOSED, open: true, nonce: Date.now(), category: f.category || "", purpose: f.purpose || "", month: f.month || "",
                 title: l.label.replace(/^View \d+ /, "").replace(/^./, (c) => c.toUpperCase()) });
    } else if (l.kind === "forecast") {
      setDetailsOpen(true);
      setTimeout(() => document.getElementById("forecast-anchor")?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    } else if (l.kind === "portfolio") {
      window.location.hash = "#/portfolio";
    }
  }, []);

  const run = useCallback(async (s, id) => {
    const full = { ...EMPTY, ...s };
    setShock(full);
    setData(await runScenario(id, full));
  }, []);

  const lookup = useCallback(async (id) => {
    setError("");
    try {
      const a = await getAccount(id.trim());
      setProfile(a.profile);
      window.history.replaceState(null, "", `#/customer/${a.profile.account_id}`);
      setPanel(CLOSED);
      await run(EMPTY, a.profile.account_id);
    } catch (e) { setError(e.message); }
  }, [run]);

  useEffect(() => { lookup(initialId || "63816"); }, [initialId, lookup]);

  const r = data?.result;
  const stackProps = r && { judge: r.judge_runway.value, realistic: r.realistic_runway.value,
                            backup: data.plan.backup.runway_after.value };

  return (
    <div className="space-y-14">
      <form onSubmit={(e) => { e.preventDefault(); lookup(input); }} className="flex flex-wrap items-end gap-x-4 gap-y-2">
        <div>
          <label htmlFor="acct" className="block text-sm text-muted">Account</label>
          <div className="flex gap-2">
            <input id="acct" value={input} inputMode="numeric" onChange={(e) => setInput(e.target.value)}
                   className="w-36 rounded-md border border-line bg-paper px-3 py-2 tabular-nums" />
            <button className="rounded-md border border-line px-4 hover:bg-raised">Open</button>
          </div>
        </div>
        <div className="flex flex-wrap gap-x-4 pb-2 text-sm text-muted">
          {EXAMPLES.map(([id, what]) => (
            <button type="button" key={id} onClick={() => { setInput(id); lookup(id); }}
                    className="underline decoration-line underline-offset-4 hover:text-ink">{id} ({what})</button>
          ))}
        </div>
      </form>
      {error && <p role="alert" className="text-negative-ink">{error}</p>}

      {profile && <AccountView accountId={profile.account_id} panel={panel} setPanel={setPanel} />}

      {profile && (
        <section aria-label="Ask ServaAI" className="space-y-4 border-t border-line pt-10">
          <div>
            <h2 className="display text-2xl">What's happening in your life?</h2>
            <p className="text-muted">Tell ServaAI in your own words. It shows how long your money would last and what you could change.</p>
          </div>
          <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
            <ChatBot accountId={profile.account_id} onApplied={(s) => run(s, profile.account_id)} onLink={onLink} />
            <figure className="m-0 overflow-hidden rounded-md border border-line bg-raised">
              <div className="h-[300px] sm:h-[400px]">
                {stackProps && (threeD
                  ? <Suspense fallback={<div className="h-full p-6"><CoinStack2D {...stackProps} /></div>}><HeroStack {...stackProps} /></Suspense>
                  : <div className="h-full p-6"><CoinStack2D {...stackProps} /></div>)}
              </div>
              <figcaption className="border-t border-line px-4 py-3 text-sm text-muted">
                Each coin is one month your savings would last. Light coins: months the suggestions add back.
                Outlined: extra months the simple judge formula assumes.
              </figcaption>
            </figure>
          </div>
        </section>
      )}

      <div className="border-t border-line pt-10"><PowerBIPanel /></div>

      {data && (
        <details open={detailsOpen} onToggle={(e) => setDetailsOpen(e.currentTarget.open)} className="rounded-md border border-line p-4">
          <summary className="cursor-pointer font-medium">Details: forecast, plan and the numbers behind it</summary>
          <div className="mt-6 space-y-12">
            <div className="space-y-2">
              <RunwayPair judge={r.judge_runway} realistic={r.realistic_runway} />
              <p className="max-w-[70ch] text-xs text-muted">Judge formula: {r.judge_runway.explanation}</p>
            </div>
            <div id="forecast-anchor" className="scroll-mt-6"><ForecastChart f={data.forecast} /></div>
            <div className="grid gap-10 lg:grid-cols-2">
              <PlanList plan={data.plan} />
              <ShockControls shock={shock} setShock={setShock} onApply={(s) => run(s, profile.account_id)} busy={false} />
            </div>
          </div>
        </details>
      )}
    </div>
  );
}
