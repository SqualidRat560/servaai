"""The API returns exactly the engine's numbers (same as Phase 1)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import engine
from backend.app import app

client = TestClient(app)


def test_health_and_page():
    assert client.get("/api/health").json() == {"ok": True, "accounts": 4500}
    page = client.get("/")
    assert page.status_code == 200 and "ServaAI" in page.text


@pytest.mark.parametrize("aid", [63816, 32078, 99477])
def test_account_matches_engine(aid):
    d = client.get(f"/api/accounts/{aid}").json()
    assert d["profile"] == engine.profile(aid).to_dict()
    for name, shock in engine.TWISTS.items():
        assert d["readme_twists"][name] == engine.run(aid, shock)["judge_runway"]


@pytest.mark.parametrize("name", list(engine.TWISTS))
def test_shock_endpoint_matches_engine(name):
    shock = engine.TWISTS[name]
    body = {"account_id": 63816, **vars(shock)}
    got = client.post("/api/shock", json=body).json()
    assert {k: got[k] for k in ("profile", "shock", "shocked", "judge_runway")} == engine.run(63816, shock)
    assert "realistic_runway" in got


def test_readme_twist_values_through_api():
    got = [client.post("/api/shock", json={"account_id": 63816, **vars(s)}).json()["judge_runway"]["value"]
           for s in engine.TWISTS.values()]
    assert got == [3.4, 98.3, 3.1]


def test_unknown_account_is_404():
    assert client.get("/api/accounts/1").status_code == 404
    assert client.post("/api/shock", json={"account_id": 1}).status_code == 404


@pytest.mark.parametrize("body", [{"account_id": 63816, "ei_pct": 1.5},
                                  {"account_id": 63816, "one_off": -10},
                                  {"account_id": "abc"}])
def test_bad_shock_is_422(body):
    assert client.post("/api/shock", json=body).status_code == 422


def test_realistic_forecast_and_plan_endpoints():
    body = {"account_id": 63816, "ei_pct": 0.55}
    r = client.post("/api/shock", json=body).json()
    assert r["judge_runway"]["value"] == 3.4 and r["realistic_runway"]["value"] < 3.4
    f = client.post("/api/forecast", json=body).json()
    assert len(f["base"]) == 3 and len(f["shocked"]) == 3
    assert client.get("/api/forecast/63816").json()["shocked"] is None
    pl = client.post("/api/plan", json=body).json()
    assert pl["backup"]["runway_after"]["value"] >= pl["backup"]["runway_before"]["value"]
    assert client.post("/api/plan", json={"account_id": 1}).status_code == 404
