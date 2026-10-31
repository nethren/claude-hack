"""Code-owned checks, complete-report validation and fixed selection policy."""
from contracts.models import DomainReport, Plan, ScenarioInput, plan_hash
from domains.pilot import evaluate_pilot
from domains.ground import evaluate_ground

ROLES = ("atc", "pilot", "ground")
METRICS = {
    "atc": {"throughput_count", "additional_delay_min"},
    "pilot": {"turbulence_units", "missed_connections"},
    "ground": {"overtime_min", "turnaround_delay_min", "gate_busy_min"},
}
RULES = {
    "atc": {"ATC_RUNWAY", "ATC_WAKE", "ATC_TAXI"},
    "pilot": {"PILOT_EARLIEST", "PILOT_FUEL", "PILOT_TURBULENCE"},
    "ground": {"GROUND_GATE", "GROUND_TURN", "GROUND_CREW"},
}
POLICY = (("throughput_count", -1), ("missed_connections", 1),
          ("additional_delay_min", 1), ("turbulence_units", 1),
          ("overtime_min", 1), ("turnaround_delay_min", 1), ("gate_busy_min", -1))


def complete_report(report: DomainReport, plan: Plan, digest: str) -> bool:
    """A missing check cannot masquerade as an all-passing empty report."""
    role = report.role
    if (report.scenario_hash != digest or report.plan_hash != plan_hash(plan) or
            set(report.metrics) != METRICS[role] or not report.checks):
        return False
    checks = report.checks
    if len({c.check_id for c in checks}) != len(checks):
        return False
    prefix = f"{role}:{digest}:{report.plan_hash}:"
    if any(not c.check_id.startswith(prefix) or not c.evidence_refs for c in checks):
        return False
    if any(c.severity == "HARD" and c.status == "NOT_APPLICABLE" and
           not (role == "atc" and c.rule_id == "ATC_WAKE" and len(plan.assignments) == 1)
           for c in checks):
        return False
    for a in plan.assignments:
        for rule in RULES[role] - ({"ATC_WAKE"} if role == "atc" else set()):
            if not any(c.rule_id == rule and c.severity == "HARD" and
                       a.flight_id in c.flight_ids for c in checks):
                return False
    if role == "atc":
        ordered = sorted(plan.assignments, key=lambda a: (a.landing_min, a.flight_id))
        pairs = [(a.flight_id, b.flight_id) for a, b in zip(ordered, ordered[1:])]
        if any(not any(c.rule_id == "ATC_WAKE" and c.severity == "HARD" and
                       c.flight_ids == list(pair) for c in checks) for pair in pairs):
            return False
        if len(ordered) == 1 and not any(c.rule_id == "ATC_WAKE" and c.severity == "HARD" and
                c.flight_ids == [ordered[0].flight_id] and c.status == "NOT_APPLICABLE" for c in checks):
            return False
    if role == "pilot" and any(not any(c.rule_id == "PILOT_CONNECTION" and
            a.flight_id in c.flight_ids for c in checks) for a in plan.assignments):
        return False
    return True


def hard_pass(report: DomainReport) -> bool:
    hard = [c for c in report.checks if c.severity == "HARD"]
    return bool(hard) and all(c.status in ("PASS", "NOT_APPLICABLE") for c in hard)


def globally_valid(reports: list[DomainReport]) -> bool:
    return ([r.role for r in reports] == list(ROLES) and
            all(hard_pass(r) and all(c.status != "UNKNOWN" for c in r.checks) for r in reports))


def evaluate(plan: Plan, scenario: ScenarioInput, digest: str) -> list[DomainReport]:
    from domains.atc import evaluate_atc
    evaluators = {"atc": evaluate_atc, "pilot": evaluate_pilot, "ground": evaluate_ground}
    reports = []
    for role in ROLES:
        # Evaluators get private copies too; canonical scenario is never handed out.
        private = ScenarioInput.model_validate_json(scenario.model_dump_json())
        own_plan = Plan.model_validate_json(plan.model_dump_json())
        report = evaluators[role](own_plan, private.shared, getattr(private, role), scenario_digest=digest)
        report = DomainReport.model_validate_json(report.model_dump_json())
        if report.role != role or not complete_report(report, plan, digest):
            raise ValueError(f"Incomplete or incorrectly bound {role} evaluator report")
        reports.append(report)
    return reports


def metrics(reports):
    return {k: v for r in reports for k, v in r.metrics.items()}


def rank(plan, reports):
    m = metrics(reports)
    return tuple(m[k] * sign for k, sign in POLICY) + (plan_hash(plan),)


def explain_comparison(selected: Plan, other: Plan, reports):
    """UI-ready facts drawn directly from actual checks and ranking metrics."""
    rejected = reports[other.plan_id]
    failures = [c.model_dump(mode="json") for r in rejected for c in r.checks
                if c.severity == "HARD" and c.status not in ("PASS", "NOT_APPLICABLE")]
    if failures:
        return {"reason": "HARD_CONSTRAINT", "checks": failures}
    a, b = metrics(reports[selected.plan_id]), metrics(rejected)
    for key, sign in POLICY:
        if a[key] != b[key]:
            return {"reason": "POLICY_CRITERION", "criterion": key,
                    "selected_value": a[key], "other_value": b[key],
                    "preferred_direction": "lower" if sign == 1 else "higher",
                    "selected_preferred": sign * a[key] < sign * b[key]}
    return {"reason": "CONTENT_HASH_TIEBREAK", "selected_hash": plan_hash(selected),
            "other_hash": plan_hash(other)}
