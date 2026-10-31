"""Ground evaluator tests against the v1 fixture and boundary mutations."""
from pathlib import Path

import pytest

from contracts.models import Interval, ScenarioInput, plan_hash, scenario_hash
from domains.ground import evaluate_ground, hard_checks_pass, validate_ground_inputs

FIXTURE = Path(__file__).resolve().parents[1] / "docs/examples/coordination-scenario-v1.json"


@pytest.fixture
def scenario() -> ScenarioInput:
    return ScenarioInput.model_validate_json(FIXTURE.read_text())


def plan(s, plan_id):
    return next(p for p in s.plans if p.plan_id == plan_id)


def assignment(s, plan_id, flight):
    return next(a for a in plan(s, plan_id).assignments if a.flight_id == flight)


def run(s: ScenarioInput, plan_id: str):
    return evaluate_ground(plan(s, plan_id), s.shared, s.ground,
                           scenario_digest=scenario_hash(s))


def check(report, rule, flight):
    return next(c for c in report.checks if c.rule_id == rule and c.flight_ids == [flight])


def service(s, flight):
    return next(x for x in s.ground.services if x.flight_id == flight)


def crew(s, crew_id):
    return next(c for c in s.ground.crews if c.crew_id == crew_id)


def gate(s, gate_id):
    return next(g for g in s.ground.gates if g.gate_id == gate_id)


def test_fixture_inputs_valid(scenario):
    assert validate_ground_inputs(scenario.shared, scenario.ground) == []


def test_p0_fails_gate_overlap(scenario):
    report = run(scenario, "P0")
    assert not hard_checks_pass(report)
    assert check(report, "GROUND_GATE", "F1").status == "FAIL"
    assert "overlaps F2" in check(report, "GROUND_GATE", "F1").observed
    assert check(report, "GROUND_GATE", "F2").status == "FAIL"


@pytest.mark.parametrize("plan_id", ["P1", "P2"])
def test_p1_p2_pass_ground(scenario, plan_id):
    assert hard_checks_pass(run(scenario, plan_id))


def test_fixture_metrics_match_hand_calculation(scenario):
    # P1 F3 service [24,32) on C1 with shift_end 30 -> 2 overtime.
    assert run(scenario, "P1").metrics == {
        "overtime_min": 2, "turnaround_delay_min": 0, "gate_busy_min": 24}
    # P2 F3 service [28,36) on C1 -> 6 overtime.
    assert run(scenario, "P2").metrics == {
        "overtime_min": 6, "turnaround_delay_min": 0, "gate_busy_min": 24}


def test_gate_busy_is_union_per_gate(scenario):
    # P0: G1 holds [12,20) and [14,22) -> union [12,22) = 10; G2 [24,32) = 8.
    assert run(scenario, "P0").metrics["gate_busy_min"] == 18


def test_gate_busy_clipped_to_horizon(scenario):
    scenario.shared.horizon_end_min = 30
    # P1: G1 [12,20) + [24,30) = 14; G2 [16,24) = 8.
    assert run(scenario, "P1").metrics["gate_busy_min"] == 22


def test_touching_gate_intervals_do_not_overlap(scenario):
    # P1 G1: F1 [12,24) now touches F3 [24,32).
    assignment(scenario, "P1", "F1").gate_out_min = 24
    report = run(scenario, "P1")
    assert check(report, "GROUND_GATE", "F1").status == "PASS"
    assert check(report, "GROUND_GATE", "F3").status == "PASS"
    assert report.metrics["turnaround_delay_min"] == 4


def test_existing_occupancy_overlap_fails_touching_passes(scenario):
    gate(scenario, "G2").occupied_windows = [Interval(start_min=23, end_min=30)]
    assert check(run(scenario, "P1"), "GROUND_GATE", "F2").status == "FAIL"
    gate(scenario, "G2").occupied_windows = [Interval(start_min=24, end_min=30)]
    assert check(run(scenario, "P1"), "GROUND_GATE", "F2").status == "PASS"


