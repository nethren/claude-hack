"""Pilot evaluator tests against the v1 fixture and boundary mutations."""
from pathlib import Path

import pytest

from contracts.models import ScenarioInput, plan_hash, scenario_hash
from domains.pilot import evaluate_pilot, hard_checks_pass, validate_pilot_inputs

FIXTURE = Path(__file__).resolve().parents[1] / "docs/examples/coordination-scenario-v1.json"


@pytest.fixture
def scenario() -> ScenarioInput:
    return ScenarioInput.model_validate_json(FIXTURE.read_text())


def run(s: ScenarioInput, plan_id: str):
    plan = next(p for p in s.plans if p.plan_id == plan_id)
    return evaluate_pilot(plan, s.shared, s.pilot, scenario_digest=scenario_hash(s))


def check(report, rule, flight):
    return next(c for c in report.checks if c.rule_id == rule and c.flight_ids == [flight])


def limits(s, flight):
    return next(l for l in s.pilot.limits if l.flight_id == flight)


def test_fixture_inputs_valid(scenario):
    assert validate_pilot_inputs(scenario.shared, scenario.pilot) == []


@pytest.mark.parametrize("plan_id", ["P0", "P1", "P2"])
def test_fixture_plans_pass_pilot_hard_checks(scenario, plan_id):
    assert hard_checks_pass(run(scenario, plan_id))


def test_fixture_metrics_match_hand_calculation(scenario):
    assert run(scenario, "P1").metrics == {"turbulence_units": 3, "missed_connections": 0}
    assert run(scenario, "P2").metrics == {"turbulence_units": 1, "missed_connections": 2}


def test_fuel_exactly_at_reserve_passes(scenario):
    c = check(run(scenario, "P2"), "PILOT_FUEL", "F3")
    assert c.status == "PASS"
    assert "fuel_at_landing_kg=800" in c.observed


def test_fuel_one_kg_below_reserve_fails(scenario):
    limits(scenario, "F3").fuel_at_earliest_landing_kg = 999
    report = run(scenario, "P2")
    assert check(report, "PILOT_FUEL", "F3").status == "FAIL"
    assert not hard_checks_pass(report)


def test_turbulence_above_cap_fails_below_cap_is_cost(scenario):
    lim = limits(scenario, "F2")
    lim.max_turbulence_units = 1
    lim.turbulence_by_landing_min["14"] = 2
    assert check(run(scenario, "P1"), "PILOT_TURBULENCE", "F2").status == "FAIL"

    lim.turbulence_by_landing_min["14"] = 1
    report = run(scenario, "P1")
    assert check(report, "PILOT_TURBULENCE", "F2").status == "PASS"
    assert report.metrics["turbulence_units"] == 3


def test_missing_turbulence_exposure_is_unknown_not_pass(scenario):
    del limits(scenario, "F2").turbulence_by_landing_min["14"]
    assert validate_pilot_inputs(scenario.shared, scenario.pilot)
    report = run(scenario, "P1")
    assert check(report, "PILOT_TURBULENCE", "F2").status == "UNKNOWN"
    assert not hard_checks_pass(report)


def test_connection_at_deadline_passes_one_minute_late_fails(scenario):
    # P1: F1 gate_in = 10 + 2 = 12, + transfer 5 = 17.
    lim = limits(scenario, "F1")
    lim.connection_deadline_min = 17
    report = run(scenario, "P1")
    assert check(report, "PILOT_CONNECTION", "F1").status == "PASS"
    assert report.metrics["missed_connections"] == 0

    lim.connection_deadline_min = 16
    report = run(scenario, "P1")
    assert check(report, "PILOT_CONNECTION", "F1").status == "FAIL"
    assert report.metrics["missed_connections"] == 2
    assert hard_checks_pass(report)  # Connections are a soft cost, not a veto.


def test_positive_passengers_without_deadline_is_invalid_input(scenario):
    limits(scenario, "F1").connection_deadline_min = None
    problems = validate_pilot_inputs(scenario.shared, scenario.pilot)
    assert any("connection_deadline_min" in p for p in problems)
    assert check(run(scenario, "P1"), "PILOT_CONNECTION", "F1").status == "UNKNOWN"


def test_zero_passengers_is_explicit_not_applicable(scenario):
    c = check(run(scenario, "P1"), "PILOT_CONNECTION", "F2")
    assert c.status == "NOT_APPLICABLE"
    assert c.severity == "SOFT"


def test_landing_before_earliest_fails_and_fuel_unknown(scenario):
    limits(scenario, "F1").earliest_landing_min = 11
    report = run(scenario, "P1")
    assert check(report, "PILOT_EARLIEST", "F1").status == "FAIL"
    assert check(report, "PILOT_FUEL", "F1").status == "UNKNOWN"


def test_missing_limits_gives_unknown_hard_checks(scenario):
    scenario.pilot.limits = [l for l in scenario.pilot.limits if l.flight_id != "F3"]
    assert validate_pilot_inputs(scenario.shared, scenario.pilot)
    report = run(scenario, "P1")
    f3 = [c for c in report.checks if c.flight_ids == ["F3"]]
    assert {c.status for c in f3} == {"UNKNOWN"}
    assert not hard_checks_pass(report)


def test_check_ids_bound_to_scenario_and_plan(scenario):
    digest = scenario_hash(scenario)
    p1 = next(p for p in scenario.plans if p.plan_id == "P1")
    report = run(scenario, "P1")
    ids = [c.check_id for c in report.checks]
    assert len(ids) == len(set(ids))
    assert all(i.startswith(f"pilot:{digest}:{plan_hash(p1)}:") for i in ids)
    assert report.plan_hash == plan_hash(p1)
    assert "source:seed-76" in check(report, "PILOT_FUEL", "F1").evidence_refs
    assert "source:seed-76" not in check(report, "PILOT_FUEL", "F2").evidence_refs


def test_evaluator_does_not_mutate_inputs(scenario):
    before = scenario.model_dump_json()
    for plan_id in ("P0", "P1", "P2"):
        run(scenario, plan_id)
    assert scenario.model_dump_json() == before
