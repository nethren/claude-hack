"""ATC evaluator tests: section 10 owner-A checks plus boundary and mutation cases."""
from __future__ import annotations

from pathlib import Path

import pytest

from contracts.models import ScenarioInput, plan_hash, scenario_hash
from domains.atc import evaluate_atc, hard_checks_pass

FIXTURE = Path(__file__).resolve().parents[1] / "docs/examples/coordination-scenario-v1.json"


def load(**changes) -> ScenarioInput:
    """Fixture scenario, optionally with top-level sections replaced via dict edits."""
    data = ScenarioInput.model_validate_json(FIXTURE.read_text(encoding="utf-8")).model_dump(mode="json")
    for edit in changes.values():
        edit(data)
    return ScenarioInput.model_validate(data)


def report(scenario: ScenarioInput, plan_id: str):
    plan = next(p for p in scenario.plans if p.plan_id == plan_id)
    return evaluate_atc(plan, scenario.shared, scenario.atc, scenario_digest=scenario_hash(scenario))


def status(rep, rule: str, *flights: str) -> str:
    matches = [c for c in rep.checks if c.rule_id == rule and c.flight_ids == list(flights)]
    assert len(matches) == 1, f"expected one {rule} check for {flights}, got {matches}"
    return matches[0].status


def test_p0_fails_wake_separation_only_on_f1_f2():
    rep = report(load(), "P0")
    assert status(rep, "ATC_WAKE", "F1", "F2") == "FAIL"
    assert status(rep, "ATC_WAKE", "F2", "F3") == "PASS"
    assert not hard_checks_pass(rep)
    failing = [c for c in rep.checks if c.status != "PASS"]
    assert [c.rule_id for c in failing] == ["ATC_WAKE"]
    assert "gap 2" in failing[0].observed and ">= 3" in failing[0].required


@pytest.mark.parametrize("plan_id, delay", [("P1", 2), ("P2", 14)])
def test_p1_p2_pass_with_fixture_metrics(plan_id, delay):
    rep = report(load(), plan_id)
    assert hard_checks_pass(rep)
    assert rep.metrics == {"throughput_count": 3, "additional_delay_min": delay}


def test_every_rule_checked_for_every_flight_and_pair():
    rep = report(load(), "P1")
    rules = [(c.rule_id, tuple(c.flight_ids)) for c in rep.checks]
    for f in ("F1", "F2", "F3"):
        assert ("ATC_RUNWAY", (f,)) in rules and ("ATC_TAXI", (f,)) in rules
    assert ("ATC_WAKE", ("F1", "F2")) in rules and ("ATC_WAKE", ("F2", "F3")) in rules
    assert len(rep.checks) == 8
    assert all(c.severity == "HARD" for c in rep.checks)


def test_check_ids_bind_scenario_and_plan_hashes():
    s = load()
    rep = report(s, "P1")
    p1 = next(p for p in s.plans if p.plan_id == "P1")
    assert rep.role == "atc" and rep.scenario_hash == scenario_hash(s) and rep.plan_hash == plan_hash(p1)
    for c in rep.checks:
        assert c.check_id == ":".join(["atc", rep.scenario_hash, rep.plan_hash, c.rule_id, *c.flight_ids])
    f1_refs = next(c for c in rep.checks if c.rule_id == "ATC_RUNWAY" and c.flight_ids == ["F1"]).evidence_refs
    assert f1_refs == ["overlay:atc", "rule:ATC_RUNWAY", "source:seed-76"]


def test_taxi_blocked_during_traversal_fails():
    def block_t1(d):
        d["atc"]["routes"][0]["blocked_windows"] = [{"start_min": 11, "end_min": 12}]
    rep = report(load(edit=block_t1), "P1")
    assert status(rep, "ATC_TAXI", "F1") == "FAIL"  # F1 traverses T1 over [10,12)
    assert status(rep, "ATC_TAXI", "F2") == "PASS"


def test_taxi_block_touching_traversal_does_not_overlap():
    def touch(d):
        d["atc"]["routes"][0]["blocked_windows"] = [{"start_min": 0, "end_min": 10}, {"start_min": 12, "end_min": 14}]
    rep = report(load(edit=touch), "P1")
    assert status(rep, "ATC_TAXI", "F1") == "PASS"


