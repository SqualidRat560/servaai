"""ServaAI event agent (Topic 6): plain-English life event -> structured events -> engine Shock.

Gemini only PARSES text into events and, on request, rephrases engine results. It never
produces a number that is shown: every number comes from backend.engine / realistic /
forecast / plan, and explain() rejects any reply containing a number it was not given.

Chain: GEMINI_MODEL -> FALLBACK_MODEL -> rule-based regex parser (works offline).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from backend import engine

ENV_FILE = Path(__file__).resolve().parent / ".env"
FALLBACK_MODEL = "gemini-3.5-flash"
TIMEOUT_MS = 12_000
DEFAULT_EI = 0.55

EventType = Literal["job_loss", "income_cut", "bills_up", "rent_up", "repair_months",
                    "one_off", "scam", "reemployment"]


class Event(BaseModel):
    type: EventType
    pct: float | None = Field(None, description="percent as a number, e.g. 55 for 55% (EI share, bill rise, income cut)")
    amount: float | None = Field(None, description="dollars (rent increase per month, repair or scam cost)")
    months: float | None = Field(None, description="repair cost in months of typical spending, or the month number a new job starts")


class ParsedEvents(BaseModel):
    events: list[Event]
    note: str | None = None


SYSTEM = """You turn a bank customer's life event into JSON events for a financial engine.
Only extract what the text says. Never invent amounts. Types:
- job_loss: lost job / laid off. pct = EI percent of usual income if stated (e.g. 55).
- income_cut: income drops but job kept. pct = percent cut (e.g. 20 for "pay cut 20%").
- bills_up: household bills or utilities go up. pct = percent rise.
- rent_up: rent goes up. amount = dollars per month.
- repair_months: a repair/emergency costing N months of typical spending. months = N ("a full month" = 1).
- one_off: a one-time cost in dollars (furnace, car, roof, vet, medical). amount = dollars.
- scam: money lost to a scam or fraud. amount = dollars.
- reemployment: a new job starts. months = the month number it starts (e.g. 4).
If nothing financial is described, return an empty events list and a short note.
Examples:
"Laid off, EI pays 55%" -> {"events":[{"type":"job_loss","pct":55}]}
"rent went up 200" -> {"events":[{"type":"rent_up","amount":200}]}
"the furnace repair costs a full month of spending" -> {"events":[{"type":"repair_months","months":1}]}
"I got scammed out of $1,500 and my hydro bill is up 10%" -> {"events":[{"type":"scam","amount":1500},{"type":"bills_up","pct":10}]}"""


# ---------------------------------------------------------------- Gemini

def _env() -> tuple[str | None, str]:
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        pass
    return os.environ.get("GEMINI_API_KEY"), os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def _gemini_json(model: str, contents: str, system: str, schema=None) -> str:
    from google import genai  # imported lazily so the engine works without the SDK
    key, _ = _env()
    client = genai.Client(api_key=key)
    config = {"system_instruction": system, "temperature": 0,
              "http_options": {"timeout": TIMEOUT_MS, "retry_options": {"attempts": 1}}}
    if schema is not None:
        config |= {"response_mime_type": "application/json", "response_schema": schema}
    return client.models.generate_content(model=model, contents=contents, config=config).text


# ---------------------------------------------------------------- rule-based fallback

_NUM_WORDS = {"a full": 1, "a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
              "half a": 0.5}
_MONEY = r"\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|thousand)?"


def _money(num: str, k: str | None) -> float:
    v = float(num.replace(",", ""))
    return v * 1000 if k else v


def rule_parse(text: str) -> ParsedEvents:
    t = " " + text.lower().replace("’", "'") + " "
    ev: list[Event] = []
    if re.search(r"laid off|lay-?off|lost (?:my|their|his|her|the) job|lose (?:my|their|his|her) job|"
                 r"job loss|unemployed|fired|let go|lost work", t):
        m = (re.search(r"(?:\bei\b|employment insurance)[^.%]*?(\d+(?:\.\d+)?)\s*%", t)
             or re.search(r"(\d+(?:\.\d+)?)\s*%[^.]*?(?:\bei\b|employment insurance)", t))
        ev.append(Event(type="job_loss", pct=float(m.group(1)) if m else None))
    elif m := re.search(r"(?:pay|income|salary|hours)[^.%]*?(?:cut|drop|reduc|down)[^.%]*?(\d+(?:\.\d+)?)\s*%", t):
        ev.append(Event(type="income_cut", pct=float(m.group(1))))
    if m := (re.search(r"(?:bills?|utilit\w*|hydro|heating)[^.%]*?(?:up|ris\w*|increas\w*|jump\w*|higher|more)"
                       r"[^.%\d]*?(\d+(?:\.\d+)?)\s*%", t)
             or re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:higher|more|increase|rise)[^.]*?(?:bills?|utilit)", t)):
        ev.append(Event(type="bills_up", pct=float(m.group(1))))
    if m := re.search(r"rent[^.$\d%]*?(?:up|ris\w*|increas\w*|hike\w*|jump\w*|by|more)[^.$\d%]*?" + _MONEY + r"(?!\s*%)", t):
        ev.append(Event(type="rent_up", amount=_money(m.group(1), m.group(2))))
    rep = re.search(r"(?:costs?|worth|equal to|of)\s+(a full|half a|a|one|two|three|four|five|six|\d+(?:\.\d+)?)"
                    r"\s+months?(?:'s)?\s+(?:of\s+)?(?:their |my |his |her |typical |usual |normal )*"
                    r"(?:spending|expenses|costs)", t)
    if rep:
        w = rep.group(1)
        ev.append(Event(type="repair_months", months=float(_NUM_WORDS.get(w, w))))
    if m := re.search(r"(?:scam\w*|fraud\w*|stolen|phish\w*|hack\w*)[^.]*?" + _MONEY, t) or \
            re.search(_MONEY + r"[^.]*?(?:scam\w*|fraud\w*|stolen)", t):
        ev.append(Event(type="scam", amount=_money(m.group(1), m.group(2))))
    elif not rep and (m := re.search(r"(?:furnace|repair\w*|car|roof|vet|medical|dentist|appliance|fridge|"
                                     r"washer|emergency|fix\w*)[^.%]*?" + _MONEY + r"(?!\s*(?:%|months?))", t)):
        ev.append(Event(type="one_off", amount=_money(m.group(1), m.group(2))))
    if m := re.search(r"(?:new job|re-?employ\w*|back to work|find a job|finds? work|hired)[^.]*?month\s*(\d+)", t):
        ev.append(Event(type="reemployment", months=float(m.group(1))))
    return ParsedEvents(events=ev, note=None if ev else "no financial event found")


# ---------------------------------------------------------------- normalise + map to the engine

def normalize(parsed: ParsedEvents) -> tuple[list[Event], list[str]]:
    out, notes = [], []
    for e in parsed.events:
        e = e.model_copy()
        if e.pct is not None:
            e.pct = e.pct / 100 if e.pct > 1 else e.pct
            if not 0 <= e.pct <= 1:
                notes.append(f"dropped {e.type}: percent {e.pct:.0%} out of range")
                continue
        if e.amount is not None and e.amount < 0:
            notes.append(f"dropped {e.type}: negative amount")
            continue
        if e.type in ("rent_up", "one_off", "scam") and not e.amount:
            notes.append(f"dropped {e.type}: no dollar amount given")
            continue
        if e.type in ("bills_up", "income_cut") and e.pct is None:
            notes.append(f"dropped {e.type}: no percent given")
            continue
        if e.type == "repair_months" and not e.months:
            notes.append("dropped repair: no number of months given")
            continue
        if e.type == "job_loss" and e.pct is None:
            e.pct = DEFAULT_EI
            notes.append("EI share not stated: assumed 55% (README)")
        out.append(e)
    return out, notes


def to_shock(events: list[Event]) -> tuple[engine.Shock, int | None, list[str]]:
    ei, bills, rent, months, one_off, reemploy = None, 0.0, 0.0, 0.0, 0.0, None
    chip = []
    for e in events:
        if e.type == "job_loss":
            ei = e.pct if ei is None else min(ei, e.pct)
            chip.append(f"Job loss, EI {e.pct:.0%} of income")
        elif e.type == "income_cut":
            keep = 1 - e.pct
            ei = keep if ei is None else min(ei, keep)
            chip.append(f"Income cut {e.pct:.0%}")
        elif e.type == "bills_up":
            bills += e.pct
            chip.append(f"Household bills +{e.pct:.0%}")
        elif e.type == "rent_up":
            rent += e.amount
            chip.append(f"Rent +${e.amount:,.0f}/month")
        elif e.type == "repair_months":
            months += e.months
            chip.append(f"Repair = {e.months:g} month(s) of spending")
        elif e.type in ("one_off", "scam"):
            one_off += e.amount
            chip.append(f"{'Scam' if e.type == 'scam' else 'One-off cost'} ${e.amount:,.0f}")
        elif e.type == "reemployment" and e.months:
            reemploy = int(e.months)
            chip.append(f"New job from month {reemploy}")
    shock = engine.Shock(ei_pct=ei, bills_up_pct=bills, rent_up=rent, repair_months=months, one_off=one_off)
    return shock, reemploy, chip


def parse_event(text: str, use_gemini: bool = True) -> dict:
    """Text -> events + Shock fields + a confirmation chip. Never applies anything itself."""
    text = (text or "").strip()[:1000]
    source, model, errors, parsed = "rules", None, [], None
    key, primary = _env()
    if use_gemini and key and text:
        for name, label in ((primary, "gemini"), (FALLBACK_MODEL, "gemini-fallback")):
            try:
                parsed = ParsedEvents.model_validate_json(_gemini_json(name, text, SYSTEM, ParsedEvents))
                source, model = label, name
                break
            except Exception as e:  # 503 / 429 / timeout / bad JSON -> next in chain
                errors.append(f"{name}: {type(e).__name__}: {str(e)[:80]}")
    if parsed is None:
        parsed = rule_parse(text)
    events, notes = normalize(parsed)
    if parsed.note:
        notes.append(parsed.note)
    shock, reemploy, chip = to_shock(events)
    return {"source": source, "model": model, "events": [e.model_dump() for e in events],
            "shock": {**vars(shock), "reemploy_month": reemploy}, "chip": chip, "notes": notes,
            "errors": errors}


# ---------------------------------------------------------------- explain (numbers only from the engine)

_NUM = re.compile(r"-?\$?\d[\d,]*(?:\.\d+)?")


def _numbers_in(obj) -> list[float]:
    if isinstance(obj, bool) or obj is None:
        return []
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, dict):
        return [x for v in obj.values() for x in _numbers_in(v)]
    if isinstance(obj, (list, tuple)):
        return [x for v in obj for x in _numbers_in(v)]
    if isinstance(obj, str):
        return [float(s.replace("$", "").replace(",", "")) for s in _NUM.findall(obj)]
    return []


def numbers_are_grounded(text: str, facts: dict) -> tuple[bool, list[float]]:
    allowed = []
    for a in _numbers_in(facts):
        allowed += [a, abs(a), a * 100, abs(a) * 100]
    bad = []
    for s in _NUM.findall(text):
        x = abs(float(s.replace("$", "").replace(",", "")))
        ok = any(abs(x - a) <= 0.051 or (a >= 100 and abs(x - a) <= 0.5) for a in allowed)
        if not ok:
            bad.append(x)
    return (not bad), bad


def explain_facts(account_id: int, shock: engine.Shock, reemploy_month: int | None = None,
                  cap: bool = True) -> dict:
    from backend import forecast, plan, realistic
    p = engine.profile(account_id)
    run = engine.run(account_id, shock)
    real = realistic.realistic_runway(p, shock, cap=cap, reemploy_month=reemploy_month)
    fc = forecast.forecast(account_id, shock, cap=cap, reemploy_month=reemploy_month)
    pl = plan.build_plan(account_id, shock, cap=cap, reemploy_month=reemploy_month)
    end = (fc["shocked"] or fc["base"])[-1]
    return {
        "account_id": account_id,
        "judge_runway_months": run["judge_runway"]["value"], "judge_label": run["judge_runway"]["label"],
        "realistic_runway_months": real.value, "realistic_label": real.label, "realistic_reason": real.reason,
        "balance_now": round(fc["start_balance"], 2), "balance_in_3_months": round(end, 2),
        "forecast_month_3": fc["months"][-1],
        "backup_monthly_savings": round(pl["backup"]["monthly_savings"], 2),
        "backup_runway_after": pl["backup"]["runway_after"]["label"],
        "asp_weekly": round(pl["goal"]["asp_weekly"], 2),
        "event": run["shocked"]["explanation"],
    }


def template_explanation(f: dict) -> str:
    return (f"With this event, the judges' formula gives {f['judge_label']} of runway; ServaAI's realistic "
            f"estimate is {f['realistic_label']} ({f['realistic_reason']}). The balance is forecast to move "
            f"from ${f['balance_now']:,.2f} to ${f['balance_in_3_months']:,.2f} by {f['forecast_month_3']}. "
            + (f"The backup plan saves ${f['backup_monthly_savings']:,.2f} a month, giving {f['backup_runway_after']}."
               if f["backup_monthly_savings"] > 0 else "No spending cuts are needed under this event."))


def explain(facts: dict, use_gemini: bool = True) -> dict:
    key, primary = _env()
    if use_gemini and key:
        prompt = ("Explain these results to a bank customer in 2-3 short, warm, plain sentences. "
                  "Use ONLY numbers that appear in the JSON, written the same way; do not compute new ones.\n"
                  + json.dumps(facts))
        for name in (primary, FALLBACK_MODEL):
            try:
                text = _gemini_json(name, prompt, "You are ServaAI, a careful financial coach.").strip()
                ok, bad = numbers_are_grounded(text, facts)
                if ok:
                    return {"text": text, "source": "gemini", "model": name}
                return {"text": template_explanation(facts), "source": "template",
                        "rejected": f"Gemini used numbers not from the engine: {bad[:5]}"}
            except Exception:
                continue
    return {"text": template_explanation(facts), "source": "template"}
