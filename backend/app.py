"""ServaAI API (FastAPI). Every number comes from backend.engine.

Run from the repo root:
    .venv/Scripts/python -m uvicorn backend.app:app --port 8000
Then open http://localhost:8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import engine

STATIC = Path(__file__).resolve().parent / "static"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    engine.get_profiles()  # load the cached profiles once at startup
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


@app.post("/api/shock")
def shock(req: ShockRequest) -> dict:
    try:
        s = engine.Shock(ei_pct=req.ei_pct, bills_up_pct=req.bills_up_pct, rent_up=req.rent_up,
                         repair_months=req.repair_months, one_off=req.one_off)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    return _run(req.account_id, s)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
