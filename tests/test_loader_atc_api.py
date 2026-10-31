import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from api import create_app
from app import default_agents
from contracts.models import ScenarioInput, scenario_hash
from domains.atc import evaluate_atc
from runtime.coordinator import run_negotiation
from runtime.model_gateway import OfflineGateway
from runtime.scenario_loader import EXAMPLE, InputError, eligible, load_scenario


@pytest.fixture
def scenario():
    return ScenarioInput.model_validate_json(EXAMPLE.read_bytes())


@pytest.mark.parametrize("weather,late,want", [(15,20,False),(16,20,True),(15,21,True),(0,21,True)])
def test_strict_delay_boundary(weather, late, want):
    assert eligible({"WEATHER_DELAY": str(weather), "LATE_AIRCRAFT_DELAY": str(late)}) is want


@pytest.mark.parametrize("value", ["NaN", "Infinity", "", "garbage"])
def test_invalid_delay_not_coerced(value):
    with pytest.raises(InputError):
        eligible({"WEATHER_DELAY": value, "LATE_AIRCRAFT_DELAY": "40"})


def test_full_source_row_is_verified(scenario, tmp_path):
    assert load_scenario(scenario).shared.source_rows[0].raw == scenario.shared.source_rows[0].raw
    scenario.shared.source_rows[0].raw["TAIL_NUMBER"] = "fabricated"
    r = asyncio.run(run_negotiation(scenario, default_agents(), OfflineGateway(), log_dir=tmp_path))
    assert r.outcome == "INPUT_ERROR" and r.reason_code == "INPUT_SOURCE_MISMATCH"
    assert r.agent_invocations == 0


@pytest.mark.parametrize("change", [
    lambda s: s.shared.options.landing_min_by_flight.pop("F1"),
    lambda s: s.pilot.limits[0].turbulence_by_landing_min.pop("10"),
    lambda s: setattr(s.pilot.limits[0], "transfer_min", None),
    lambda s: s.atc.separation_min.clear(),
    lambda s: setattr(s.atc.routes[0], "taxi_in_min", 9),
    lambda s: s.ground.crews.append(s.ground.crews[0]),
    lambda s: s.plans.append(s.plans[0].model_copy(update={"plan_id":"duplicate"})),
    lambda s: setattr(s.plans[0].assignments[0], "landing_min", 999),
    lambda s: s.plans[0].assignments.pop(),
    lambda s: setattr(s.atc.routes[0].blocked_windows[0], "end_min", 0),
])
def test_invalid_configuration_never_calls_models(scenario, tmp_path, change):
    change(scenario)
    r = asyncio.run(run_negotiation(scenario, default_agents(), OfflineGateway(), log_dir=tmp_path))
    assert r.outcome == "INPUT_ERROR" and r.agent_invocations == 0


def test_atc_fixture_and_wake_boundary(scenario):
    p0, p1, _ = scenario.plans
    r = evaluate_atc(p0, scenario.shared, scenario.atc, scenario_digest=scenario_hash(scenario))
    assert any(c.rule_id == "ATC_WAKE" and c.status == "FAIL" for c in r.checks)
    r = evaluate_atc(p1, scenario.shared, scenario.atc, scenario_digest=scenario_hash(scenario))
    assert all(c.status == "PASS" for c in r.checks)
    p1.assignments[1].landing_min = 13
    r = evaluate_atc(p1, scenario.shared, scenario.atc, scenario_digest=scenario_hash(scenario))
    assert all(c.status == "PASS" for c in r.checks)  # gap exactly 3
    p1.assignments[1].landing_min = 12
    r = evaluate_atc(p1, scenario.shared, scenario.atc, scenario_digest=scenario_hash(scenario))
    assert any(c.rule_id == "ATC_WAKE" and c.status == "FAIL" for c in r.checks)


def test_atc_blocked_route_and_half_open_boundaries(scenario):
    p = scenario.plans[1]
    p.assignments[0].taxi_route_id = "T2"
    r = evaluate_atc(p, scenario.shared, scenario.atc, scenario_digest=scenario_hash(scenario))
    assert any(c.rule_id == "ATC_TAXI" and c.status == "FAIL" for c in r.checks)
    p.assignments[0].taxi_route_id = "T1"
    scenario.atc.routes[0].blocked_windows[0].end_min = 10
    r = evaluate_atc(p, scenario.shared, scenario.atc, scenario_digest=scenario_hash(scenario))
    assert all(c.status == "PASS" for c in r.checks)


def test_api_runs_replay_evidence_and_why(scenario, tmp_path):
    client = TestClient(create_app(model=OfflineGateway(), log_dir=tmp_path))
    assert client.get("/health").json()["mode"] == "offline"
    assert client.get("/scenarios/example").json() == scenario.model_dump(mode="json")
    response = client.post("/runs", json=scenario.model_dump(mode="json"))
    assert response.status_code == 200
    r = response.json()
    assert r["outcome"] == "CONSENSUS" and r["selected_plan_id"] == "P1"
    prefix = f"/runs/{r['run_id']}"
    assert client.get(prefix).json() == r
    assert client.get(prefix + "/events").json()[-1]["type"] == "RUN_FINISHED"
    assert json.loads(client.get(prefix + "/evidence").text.splitlines()[0])["type"] == "INPUT_VALIDATED"
    assert client.get(prefix + "/why/P0").json()["reason"] == "HARD_CONSTRAINT"
    why = client.get(prefix + "/why/P2").json()
    assert why == dict(reason="POLICY_CRITERION", criterion="missed_connections", selected_value=0,
                       other_value=2, preferred_direction="lower", selected_preferred=True)
    assert client.get(prefix + "/why/unknown").status_code == 404
    assert client.get("/runs/invalid").status_code == 404
    assert client.post("/runs", json={}).status_code == 422
    # A new app instance reads persisted evidence/results after a restart.
    assert TestClient(create_app(log_dir=tmp_path)).get(prefix).json() == r
