"""Ground domain evaluator (C2-16 to C2-18).

Pure and deterministic: no filesystem, network, model calls or mutation of its
inputs. Units: integer minutes from the scenario origin. Intervals are
half-open [start_min, end_min); touching boundaries do not overlap.

Simplifications shown alongside the simulation: gate_busy_min is fixed-horizon
occupancy, not a complete gate-capacity model; crew shift end is a soft-cost
boundary (overtime), never permission to use unavailable crew.
"""
from __future__ import annotations

from contracts.models import (
    Assignment,
    Check,
    Crew,
    DomainReport,
    Gate,
    GroundService,
    GroundState,
    Interval,
    Plan,
    SharedInput,
    plan_hash,
)

RULES_VERSION = "ground-rules-1.0"

RULE_GATE = "GROUND_GATE"
RULE_TURN = "GROUND_TURN"
RULE_CREW = "GROUND_CREW"
HARD_RULES = (RULE_GATE, RULE_TURN, RULE_CREW)

METRIC_KEYS = ("overtime_min", "turnaround_delay_min", "gate_busy_min")

OVERLAY_REF = "overlay:ground"


def overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def validate_ground_inputs(shared: SharedInput, state: GroundState) -> list[str]:
    """Return preflight problems for D's INPUT_ERROR path; empty means valid.

    A missing hard-limit input is never filled in by the evaluator or a model.
    """
    problems: list[str] = []
    flight_ids = {f.flight_id for f in shared.flights}

    def unique(kind: str, ids: list[str]) -> None:
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            problems.append(f"ground.{kind}: duplicate ids {dupes}")

    def positive(where: str, windows: list[Interval]) -> None:
        for w in windows:
            if w.end_min <= w.start_min:
                problems.append(f"{where}: interval [{w.start_min},{w.end_min}) "
                                "must have positive length")

    unique("gates", [g.gate_id for g in state.gates])
    unique("crews", [c.crew_id for c in state.crews])
    unique("services", [s.flight_id for s in state.services])

    gate_ids = {g.gate_id for g in state.gates}
    for gid in shared.options.gate_ids:
        if gid not in gate_ids:
            problems.append(f"shared.options.gate_ids: {gid} not declared in ground.gates")
    for g in state.gates:
        positive(f"ground.gates[{g.gate_id}].occupied_windows", g.occupied_windows)
        for fid in g.compatible_flight_ids:
            if fid not in flight_ids:
                problems.append(f"ground.gates[{g.gate_id}].compatible_flight_ids: "
                                f"{fid} not in shared.flights")

    crew_ids = {c.crew_id for c in state.crews}
    for c in state.crews:
        positive(f"ground.crews[{c.crew_id}].available_windows", c.available_windows)

    serviced = {s.flight_id for s in state.services}
    for s in state.services:
        if s.flight_id not in flight_ids:
            problems.append(f"ground.services[{s.flight_id}]: flight_id not in shared.flights")
        if s.crew_id not in crew_ids:
            problems.append(f"ground.services[{s.flight_id}].crew_id: {s.crew_id} "
                            "not declared in ground.crews")
    for fid in sorted(flight_ids - serviced):
        problems.append(f"ground.services: missing service for flight {fid}")
    return problems


def evaluate_ground(
    plan: Plan, shared: SharedInput, state: GroundState, *, scenario_digest: str
) -> DomainReport:
    digest = plan_hash(plan)
    gates = {g.gate_id: g for g in state.gates}
    crews = {c.crew_id: c for c in state.crews}
    services = {s.flight_id: s for s in state.services}
    assignments = {a.flight_id: a for a in plan.assignments}
    source_refs = {
        f.flight_id: f"source:{f.source_id}"
        for f in shared.flights if f.source_id is not None
    }

    flight_ids = [f.flight_id for f in shared.flights]
    flight_ids += sorted(fid for fid in assignments if fid not in flight_ids)

    def make(rule: str, fid: str, status: str, observed: str, required: str) -> Check:
        refs = [OVERLAY_REF, f"rule:{rule}"]
        if fid in source_refs:
            refs.insert(0, source_refs[fid])
        return Check(
            check_id=f"ground:{scenario_digest}:{digest}:{rule}:{fid}",
            rule_id=rule, flight_ids=[fid], severity="HARD", status=status,
            observed=observed, required=required, evidence_refs=refs,
        )

    # Derived times shared by every rule: gate_in and the service interval.
    gate_in: dict[str, int] = {}
    service_iv: dict[str, tuple[int, int]] = {}
    for fid, a in assignments.items():
        taxi = shared.taxi_in_min_by_route.get(a.taxi_route_id)
        if taxi is None:
            continue
        gate_in[fid] = a.landing_min + taxi
        if fid in services:
            start = gate_in[fid]
            service_iv[fid] = (start, start + services[fid].min_turnaround_min)

    checks: list[Check] = []
    overtime = 0
    turnaround_delay = 0

    for fid in flight_ids:
        a = assignments.get(fid)
        if a is None or fid not in gate_in:
            reason = (f"no assignment for flight {fid}" if a is None
                      else f"no taxi time for route {a.taxi_route_id}")
            for rule in HARD_RULES:
                checks.append(make(rule, fid, "UNKNOWN", reason,
                                   "exactly one assignment with a declared taxi route"))
            continue

        checks.append(_gate(a, gate_in, assignments, gates, make))

        svc = services.get(fid)
        if svc is None:
            for rule in (RULE_TURN, RULE_CREW):
                checks.append(make(rule, fid, "UNKNOWN", f"no ground service for {fid}",
                                   "declared service with crew and min turnaround"))
            continue

        check, delay = _turn(a, gate_in[fid], svc, make)
        checks.append(check)
        turnaround_delay += delay

        check, ot = _crew(fid, svc, service_iv, services, crews, make)
        checks.append(check)
        overtime += ot

    return DomainReport(
        role="ground",
        scenario_hash=scenario_digest,
        plan_hash=digest,
        checks=checks,
        metrics={
            "overtime_min": overtime,
            "turnaround_delay_min": turnaround_delay,
            "gate_busy_min": _gate_busy(assignments, gate_in, shared.horizon_end_min),
        },
    )


