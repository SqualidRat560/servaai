import { C } from "../theme.js";
// 2D fallback for the hero: one coin = one month of runway.
// Solid tangerine = realistic runway, peel = months the backup plan adds,
// outline = extra months the judge formula promises on top.
export const MAX_COINS = 24;

export function coinCounts(judge, realistic, backup) {
  const v = (x) => Math.min(x === null || x === undefined ? MAX_COINS : x, MAX_COINS);
  const real = Math.round(v(realistic));
  const plan = Math.max(Math.round(v(backup ?? realistic)) - real, 0);
  const ghost = Math.max(Math.round(v(judge)) - real - plan, 0);
  return { real, plan, ghost };
}

export default function CoinStack2D({ judge, realistic, backup }) {
  const { real, plan, ghost } = coinCounts(judge, realistic, backup);
  const total = real + plan + ghost;
  const W = 300, coinH = 11, rx = 92, ry = 22, base = 40 + MAX_COINS * coinH + ry;
  const coins = Array.from({ length: total }, (_, i) => (i < real ? "real" : i < real + plan ? "plan" : "ghost"));
  return (
    <svg viewBox={`0 0 ${W} ${base + 30}`} className="h-full w-full" role="img"
         aria-label={`${real} months realistic runway${plan ? `, ${plan} more with the backup plan` : ""}${ghost ? `, ${ghost} more promised by the judge formula` : ""}`}>
      <ellipse cx={W / 2} cy={base + 8} rx={rx + 26} ry={ry + 6} fill={C.raised} />
      {coins.map((kind, i) => {
        const y = base - i * coinH;
        const fill = kind === "real" ? C.accent : kind === "plan" ? C.accentSoft : "none";
        const edge = kind === "real" ? C.coinEdge : kind === "plan" ? C.coinEdgeSoft : C.stone;
        return (
          <g key={i} style={{ transition: "opacity 300ms", transitionDelay: `${i * 18}ms` }}>
            {kind !== "ghost" && <rect x={W / 2 - rx} y={y - coinH} width={rx * 2} height={coinH} fill={edge} />}
            <ellipse cx={W / 2} cy={y} rx={rx} ry={ry} fill={kind === "ghost" ? "none" : edge}
                     stroke={kind === "ghost" ? edge : "none"} strokeDasharray={kind === "ghost" ? "4 5" : undefined} />
            <ellipse cx={W / 2} cy={y - coinH} rx={rx} ry={ry} fill={fill} stroke={kind === "ghost" ? edge : "none"}
                     strokeDasharray={kind === "ghost" ? "4 5" : undefined} />
          </g>
        );
      })}
      {total === 0 && (
        <text x={W / 2} y={base - 30} textAnchor="middle" fill={C.negativeInk} className="display" fontSize="22">No buffer left</text>
      )}
    </svg>
  );
}
