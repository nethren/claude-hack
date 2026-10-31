"""Reference ATC evaluator, replaceable through the protocol 1.0 interface.

This is an integrator implementation because no ATC branch was available.
Single runway and blocked-route simulation; no full sector/collision model.
"""
from contracts.models import ATCState, Check, DomainReport, Plan, SharedInput, plan_hash

RULES_VERSION = "atc-reference-rules-1.0"


def evaluate_atc(plan: Plan, shared: SharedInput, state: ATCState, *, scenario_digest: str) -> DomainReport:
    digest = plan_hash(plan)
    routes = {r.route_id: r for r in state.routes}
    refs = {f.flight_id: f"source:{f.source_id}" for f in shared.flights if f.source_id}
    checks = []

    def add(rule, ids, status, observed, required):
        evidence = sorted({refs[f] for f in ids if f in refs}) + ["overlay:atc", f"rule:{rule}"]
        checks.append(Check(check_id=f"atc:{scenario_digest}:{digest}:{rule}:{':'.join(ids)}",
                            rule_id=rule, flight_ids=ids, severity="HARD", status=status,
                            observed=observed, required=required, evidence_refs=evidence))

    ordered = sorted(plan.assignments, key=lambda a: (a.landing_min, a.flight_id))
    for a in ordered:
        start, end = a.landing_min, a.landing_min + state.runway_occupancy_min
        ok = any(w.start_min <= start and end <= w.end_min for w in state.runway_open_windows)
        add("ATC_RUNWAY", [a.flight_id], "PASS" if ok else "FAIL",
            f"runway occupancy=[{start},{end})", "occupancy contained in an open runway window")
        route = routes.get(a.taxi_route_id)
        if route is None:
            add("ATC_TAXI", [a.flight_id], "UNKNOWN", "route not declared", "declared route traversal avoids blocked windows")
        else:
            end = start + route.taxi_in_min
            blocked = any(start < w.end_min and w.start_min < end for w in route.blocked_windows)
            add("ATC_TAXI", [a.flight_id], "FAIL" if blocked else "PASS",
                f"route={route.route_id} traversal=[{start},{end}); blocked={blocked}",
                "route traversal does not overlap any blocked window")
    if len(ordered) == 1:
        add("ATC_WAKE", [ordered[0].flight_id], "NOT_APPLICABLE", "one arrival; no adjacent pair", "applies to consecutive arrivals")
    for leader, follower in zip(ordered, ordered[1:]):
        lc = state.wake_class_by_flight.get(leader.flight_id)
        fc = state.wake_class_by_flight.get(follower.flight_id)
        sep = state.separation_min.get(lc, {}).get(fc)
        ids = [leader.flight_id, follower.flight_id]
        gap = follower.landing_min - leader.landing_min
        if sep is None:
            add("ATC_WAKE", ids, "UNKNOWN", "wake matrix entry missing", "declared leader/follower minimum separation")
        else:
            minimum = max(sep, state.runway_occupancy_min)
            add("ATC_WAKE", ids, "PASS" if gap >= minimum else "FAIL",
                f"landing gap={gap} min; classes={lc}->{fc}", f"gap >= {minimum} min")
    targets = {f.flight_id: f.scheduled_landing_min for f in shared.flights}
    return DomainReport(role="atc", scenario_hash=scenario_digest, plan_hash=digest, checks=checks,
                        metrics={"throughput_count": sum(a.landing_min < shared.horizon_end_min for a in ordered),
                                 "additional_delay_min": sum(max(0, a.landing_min - targets[a.flight_id]) for a in ordered)})