def _gate(a: Assignment, gate_in: dict[str, int], assignments: dict[str, Assignment],
          gates: dict[str, Gate], make) -> Check:
    start, end = gate_in[a.flight_id], a.gate_out_min
    observed = f"gate={a.gate_id} interval=[{start},{end})"
    required = ("gate exists, is compatible, and its interval overlaps neither "
                "existing occupancy nor another assignment")
    gate = gates.get(a.gate_id)
    if gate is None:
        return make(RULE_GATE, a.flight_id, "FAIL",
                    f"{observed}; gate not declared", required)
    problems = []
    if a.flight_id not in gate.compatible_flight_ids:
        problems.append("flight not compatible with gate")
    if end <= start:
        problems.append("gate_out not after gate_in")
    for w in gate.occupied_windows:
        if overlap(start, end, w.start_min, w.end_min):
            problems.append(f"overlaps existing occupancy [{w.start_min},{w.end_min})")
    for other_id, other in sorted(assignments.items()):
        if other_id == a.flight_id or other.gate_id != a.gate_id or other_id not in gate_in:
            continue
        o_start, o_end = gate_in[other_id], other.gate_out_min
        if overlap(start, end, o_start, o_end):
            problems.append(f"overlaps {other_id} at [{o_start},{o_end})")
    if problems:
        return make(RULE_GATE, a.flight_id, "FAIL",
                    f"{observed}; " + "; ".join(problems), required)
    return make(RULE_GATE, a.flight_id, "PASS", observed, required)


def _turn(a: Assignment, gate_in: int, svc: GroundService, make) -> tuple[Check, int]:
    ready = gate_in + svc.min_turnaround_min
    observed = (f"gate_out={a.gate_out_min}; gate_in={gate_in} + "
                f"min_turnaround={svc.min_turnaround_min} = {ready}")
    required = f"gate_out_min >= {ready}"
    if a.gate_out_min < ready:
        # Negative slack is a hard failure, not a turnaround-delay credit.
        return make(RULE_TURN, a.flight_id, "FAIL", observed, required), 0
    return make(RULE_TURN, a.flight_id, "PASS", observed, required), a.gate_out_min - ready


def _crew(fid: str, svc: GroundService, service_iv: dict[str, tuple[int, int]],
          services: dict[str, GroundService], crews: dict[str, Crew],
          make) -> tuple[Check, int]:
    start, end = service_iv[fid]
    observed = f"crew={svc.crew_id} service=[{start},{end})"
    required = ("service fits one available window and does not overlap "
                "another service by the same crew")
    crew = crews.get(svc.crew_id)
    if crew is None:
        return make(RULE_CREW, fid, "UNKNOWN",
                    f"{observed}; crew not declared", required), 0
    problems = []
    if not any(w.start_min <= start and end <= w.end_min for w in crew.available_windows):
        problems.append("outside every available window")
    for other_id, (o_start, o_end) in sorted(service_iv.items()):
        if other_id == fid or services[other_id].crew_id != svc.crew_id:
            continue
        if overlap(start, end, o_start, o_end):
            problems.append(f"overlaps {other_id} service at [{o_start},{o_end})")
    overtime = max(0, end - max(start, crew.shift_end_min))
    observed += f"; shift_end={crew.shift_end_min}; overtime={overtime}"
    if problems:
        return make(RULE_CREW, fid, "FAIL",
                    f"{observed}; " + "; ".join(problems), required), overtime
    return make(RULE_CREW, fid, "PASS", observed, required), overtime


def _gate_busy(assignments: dict[str, Assignment], gate_in: dict[str, int],
               horizon_end: int) -> int:
    """New gate occupancy clipped to [0, horizon_end), union per gate, summed."""
    by_gate: dict[str, list[tuple[int, int]]] = {}
    for fid, a in assignments.items():
        if fid not in gate_in:
            continue
        start, end = max(0, gate_in[fid]), min(horizon_end, a.gate_out_min)
        if end > start:
            by_gate.setdefault(a.gate_id, []).append((start, end))
    total = 0
    for spans in by_gate.values():
        cur_start, cur_end = None, None
        for s, e in sorted(spans):
            if cur_end is None or s > cur_end:
                if cur_end is not None:
                    total += cur_end - cur_start
                cur_start, cur_end = s, e
            else:
                cur_end = max(cur_end, e)
        if cur_end is not None:
            total += cur_end - cur_start
    return total


def hard_checks_pass(report: DomainReport) -> bool:
    """True when every HARD check is PASS or code-evaluated NOT_APPLICABLE."""
    hard = [c for c in report.checks if c.severity == "HARD"]
    return bool(hard) and all(c.status in ("PASS", "NOT_APPLICABLE") for c in hard)
