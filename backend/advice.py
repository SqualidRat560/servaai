"""Chatbot replies: the outcome in plain words + lifestyle suggestions.

Gemini writes the words; every number must come from the engine's facts (checked with
agent.numbers_are_grounded). If Gemini is down or invents a number, template advice built from
the same facts is used instead.
"""
from __future__ import annotations

import json

from pydantic import BaseModel

from backend import agent, engine, plan

SYSTEM = ("You are ServaAI, a warm, practical money coach for a Tangerine bank customer. "
          "Give everyday lifestyle suggestions in plain words. No jargon, no formulas. "
          "Write money as whole dollars with a dollar sign and commas, like $3,159; write months like 1.9 months.")


class AdviceOut(BaseModel):
    summary: str
    suggestions: list[str]


def facts(account_id: int, shock: engine.Shock, reemploy_month: int | None = None, cap: bool = True) -> dict:
    f = agent.explain_facts(account_id, shock, reemploy_month=reemploy_month, cap=cap)
    pl = plan.build_plan(account_id, shock, cap=cap, reemploy_month=reemploy_month)
    med = plan.flexible_medians(int(account_id))
    f["monthly_card_spending"] = round(med["card_withdrawals"], 2)
    f["monthly_cash_withdrawals"] = round(med["cash_withdrawals_genuine"], 2)
    f["backup_cuts"] = [{"what": c["label"], "per_month": round(c["cut"], 2)} for c in pl["backup"]["cuts"]]
    f["weekly_savings_suggestion"] = round(pl["goal"]["asp_weekly"], 2)
    f["job_loss"] = shock.ei_pct is not None
    return f


def template_tips(f: dict) -> list[str]:
    tips = [f"Trim {c['what']} by about ${c['per_month']:,.0f} a month." for c in f["backup_cuts"][:2]]
    if f["job_loss"]:
        tips.append("Apply for Employment Insurance in the first week: payments start sooner when you apply early.")
    tips += ["Cook at home a few more nights a week and plan meals around what is on sale.",
             "Pause subscriptions and memberships you did not use this month.",
             "Turn on a low-balance alert so nothing catches you by surprise."]
    if f["weekly_savings_suggestion"] > 0:
        tips.append(f"Move ${f['weekly_savings_suggestion']:,.0f} a week automatically into an emergency fund.")
    return tips[:5]


def _ask(prompt: str, f: dict) -> dict | None:
    key, primary = agent._env()
    if not key:
        return None
    for name in (primary, agent.FALLBACK_MODEL):
        try:
            out = AdviceOut.model_validate_json(agent._gemini_json(name, prompt, SYSTEM, AdviceOut))
        except Exception:
            continue
        ok, bad = agent.numbers_are_grounded(out.summary + " " + " ".join(out.suggestions), f)
        if ok and out.suggestions:
            return {"summary": out.summary, "suggestions": out.suggestions[:5], "source": "gemini", "model": name}
        return {"rejected": f"Gemini used numbers not from the engine: {bad[:5]}"}
    return None


def outcome_advice(f: dict, use_gemini: bool = True) -> dict:
    if use_gemini:
        got = _ask("Using ONLY numbers from this JSON (same values; whole dollars are fine), return JSON with "
                   "'summary': 2 short friendly sentences on how long their money lasts and what happens to their "
                   "balance next, and 'suggestions': 4 short concrete lifestyle changes (meals, transport, "
                   "subscriptions, side income, applying for EI early...), at most one number each, only from the JSON.\n"
                   + json.dumps(f), f)
        if got and "summary" in got:
            return got
    return {"summary": agent.template_explanation(f), "suggestions": template_tips(f), "source": "template"}


def answer(account_id: int, question: str, use_gemini: bool = True) -> dict:
    f = facts(account_id, engine.Shock())
    if use_gemini:
        got = _ask("Customer question: " + question[:500] + "\nTheir numbers (use ONLY these, same values):\n"
                   + json.dumps(f) + "\nReturn JSON: 'summary' (a 1-2 sentence direct, friendly answer) and "
                   "'suggestions' (3-4 short practical lifestyle suggestions).", f)
        if got and "summary" in got:
            return got
    return {"summary": "Here is what would help most right now, based on your own spending.",
            "suggestions": template_tips(f), "source": "template"}
