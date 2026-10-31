"""Fuel & CO2 panel: modelled-estimate arithmetic, baseline, labelling, API."""
import pytest
from fastapi.testclient import TestClient

from analysis.fuel_co2 import (CO2_KG_PER_KG_FUEL, ESTIMATE_LABEL, PlanEstimate,
                               build_panel, compare, estimate_plan,
                               hard_check_results, render_text,
                               scheduled_order_baseline)
from api_fuel import create_fuel_app
from contracts.models import Interval, ScenarioInput
from runtime.model_gateway import OfflineGateway
from runtime.scenario_loader import EXAMPLE


@pytest.fixture
def scenario():
    return ScenarioInput.model_validate_json(EXAMPLE.read_bytes())


def plan(s, plan_id):
    return next(p for p in s.plans if p.plan_id == plan_id)


def estimate(plan_id, fuel):
    return PlanEstimate(plan_id=plan_id, status="ESTIMATED", unknown_reason=None,
                        flights=[], holding_min=0, fuel_kg=fuel,
                        co2_kg=round(fuel * CO2_KG_PER_KG_FUEL, 1))


def test_co2_factor_is_the_standard_value():
    assert CO2_KG_PER_KG_FUEL == 3.16


def test_plan_fuel_uses_holding_minutes_and_per_flight_burn(scenario):
    # P2: F1 14-10=4, F2 18-12=6, F3 26-22=4 min holding at 50 kg/min.
    est = estimate_plan(scenario, plan(scenario, "P2"))
    assert [(f.flight_id, f.holding_min, f.fuel_kg) for f in est.flights] == [
        ("F1", 4, 200), ("F2", 6, 300), ("F3", 4, 200)]
    assert est.fuel_kg == 700
    assert est.co2_kg == 2212.0
    assert est.flights[0].evidence_refs == ["source:seed-76", "overlay:pilot"]


def test_landing_before_earliest_counts_as_zero_holding(scenario):
    next(a for a in plan(scenario, "P1").assignments if a.flight_id == "F1").landing_min = 8
    assert estimate_plan(scenario, plan(scenario, "P1")).flights[0].holding_min == 0


def test_scheduled_order_baseline_respects_wake_separation(scenario):
    # F1 lands 10; F2 scheduled 12 must wait for the 3 min M->M gap; F3 at 22.
    landings, reason = scheduled_order_baseline(scenario)
    assert reason is None
    assert landings == {"F1": 10, "F2": 13, "F3": 22}


def test_baseline_separation_equality_is_allowed(scenario):
    scenario.atc.separation_min["M"]["M"] = 2  # F2 at exactly 10 + 2 = 12.
    assert scheduled_order_baseline(scenario)[0]["F2"] == 12


def test_baseline_waits_for_open_runway_window(scenario):
    scenario.atc.runway_open_windows = [Interval(start_min=15, end_min=120)]
    landings, _ = scheduled_order_baseline(scenario)
    assert landings == {"F1": 15, "F2": 18, "F3": 22}


def test_missing_separation_makes_baseline_unknown_not_guessed(scenario):
    scenario.atc.separation_min = {}
    panel = build_panel(scenario)
    assert panel.baseline.status == "UNKNOWN"
    assert "wake separation" in panel.baseline.unknown_reason
    assert all(c.status == "UNKNOWN" and c.co2_saved_kg is None for c in panel.comparisons)


def test_fixture_selected_plan_reports_extra_co2_honestly(scenario):
    panel = build_panel(scenario, hard_pass=hard_check_results(scenario))
    p1 = next(c for c in panel.comparisons if c.plan_id == "P1")
    # Baseline holds F2 1 min (50 kg); P1 holds F2 2 min (100 kg).
    assert (p1.hard_constraints, p1.fuel_saved_kg, p1.co2_saved_kg) == ("PASS", -50, -158.0)
    assert p1.headline.startswith("P1 uses about 158 kg more CO2 (50 kg more fuel)")


def test_infeasible_plan_is_never_reported_as_a_saving(scenario):
    panel = build_panel(scenario, hard_pass=hard_check_results(scenario))
    p0 = next(c for c in panel.comparisons if c.plan_id == "P0")
    assert p0.hard_constraints == "FAIL"
    assert "saves" not in p0.headline
    assert "not an achievable saving" in p0.headline
    assert "infeasible" in render_text(panel)
    # P0 burns 50 kg less than the baseline, but the JSON must not expose that
    # as a number an API client could render as a saving.
    assert p0.fuel_saved_kg is None and p0.co2_saved_kg is None


def test_api_withholds_savings_for_infeasible_plans():
    body = TestClient(create_fuel_app()).get("/scenarios/example/fuel-co2").json()
    by_id = {c["plan_id"]: c for c in body["comparisons"]}
    assert by_id["P0"]["hard_constraints"] == "FAIL"
    assert by_id["P0"]["fuel_saved_kg"] is None and by_id["P0"]["co2_saved_kg"] is None
    assert by_id["P1"]["co2_saved_kg"] == -158.0


def test_saving_headline_wording():
    cmp = compare(estimate("PX", 100), estimate("BASE", 150), "PASS")
    assert cmp.fuel_saved_kg == 50 and cmp.co2_saved_kg == 158.0
    assert cmp.headline.startswith(
        "PX saves about 158 kg CO2 (50 kg fuel) against landing in scheduled order.")


def test_every_output_is_labelled_as_a_modelled_estimate(scenario):
    panel = build_panel(scenario, hard_pass=hard_check_results(scenario))
    assert panel.label == ESTIMATE_LABEL
    assert all(ESTIMATE_LABEL in c.headline for c in panel.comparisons)
    text = render_text(panel, highlight="P1")
    assert text.count(ESTIMATE_LABEL) >= 3
    assert any("not modelled" in a for a in panel.assumptions)


def test_panel_does_not_mutate_scenario(scenario):
    before = scenario.model_dump_json()
    build_panel(scenario, hard_pass=hard_check_results(scenario))
    assert scenario.model_dump_json() == before


def test_api_panel_for_example_and_finished_run(tmp_path):
    client = TestClient(create_fuel_app(model=OfflineGateway(), log_dir=tmp_path))
    example = client.get("/scenarios/example/fuel-co2").json()
    assert example["label"] == ESTIMATE_LABEL

    run = client.post("/runs", json=ScenarioInput.model_validate_json(
        EXAMPLE.read_bytes()).model_dump(mode="json")).json()
    body = client.get(f"/runs/{run['run_id']}/fuel-co2").json()
    assert body["selected_plan_id"] == run["selected_plan_id"]
    assert ESTIMATE_LABEL in body["headline"]
    assert client.get("/runs/" + "0" * 32 + "/fuel-co2").status_code == 404
    # Existing routes are unchanged and still served.
    assert client.get("/health").json()["status"] == "ok"
