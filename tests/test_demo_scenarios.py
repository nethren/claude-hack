"""The three demo scenarios reach their outcomes through the real API (offline gateway)."""
import json

import pytest
from fastapi.testclient import TestClient

from api_fuel import create_fuel_app
from runtime.demo_scenarios import DEMOS, RUNWAY_REOPENS_MIN, demo_scenario
from runtime.model_gateway import OfflineGateway
from runtime.scenario_loader import EXAMPLE


@pytest.fixture
def client(tmp_path):
    return TestClient(create_fuel_app(model=OfflineGateway(), log_dir=tmp_path))


def run(client, demo_id):
    scenario = client.get(f"/scenarios/demo/{demo_id}").json()
    response = client.post("/runs", json=scenario)
    assert response.status_code == 200, response.text
    result = response.json()
    events = client.get(f"/runs/{result['run_id']}/events").json()
    fuel = client.get(f"/runs/{result['run_id']}/fuel-co2")
    assert fuel.status_code == 200
    return result, events, fuel.json()


def test_catalog_lists_three_distinct_scenarios(client):
    catalog = client.get("/scenarios/demo").json()
    assert [d["id"] for d in catalog] == ["clear", "counter", "escalate"]
    assert len({d["scenario_id"] for d in catalog}) == 3


def test_unknown_demo_is_404(client):
    assert client.get("/scenarios/demo/nope").status_code == 404


@pytest.mark.parametrize("demo_id", DEMOS)
def test_every_demo_keeps_the_real_source_row(demo_id):
    original = json.loads(EXAMPLE.read_bytes())["shared"]["source_rows"]
    s = demo_scenario(demo_id)
    assert [r.model_dump() for r in s.shared.source_rows] == original
    raw = s.shared.source_rows[0].raw
    assert int(raw["WEATHER_DELAY"]) > 15 or int(raw["LATE_AIRCRAFT_DELAY"]) > 20


def test_clear_reaches_consensus_in_round_one(client):
    result, events, fuel = run(client, "clear")
    assert (result["outcome"], result["rounds_completed"], result["selected_plan_id"]) == ("CONSENSUS", 1, "P1")
    replies = [e["payload"]["reply"] for e in events if e["type"] == "AGENT_REPLIED"]
    assert {r["result"]["decision"]["verdict"] for r in replies} == {"ACCEPT"} and len(replies) == 3
    assert fuel["selected_plan_id"] == "P1"


def test_counter_offers_lead_to_a_selected_plan(client):
    result, events, _ = run(client, "counter")
    assert (result["outcome"], result["rounds_completed"], result["selected_plan_id"]) == ("CONSENSUS", 2, "P1")
    first = [e["payload"]["reply"] for e in events
             if e["type"] == "AGENT_REPLIED" and e["payload"]["reply"]["round_index"] == 1]
    assert {"COUNTER"} <= {r["result"]["decision"]["verdict"] for r in first}
    proposals = [e for e in events if e["type"] == "PROPOSAL_PUBLISHED"]
    assert len(proposals) == 2


def test_runway_closure_escalates_with_no_plan(client):
    result, events, fuel = run(client, "escalate")
    assert result["outcome"] == "ESCALATED" and result["reason_code"] == "NO_VALID_PLAN_IN_CATALOG"
    assert result["selected_plan_id"] is None and result["acceptances"] == []
    for reports in result["candidate_reports"].values():
        atc = next(r for r in reports if r["role"] == "atc")
        assert any(c["rule_id"] == "ATC_RUNWAY" and c["status"] == "FAIL" for c in atc["checks"])
    assert fuel["selected_plan_id"] is None and "selected no plan" in fuel["headline"]
    assert demo_scenario("escalate").atc.runway_open_windows[0].start_min == RUNWAY_REOPENS_MIN
