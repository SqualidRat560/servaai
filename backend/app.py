"""ServaAI API (FastAPI). Every number comes from backend.engine.

Run from the repo root:
    .venv/Scripts/python -m uvicorn backend.app:app --port 8000
Then open http://localhost:8000
"""
from __future__ import annotations

import os
import re
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import advice as advice_mod
from backend import agent, engine, forecast, money_chat, plan, population, realistic, statement

STATIC = Path(__file__).resolve().parent / "static"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    engine.get_profiles()  # load the cached profiles once at startup
    forecast.load_bundle()  # load (or train once) the forecast models
    population.load_portfolio()  # build the portfolio once so /api/portfolio is instant
    statement.store()  # transactions loaded once (parquet cache), never per request
    yield


app = FastAPI(title="ServaAI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])

TWIST_TEXT = {
    "layoff_ei55": "Laid off. EI pays 55% of usual income for 6 months.",
    "furnace_1mo": "The furnace dies; the repair costs a full month of typical spending.",
    "layoff_ei55_bills15": "Job loss (EI at 55%) and household bills up 15% in the same month.",
}


class ShockRequest(BaseModel):
    account_id: int
    ei_pct: float | None = Field(None, ge=0, le=1, description="EI share of income, 0.55 = 55%")
    bills_up_pct: float = Field(0.0, ge=0, description="household bills up, 0.15 = 15%")
    rent_up: float = Field(0.0, ge=0, description="rent up, dollars per month")
    repair_months: float = Field(0.0, ge=0, description="repair costing k months of spending")
    one_off: float = Field(0.0, ge=0, description="repair or scam, dollars")
    ei_cap: bool = Field(True, description="apply the EI cap of $729/week (realistic runway)")
    reemploy_month: int | None = Field(None, ge=1, le=120, description="new job from this month")

    def to_shock(self) -> engine.Shock:
        try:
            return engine.Shock(ei_pct=self.ei_pct, bills_up_pct=self.bills_up_pct, rent_up=self.rent_up,
                                repair_months=self.repair_months, one_off=self.one_off)
        except ValueError as e:
            raise HTTPException(422, str(e)) from None


def _run(account_id: int, shock: engine.Shock) -> dict:
    try:
        return engine.run(account_id, shock)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {account_id} not found") from None


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "accounts": len(engine.get_profiles())}


@app.get("/api/twists")
def twists() -> list[dict]:
    return [{"id": k, "text": TWIST_TEXT[k], "shock": vars(v)} for k, v in engine.TWISTS.items()]


@app.get("/api/accounts/{account_id}")
def account(account_id: int) -> dict:
    try:
        p = engine.profile(account_id)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {account_id} not found") from None
    baseline = _run(account_id, engine.Shock())["judge_runway"]
    readme = {k: _run(account_id, s)["judge_runway"] for k, s in engine.TWISTS.items()}
    return {"profile": p.to_dict(), "runway_no_shock": baseline, "readme_twists": readme}


@app.get("/api/accounts/{account_id}/statement")
def account_statement(account_id: int, limit: int = 50, before: str | None = None, direction: str | None = None,
                      category: str | None = None, purpose: str | None = None, month: str | None = None) -> dict:
    """'My account': balance, loan (estimate), cards and transactions, newest first. Filters: direction
    (in/out), category (a key from /categories), purpose (raw, e.g. 'loan payment'), month (YYYY-MM)."""
    if before is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", before):
        raise HTTPException(422, "before must be a date like 2025-06-30")
    if month is not None and not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(422, "month must look like 2025-06")
    if direction not in (None, "", "in", "out"):
        raise HTTPException(422, "direction must be 'in' or 'out'")
    try:
        return statement.statement(account_id, limit=limit, before=before, direction=direction or None,
                                   category=category or None, purpose=purpose or None, month=month)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {account_id} not found") from None
    except statement.BadFilter as e:
        raise HTTPException(422, str(e)) from None


@app.get("/api/accounts/{account_id}/categories")
def account_categories(account_id: int, month: str | None = None) -> dict:
    """Totals per category (they add up to money out / money in) for one month, default the latest."""
    if month is not None and not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(422, "month must look like 2025-06")
    try:
        return statement.categories(account_id, month)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {account_id} not found") from None
    except statement.BadFilter as e:
        raise HTTPException(422, str(e)) from None


@app.post("/api/shock")
def shock(req: ShockRequest) -> dict:
    s = req.to_shock()
    out = _run(req.account_id, s)
    p = engine.profile(req.account_id)
    out["realistic_runway"] = realistic.realistic_runway(
        p, s, cap=req.ei_cap, reemploy_month=req.reemploy_month).to_dict()
    return out


@app.get("/api/forecast/{account_id}")
def forecast_get(account_id: int) -> dict:
    try:
        return forecast.forecast(account_id)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {account_id} not found") from None


@app.post("/api/forecast")
def forecast_post(req: ShockRequest) -> dict:
    s = req.to_shock()
    try:
        return forecast.forecast(req.account_id, s, cap=req.ei_cap, reemploy_month=req.reemploy_month)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {req.account_id} not found") from None


