"""ATC deterministic evaluator (protocol 1.0, C2-09 to C2-11).

Pure function: no I/O, model calls or global state. Every hard rule is checked
for every applicable flight or adjacent landing pair, and missing inputs give
UNKNOWN, never PASS. Rule definitions follow section 6 of
docs/ai-orchestration-architecture.md:

- ATC_RUNWAY: runway occupancy [landing, landing + occupancy) lies inside one
  open runway window.
- ATC_WAKE: landings sorted by (landing_min, flight_id); each adjacent gap is
  >= max(runway_occupancy_min, separation_min[leader_class][follower_class]).
- ATC_TAXI: taxi traversal [landing, gate_in) intersects no blocked window of
  the assigned route.

Metrics: throughput_count (flights landing before shared.horizon_end_min, an
airport-arrival proxy for sector throughput) and additional_delay_min (sum of
max(0, landing - scheduled landing)). Assignments are assumed to have passed
D's preflight (known flights, one assignment each).
"""
from __future__ import annotations

from contracts.models import (
    ATCState,
    Assignment,
    Check,
    DomainReport,
    Interval,
    Plan,
    SharedInput,
    plan_hash,
)

RULES_VERSION = "atc-rules-1.0"
RULE_RUNWAY = "ATC_RUNWAY"
RULE_WAKE = "ATC_WAKE"
RULE_TAXI = "ATC_TAXI"
METRIC_KEYS = ("throughput_count", "additional_delay_min")


def _fmt(interval: tuple[int, int]) -> str:
    return f"[{interval[0]},{interval[1]})"


def _overlaps(a: tuple[int, int], b: Interval) -> bool:
    return a[0] < b.end_min and b.start_min < a[1]


def _contained(a: tuple[int, int], b: Interval) -> bool:
    return b.start_min <= a[0] and a[1] <= b.end_min


class _Builder:
    """Collects checks bound to one scenario hash and plan hash."""

    def __init__(self, shared: SharedInput, scenario_digest: str, plan_digest: str):
        self.scenario_digest = scenario_digest
        self.plan_digest = plan_digest
        self.source_by_flight = {
            f.flight_id: f.source_id for f in shared.flights if f.source_id is not None
        }
        self.checks: list[Check] = []

    def add(self, rule: str, flight_ids: list[str], status: str, observed: str, required: str) -> None:
        refs = ["overlay:atc", f"rule:{rule}"]
        refs += [
            f"source:{self.source_by_flight[f]}" for f in flight_ids if f in self.source_by_flight
        ]
        self.checks.append(Check(
            check_id=":".join(["atc", self.scenario_digest, self.plan_digest, rule, *flight_ids]),
            rule_id=rule,
            flight_ids=flight_ids,
            severity="HARD",
            status=status,
            observed=observed,
            required=required,
            evidence_refs=refs,
        ))


def _check_runway(b: _Builder, a: Assignment, state: ATCState) -> None:
    occupancy = (a.landing_min, a.landing_min + state.runway_occupancy_min)
    windows = ", ".join(_fmt((w.start_min, w.end_min)) for w in state.runway_open_windows)
    required = f"inside an open runway window: {windows or 'none declared'}"
    ok = any(_contained(occupancy, w) for w in state.runway_open_windows)
    b.add(RULE_RUNWAY, [a.flight_id], "PASS" if ok else "FAIL",
          f"runway occupancy {_fmt(occupancy)}", required)


