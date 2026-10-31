"""Pilot domain evaluator (C2-12 to C2-15).

Pure and deterministic: no filesystem, network, model calls or mutation of its
inputs. Units: integer minutes from the scenario origin, integer kilograms,
kg/min holding burn and a synthetic 0-3 turbulence ordinal.

Simplifications shown alongside the simulation: fuel is a holding-only model
(no routing, taxi or diversion fuel, no regulatory compliance), and "flight
safety" (C2-13) is represented only by the earliest-landing, fuel-reserve and
turbulence-cap hard checks below.
"""
from __future__ import annotations

from contracts.models import (
    Assignment,
    Check,
    DomainReport,
    PilotLimits,
    PilotState,
    Plan,
    SharedInput,
    plan_hash,
)

RULES_VERSION = "pilot-rules-1.0"

RULE_EARLIEST = "PILOT_EARLIEST"
RULE_FUEL = "PILOT_FUEL"
RULE_TURBULENCE = "PILOT_TURBULENCE"
RULE_CONNECTION = "PILOT_CONNECTION"
HARD_RULES = (RULE_EARLIEST, RULE_FUEL, RULE_TURBULENCE)

METRIC_KEYS = ("turbulence_units", "missed_connections")

OVERLAY_REF = "overlay:pilot"


def validate_pilot_inputs(shared: SharedInput, state: PilotState) -> list[str]:
    """Return preflight problems for D's INPUT_ERROR path; empty means valid.

    A missing hard-limit input is never filled in by the evaluator or a model.
    """
    problems: list[str] = []
    flight_ids = [f.flight_id for f in shared.flights]
    seen: set[str] = set()
    for lim in state.limits:
        where = f"pilot.limits[{lim.flight_id}]"
        if lim.flight_id in seen:
            problems.append(f"{where}: duplicate flight_id")
        seen.add(lim.flight_id)
        if lim.flight_id not in flight_ids:
            problems.append(f"{where}: flight_id not in shared.flights")
        if lim.connecting_passengers > 0:
            if lim.connection_deadline_min is None:
                problems.append(
                    f"{where}.connection_deadline_min: required when "
                    f"connecting_passengers={lim.connecting_passengers}")
            if lim.transfer_min is None:
                problems.append(
                    f"{where}.transfer_min: required when "
                    f"connecting_passengers={lim.connecting_passengers}")
        options = shared.options.landing_min_by_flight.get(lim.flight_id, [])
        for landing in options:
            if str(landing) not in lim.turbulence_by_landing_min:
                problems.append(
                    f"{where}.turbulence_by_landing_min: missing exposure for "
                    f"allowed landing option {landing}")
    for fid in flight_ids:
        if fid not in seen:
            problems.append(f"pilot.limits: missing limits for flight {fid}")
    return problems


def evaluate_pilot(
    plan: Plan, shared: SharedInput, state: PilotState, *, scenario_digest: str
) -> DomainReport:
    digest = plan_hash(plan)
    limits = {lim.flight_id: lim for lim in state.limits}
    assignments = {a.flight_id: a for a in plan.assignments}
    source_refs = {
        f.flight_id: f"source:{f.source_id}"
        for f in shared.flights if f.source_id is not None
    }

    flight_ids = [f.flight_id for f in shared.flights]
    flight_ids += sorted(fid for fid in assignments if fid not in flight_ids)

    def make(rule: str, fid: str, severity: str, status: str,
             observed: str, required: str) -> Check:
        refs = [OVERLAY_REF, f"rule:{rule}"]
        if fid in source_refs:
            refs.insert(0, source_refs[fid])
        return Check(
            check_id=f"pilot:{scenario_digest}:{digest}:{rule}:{fid}",
            rule_id=rule, flight_ids=[fid], severity=severity, status=status,
            observed=observed, required=required, evidence_refs=refs,
        )

    checks: list[Check] = []
    turbulence_units = 0
    missed_connections = 0

    for fid in flight_ids:
        a = assignments.get(fid)
        lim = limits.get(fid)
        if a is None or lim is None:
            missing = "assignment" if a is None else "pilot limits"
            for rule in HARD_RULES:
                checks.append(make(rule, fid, "HARD", "UNKNOWN",
                                   f"no {missing} for flight {fid}",
                                   "exactly one assignment and declared limits"))
            continue

        checks.append(_earliest(a, lim, make))

        check, _ = _fuel(a, lim, make)
        checks.append(check)

        check, exposure = _turbulence(a, lim, make)
        checks.append(check)
        if exposure is not None:
            turbulence_units += exposure

        check, missed = _connection(a, lim, shared, make)
        checks.append(check)
        missed_connections += missed

    return DomainReport(
        role="pilot",
        scenario_hash=scenario_digest,
        plan_hash=digest,
        checks=checks,
        metrics={
            "turbulence_units": turbulence_units,
            "missed_connections": missed_connections,
        },
    )


