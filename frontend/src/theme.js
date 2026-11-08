// Same palette as the @theme block in index.css, for places CSS classes can't reach:
// Recharts props, SVG fills and three.js materials. Change both together.
export const C = {
  paper: "#F3EEE5",
  raised: "#EBE4D8",
  line: "#CFC5B5",
  ink: "#34322E",
  muted: "#67625A",
  stone: "#8A857C",
  accent: "#D9895A",
  accentSoft: "#EED9C8",
  accentInk: "#9A4F22",
  positive: "#8FA08A",
  positiveInk: "#546851",
  negative: "#B5705A",
  negativeInk: "#96503C",
  // derived shades (coin edges, a lighter segment tone, 3D lights)
  coinEdge: "#B9714A",
  coinEdgeSoft: "#D2AE90",
  fragile: "#E3B48F",
  rimLight: "#E8E1D5",
  keyLight: "#FFF6EA",
};

export const tooltipStyle = {
  background: C.paper, border: `1px solid ${C.line}`, borderRadius: 6, color: C.ink, boxShadow: "none",
};