def _check_wake(b: _Builder, ordered: list[Assignment], state: ATCState) -> None:
    if len(ordered) < 2:
        b.add(RULE_WAKE, [a.flight_id for a in ordered], "NOT_APPLICABLE",
              f"{len(ordered)} landing in plan", "wake separation applies to adjacent landing pairs")
        return
    for leader, follower in zip(ordered, ordered[1:]):
        pair = [leader.flight_id, follower.flight_id]
        gap = follower.landing_min - leader.landing_min
        observed = f"{leader.flight_id}->{follower.flight_id} gap {gap} min"
        lead_cls = state.wake_class_by_flight.get(leader.flight_id)
        follow_cls = state.wake_class_by_flight.get(follower.flight_id)
        if lead_cls is None or follow_cls is None:
            missing = leader.flight_id if lead_cls is None else follower.flight_id
            b.add(RULE_WAKE, pair, "UNKNOWN", observed, f"wake class for {missing} is not declared")
            continue
        matrix_gap = state.separation_min.get(lead_cls, {}).get(follow_cls)
        if matrix_gap is None:
            b.add(RULE_WAKE, pair, "UNKNOWN", observed,
                  f"separation for leader {lead_cls} / follower {follow_cls} is not declared")
            continue
        needed = max(state.runway_occupancy_min, matrix_gap)
        b.add(RULE_WAKE, pair, "PASS" if gap >= needed else "FAIL", observed,
              f">= {needed} min ({lead_cls}->{follow_cls} separation {matrix_gap}, "
              f"runway occupancy {state.runway_occupancy_min})")


def _check_taxi(b: _Builder, a: Assignment, shared: SharedInput, state: ATCState) -> None:
    route = next((r for r in state.routes if r.route_id == a.taxi_route_id), None)
    taxi_in = shared.taxi_in_min_by_route.get(a.taxi_route_id)
    if route is None or taxi_in is None:
        b.add(RULE_TAXI, [a.flight_id], "UNKNOWN", f"route {a.taxi_route_id}",
              f"route {a.taxi_route_id} must be declared in ATC state and shared taxi times")
        return
    if route.taxi_in_min != taxi_in:
        b.add(RULE_TAXI, [a.flight_id], "UNKNOWN",
              f"route {a.taxi_route_id} taxi-in {route.taxi_in_min} (ATC) vs {taxi_in} (shared)",
              "ATC and shared taxi-in durations must match")
        return
    traversal = (a.landing_min, a.landing_min + taxi_in)
    hits = [w for w in route.blocked_windows if _overlaps(traversal, w)]
    blocked = ", ".join(_fmt((w.start_min, w.end_min)) for w in route.blocked_windows)
    b.add(RULE_TAXI, [a.flight_id], "FAIL" if hits else "PASS",
          f"{a.taxi_route_id} traversal {_fmt(traversal)}"
          + (f" intersects blocked {', '.join(_fmt((w.start_min, w.end_min)) for w in hits)}" if hits else ""),
          f"no overlap with {a.taxi_route_id} blocked windows: {blocked or 'none'}")


def evaluate_atc(
    plan: Plan, shared: SharedInput, state: ATCState, *, scenario_digest: str
) -> DomainReport:
    flight_ids = [a.flight_id for a in plan.assignments]
    if len(set(flight_ids)) != len(flight_ids):
        raise ValueError(f"plan {plan.plan_id} has duplicate flight assignments: {flight_ids}")
    if not plan.assignments:
        raise ValueError(f"plan {plan.plan_id} has no assignments")
    b = _Builder(shared, scenario_digest, plan_hash(plan))

    ordered = sorted(plan.assignments, key=lambda a: (a.landing_min, a.flight_id))
    for a in ordered:
        _check_runway(b, a, state)
    _check_wake(b, ordered, state)
    for a in ordered:
        _check_taxi(b, a, shared, state)

    scheduled = {f.flight_id: f.scheduled_landing_min for f in shared.flights}
    metrics = {
        "throughput_count": sum(a.landing_min < shared.horizon_end_min for a in plan.assignments),
        "additional_delay_min": sum(
            max(0, a.landing_min - scheduled[a.flight_id])
            for a in plan.assignments if a.flight_id in scheduled
        ),
    }
    return DomainReport(
        role="atc",
        scenario_hash=scenario_digest,
        plan_hash=b.plan_digest,
        checks=b.checks,
        metrics=metrics,
    )


def hard_checks_pass(report: DomainReport) -> bool:
    """True only when the report has checks and every HARD check is PASS or NOT_APPLICABLE."""
    hard = [c for c in report.checks if c.severity == "HARD"]
    return bool(hard) and all(c.status in ("PASS", "NOT_APPLICABLE") for c in hard)