def _earliest(a: Assignment, lim: PilotLimits, make) -> Check:
    ok = a.landing_min >= lim.earliest_landing_min
    return make(RULE_EARLIEST, a.flight_id, "HARD", "PASS" if ok else "FAIL",
                f"landing_min={a.landing_min}",
                f"landing_min >= {lim.earliest_landing_min}")


def _fuel(a: Assignment, lim: PilotLimits, make) -> tuple[Check, int | None]:
    holding = a.landing_min - lim.earliest_landing_min
    required = f"fuel_at_landing_kg >= reserve_kg={lim.reserve_kg}"
    if holding < 0:
        # The holding-only model is undefined before the earliest landing time.
        return make(RULE_FUEL, a.flight_id, "HARD", "UNKNOWN",
                    f"landing_min={a.landing_min} precedes earliest "
                    f"{lim.earliest_landing_min}; holding fuel model undefined",
                    required), None
    fuel = lim.fuel_at_earliest_landing_kg - holding * lim.holding_burn_kg_per_min
    status = "PASS" if fuel >= lim.reserve_kg else "FAIL"
    return make(RULE_FUEL, a.flight_id, "HARD", status,
                f"fuel_at_landing_kg={fuel} = {lim.fuel_at_earliest_landing_kg} - "
                f"{holding} min x {lim.holding_burn_kg_per_min} kg/min",
                required), fuel


def _turbulence(a: Assignment, lim: PilotLimits, make) -> tuple[Check, int | None]:
    exposure = lim.turbulence_by_landing_min.get(str(a.landing_min))
    required = f"exposure declared and <= max_turbulence_units={lim.max_turbulence_units}"
    if exposure is None:
        return make(RULE_TURBULENCE, a.flight_id, "HARD", "UNKNOWN",
                    f"no exposure declared for landing_min={a.landing_min}",
                    required), None
    status = "PASS" if exposure <= lim.max_turbulence_units else "FAIL"
    return make(RULE_TURBULENCE, a.flight_id, "HARD", status,
                f"exposure={exposure} at landing_min={a.landing_min}",
                required), exposure


def _connection(a: Assignment, lim: PilotLimits, shared: SharedInput,
                make) -> tuple[Check, int]:
    if lim.connecting_passengers == 0:
        return make(RULE_CONNECTION, a.flight_id, "SOFT", "NOT_APPLICABLE",
                    "connecting_passengers=0",
                    "applies only when connecting_passengers > 0"), 0
    taxi = shared.taxi_in_min_by_route.get(a.taxi_route_id)
    required = (f"gate_in + transfer_min <= connection_deadline_min="
                f"{lim.connection_deadline_min}")
    if (taxi is None or lim.connection_deadline_min is None
            or lim.transfer_min is None):
        return make(RULE_CONNECTION, a.flight_id, "SOFT", "UNKNOWN",
                    f"connecting_passengers={lim.connecting_passengers}; missing "
                    "taxi route time, deadline or transfer time", required), 0
    gate_in = a.landing_min + taxi
    arrival = gate_in + lim.transfer_min
    if arrival > lim.connection_deadline_min:
        return make(RULE_CONNECTION, a.flight_id, "SOFT", "FAIL",
                    f"gate_in={gate_in} + transfer={lim.transfer_min} = {arrival}; "
                    f"{lim.connecting_passengers} passengers miss connection",
                    required), lim.connecting_passengers
    return make(RULE_CONNECTION, a.flight_id, "SOFT", "PASS",
                f"gate_in={gate_in} + transfer={lim.transfer_min} = {arrival}",
                required), 0


def hard_checks_pass(report: DomainReport) -> bool:
    """True when every HARD check is PASS or code-evaluated NOT_APPLICABLE."""
    hard = [c for c in report.checks if c.severity == "HARD"]
    return bool(hard) and all(c.status in ("PASS", "NOT_APPLICABLE") for c in hard)