def test_wake_gap_equal_to_required_passes():
    def sep4(d):
        d["atc"]["separation_min"]["M"]["M"] = 4
    rep = report(load(edit=sep4), "P1")  # F1 10 -> F2 14 is exactly 4
    assert status(rep, "ATC_WAKE", "F1", "F2") == "PASS"

    def sep5(d):
        d["atc"]["separation_min"]["M"]["M"] = 5
    assert status(report(load(edit=sep5), "P1"), "ATC_WAKE", "F1", "F2") == "FAIL"


def test_runway_occupancy_dominates_smaller_matrix_gap():
    def occupy(d):
        d["atc"]["runway_occupancy_min"] = 5
    rep = report(load(edit=occupy), "P1")  # gap 4 < occupancy 5
    assert status(rep, "ATC_WAKE", "F1", "F2") == "FAIL"


def test_missing_wake_class_is_unknown_never_pass():
    def drop(d):
        del d["atc"]["wake_class_by_flight"]["F2"]
    rep = report(load(edit=drop), "P1")
    assert status(rep, "ATC_WAKE", "F1", "F2") == "UNKNOWN"
    assert status(rep, "ATC_WAKE", "F2", "F3") == "UNKNOWN"
    assert not hard_checks_pass(rep)


def test_missing_matrix_entry_is_unknown():
    def heavy(d):
        d["atc"]["wake_class_by_flight"]["F2"] = "H"
    rep = report(load(edit=heavy), "P1")
    assert status(rep, "ATC_WAKE", "F1", "F2") == "UNKNOWN"
    assert not hard_checks_pass(rep)


def test_runway_closed_window_fails_and_touching_end_passes():
    def close(d):
        d["atc"]["runway_open_windows"] = [{"start_min": 0, "end_min": 23}]
    rep = report(load(edit=close), "P1")
    assert status(rep, "ATC_RUNWAY", "F3") == "PASS"  # [22,23) fits exactly
    def tighter(d):
        d["atc"]["runway_open_windows"] = [{"start_min": 0, "end_min": 22}]
    assert status(report(load(edit=tighter), "P1"), "ATC_RUNWAY", "F3") == "FAIL"


def test_undeclared_route_or_mismatched_taxi_time_is_unknown():
    def mismatch(d):
        d["atc"]["routes"][0]["taxi_in_min"] = 3
    assert status(report(load(edit=mismatch), "P1"), "ATC_TAXI", "F1") == "UNKNOWN"

    def drop_route(d):
        d["atc"]["routes"] = d["atc"]["routes"][1:]
    assert status(report(load(edit=drop_route), "P1"), "ATC_TAXI", "F1") == "UNKNOWN"


def test_throughput_uses_shared_horizon():
    def horizon(d):
        d["shared"]["horizon_end_min"] = 22
    assert report(load(edit=horizon), "P1").metrics["throughput_count"] == 2  # F3 lands at 22


def test_single_flight_wake_is_not_applicable():
    def one(d):
        d["plans"] = [{"plan_id": "S", "assignments": [d["plans"][1]["assignments"][0]]}]
    s = load(edit=one)
    rep = evaluate_atc(s.plans[0], s.shared, s.atc, scenario_digest=scenario_hash(s))
    assert status(rep, "ATC_WAKE", "F1") == "NOT_APPLICABLE"
    assert hard_checks_pass(rep)


def test_order_independent_and_mutation_recomputes():
    s = load()
    p1 = next(p for p in s.plans if p.plan_id == "P1")
    shuffled = p1.model_copy(update={"assignments": list(reversed(p1.assignments))})
    a = evaluate_atc(p1, s.shared, s.atc, scenario_digest="0" * 64)
    b = evaluate_atc(shuffled, s.shared, s.atc, scenario_digest="0" * 64)
    assert a == b

    def shift(d):  # move F2 later in P0 so the F1/F2 gap becomes legal
        d["plans"][0]["assignments"][1]["landing_min"] = 13
    assert status(report(load(edit=shift), "P0"), "ATC_WAKE", "F1", "F2") == "PASS"


def test_duplicate_flight_assignment_rejected():
    def dup(d):
        d["plans"][1]["assignments"][1]["flight_id"] = "F1"
    s = load(edit=dup)
    with pytest.raises(ValueError, match="duplicate"):
        report(s, "P1")
