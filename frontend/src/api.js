// Every number the app shows comes from these endpoints (the tested Python engine).
async function call(path, body) {
  const opts = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  };
  let res;
  try {
    res = await fetch(`/api${path}`, opts);
  } catch {
    throw new Error("Can't reach the ServaAI server. Start it with: .venv/Scripts/python -m uvicorn backend.app:app --port 8000");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    if (res.status === 404) throw new Error(typeof d === "string" ? `No customer with that account_id (${d.replace(/\D+/g, "")}).` : "Not found.");
    throw new Error(typeof d === "string" ? d : "That input isn't valid. Check the numbers and try again.");
  }
  return data;
}

export const getAccount = (id) => call(`/accounts/${encodeURIComponent(id)}`);
export const getTwists = () => call("/twists");
export const parseEvent = (text) => call("/parse-event", { text });
export const getPortfolio = () => call("/portfolio");
export const getBacktest = () => call("/backtest");
export function getStatement(id, { limit = 15, before, direction } = {}) {
  const q = new URLSearchParams({ limit: String(limit) });
  if (before) q.set("before", before);
  if (direction) q.set("direction", direction);
  return call(`/accounts/${encodeURIComponent(id)}/statement?${q}`);
}

export async function runScenario(accountId, shock) {
  const body = { account_id: accountId, ...shock };
  const [result, forecast, plan] = await Promise.all([call("/shock", body), call("/forecast", body), call("/plan", body)]);
  return { result, forecast, plan };
}
export const explain = (accountId, shock) => call("/explain", { account_id: accountId, ...shock });

export const money = (v, digits = 0) =>
  v === null || v === undefined ? "n/a"
    : v.toLocaleString("en-CA", { style: "currency", currency: "CAD", minimumFractionDigits: digits, maximumFractionDigits: digits });
export const months = (r) => (r.value === null ? "120+" : r.value.toFixed(1));