def test_incompatible_gate_fails(scenario):
    gate(scenario, "G2").compatible_flight_ids = ["F1", "F3"]
    c = check(run(scenario, "P1"), "GROUND_GATE", "F2")
    assert c.status == "FAIL"
    assert "not compatible" in c.observed


def test_undeclared_gate_fails(scenario):
    assignment(scenario, "P1", "F2").gate_id = "G9"
    assert check(run(scenario, "P1"), "GROUND_GATE", "F2").status == "FAIL"


def test_short_turnaround_fails(scenario):
    service(scenario, "F1").min_turnaround_min = 9  # P1 F1 ready at 21 > gate_out 20.
    report = run(scenario, "P1")
    assert check(report, "GROUND_TURN", "F1").status == "FAIL"
    assert not hard_checks_pass(report)


def test_unavailable_crew_fails(scenario):
    crew(scenario, "C1").available_windows = [Interval(start_min=0, end_min=30)]
    report = run(scenario, "P1")  # F3 service [24,32) leaves the window.
    c = check(report, "GROUND_CREW", "F3")
    assert c.status == "FAIL"
    assert "outside every available window" in c.observed


def test_two_simultaneous_jobs_on_one_crew_fail(scenario):
    service(scenario, "F2").crew_id = "C1"  # P1 F1 [12,20) and F2 [16,24) on C1.
    report = run(scenario, "P1")
    assert check(report, "GROUND_CREW", "F1").status == "FAIL"
    assert check(report, "GROUND_CREW", "F2").status == "FAIL"


def test_touching_crew_services_pass(scenario):
    # P2 on one crew: F1 [16,20), F2 [20,28), F3 [28,36) touch but never overlap.
    service(scenario, "F1").min_turnaround_min = 4
    service(scenario, "F2").crew_id = "C1"
    report = run(scenario, "P2")
    assert all(check(report, "GROUND_CREW", f).status == "PASS" for f in ("F1", "F2", "F3"))
    # Overtime past shift_end 30: F3 [28,36) -> 6. Turnaround slack: F1 24-20 = 4.
    assert report.metrics["overtime_min"] == 6
    assert report.metrics["turnaround_delay_min"] == 4


def test_missing_service_is_invalid_input_and_unknown(scenario):
    scenario.ground.services = [x for x in scenario.ground.services if x.flight_id != "F2"]
    assert any("missing service for flight F2" in p
               for p in validate_ground_inputs(scenario.shared, scenario.ground))
    report = run(scenario, "P1")
    assert check(report, "GROUND_TURN", "F2").status == "UNKNOWN"
    assert check(report, "GROUND_CREW", "F2").status == "UNKNOWN"
    assert not hard_checks_pass(report)


def test_invalid_inputs_reported(scenario):
    service(scenario, "F1").crew_id = "C9"
    crew(scenario, "C2").available_windows = [Interval(start_min=5, end_min=5)]
    problems = validate_ground_inputs(scenario.shared, scenario.ground)
    assert any("C9 not declared" in p for p in problems)
    assert any("positive length" in p for p in problems)
    assert check(run(scenario, "P1"), "GROUND_CREW", "F1").status == "UNKNOWN"


def test_check_ids_bound_to_scenario_and_plan(scenario):
    digest = scenario_hash(scenario)
    report = run(scenario, "P1")
    ids = [c.check_id for c in report.checks]
    assert len(ids) == len(set(ids)) == 9
    assert all(i.startswith(f"ground:{digest}:{plan_hash(plan(scenario, 'P1'))}:") for i in ids)
    assert "source:seed-76" in check(report, "GROUND_GATE", "F1").evidence_refs
    assert "source:seed-76" not in check(report, "GROUND_GATE", "F2").evidence_refs


def test_evaluator_does_not_mutate_inputs(scenario):
    before = scenario.model_dump_json()
    for plan_id in ("P0", "P1", "P2"):
        run(scenario, plan_id)
    assert scenario.model_dump_json() == before