@app.post("/api/plan")
def plan_post(req: ShockRequest) -> dict:
    s = req.to_shock()
    try:
        return plan.build_plan(req.account_id, s, cap=req.ei_cap, reemploy_month=req.reemploy_month)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {req.account_id} not found") from None


class EventText(BaseModel):
    text: str = Field(..., max_length=1000)


@app.post("/api/parse-event")
def parse_event(req: EventText) -> dict:
    """Text -> structured events + shock fields. Shows a chip to confirm; applies nothing."""
    return agent.parse_event(req.text)


@app.post("/api/explain")
def explain(req: ShockRequest) -> dict:
    """Plain-English summary; every number in it comes from the engine (checked)."""
    s = req.to_shock()
    try:
        facts = agent.explain_facts(req.account_id, s, reemploy_month=req.reemploy_month, cap=req.ei_cap)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {req.account_id} not found") from None
    return {**agent.explain(facts), "facts": facts}


class ChatTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=money_chat.MAX_CHARS)


class ChatRequest(BaseModel):
    account_id: int
    messages: list[ChatTurn] = Field(..., min_length=1, max_length=40)  # the last 8 are used


RATE_LIMIT = 20          # chat requests per IP ...
RATE_WINDOW = 10 * 60    # ... per 10 minutes (in memory)
_hits: dict[str, deque] = {}


def _allow(ip: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    q = _hits.setdefault(ip, deque())
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return False
    q.append(now)
    return True


@app.post("/api/chat")
def chat(req: ChatRequest, request: Request) -> dict:
    """Ask about your money. Gemini calls read-only tools bound to req.account_id; numbers come from tool results."""
    if not _allow(request.client.host if request.client else "unknown"):
        raise HTTPException(429, "That's a lot of questions in a short time. Please wait a few minutes and try again.")
    try:
        engine.profile(req.account_id)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {req.account_id} not found") from None
    try:
        return money_chat.respond(req.account_id, [t.model_dump() for t in req.messages])
    except ValueError as e:
        raise HTTPException(422, str(e)) from None


@app.post("/api/advice")
def advice(req: ShockRequest) -> dict:
    """The outcome in plain words + lifestyle suggestions; every number comes from the engine (checked)."""
    s = req.to_shock()
    try:
        f = advice_mod.facts(req.account_id, s, reemploy_month=req.reemploy_month, cap=req.ei_cap)
    except engine.UnknownAccount:
        raise HTTPException(404, f"account_id {req.account_id} not found") from None
    return {**advice_mod.outcome_advice(f), "facts": f}


class SpeakRequest(BaseModel):
    text: str = Field(..., max_length=1500)


@app.post("/api/speak")
def speak(req: SpeakRequest) -> Response:
    """ElevenLabs text-to-speech when ELEVENLABS_API_KEY is set in backend/.env.
    404 = not configured, so the app falls back to the browser's built-in voice."""
    agent._env()  # loads backend/.env into the environment
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise HTTPException(404, "voice not configured")
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    try:
        r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                       headers={"xi-api-key": key, "accept": "audio/mpeg"},
                       json={"text": req.text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_turbo_v2_5")},
                       timeout=20)
        r.raise_for_status()
    except Exception:
        raise HTTPException(502, "voice service unavailable") from None
    return Response(content=r.content, media_type="audio/mpeg")


@app.get("/api/portfolio")
def portfolio() -> dict:
    """Headline + one compact point per customer (for the galaxy and the Portfolio page)."""
    a = population.load_portfolio()
    import pandas as pd
    hl = pd.read_csv(population.EXPORTS / "headline.csv") if (population.EXPORTS / "headline.csv").exists() else None
    if hl is None:
        population.build(write=True)
        hl = pd.read_csv(population.EXPORTS / "headline.csv")
    headline = {r.metric: {"share": r.share, "ci_low": r.ci_low, "ci_high": r.ci_high} for r in hl.itertuples()}
    seg = a["segment"].value_counts().reindex(population.SEGMENTS, fill_value=0)
    pts = [{"id": int(i), "segment": r.segment, "B": round(float(r.B), 2),
            "judge": None if pd.isna(r.judge_ei55) else float(r.judge_ei55),
            "realistic": None if pd.isna(r.realistic_ei55) else float(r.realistic_ei55),
            "region": r.region} for i, r in zip(a.index, a.itertuples())]
    return {"shock": "Job loss, EI 55%", "headline": headline,
            "segments": {k: int(v) for k, v in seg.items()}, "points": pts}


@app.get("/api/backtest")
def backtest() -> dict:
    b = forecast.load_bundle()
    return {"winner": b["winner"], "results": b["results"], "avg_mae": b["avg_mae"],
            "coverage": b["coverage"], "rows": b["rows"]}


DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


@app.get("/preview")
def preview() -> FileResponse:
    """The original plain-HTML engine preview."""
    return FileResponse(STATIC / "index.html")


@app.get("/")
def index() -> FileResponse:
    """The React app when it has been built (npm run build), else the plain preview."""
    built = DIST / "index.html"
    return FileResponse(built if built.exists() else STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
