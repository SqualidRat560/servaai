import { months } from "../api.js";

function Figure({ label, runway, accent }) {
  const n = months(runway);
  const unit = runway.value === null ? "no shortfall" : "months";
  return (
    <div>
      <div className={`text-[15px] ${accent ? "text-accent-ink" : "text-muted"}`}>{label}</div>
      <div className={`numeral text-[clamp(4.5rem,11vw,8.5rem)] ${accent ? "text-ink" : "text-muted"}`}>{n}</div>
      <div className="mt-1 text-[15px] text-muted">{unit}</div>
    </div>
  );
}

export default function RunwayPair({ judge, realistic }) {
  const gap = judge.value !== null && realistic.value !== null ? judge.value - realistic.value
    : judge.value === null && realistic.value !== null ? null : 0;
  return (
    <section aria-label="Runway">
      <div className="flex items-end gap-8 sm:gap-12">
        <Figure label="Judge formula" runway={judge} />
        <Figure label="ServaAI realistic" runway={realistic} accent />
      </div>
      <p className="mt-4 max-w-[60ch] text-[15px] text-muted">
        {gap === null
          ? <>The formula sees no shortfall at all; realistically the money runs out after {months(realistic)} months.</>
          : gap > 0.05
            ? <>The formula overstates this customer's runway by <span className="text-ink">{gap.toFixed(1)} months</span>. {realistic.reason}.</>
            : <>Both views agree. {realistic.reason}.</>}
      </p>
    </section>
  );
}
