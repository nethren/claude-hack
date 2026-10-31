"""Three demo scenarios, one per negotiation outcome, derived from the fixture.

Every scenario keeps the fixture's real source row (CSV row 76, C2-20/C2-21) and
changes only labelled simulated overlay fields. Each has its own scenario_id so
the scenario store never sees two different payloads under one revision.

- clear:    the initial plan already passes every domain; agents can agree in round 1.
- counter:  P0 breaks wake separation and double-books G1; agents counter and the
            coordinator selects a complete catalog plan for round 2.
- escalate: the runway is closed until +45 min and every catalog plan lands earlier,
            so no plan can be validated and the run escalates to a human controller.

Outcomes are what the deterministic checks make possible; live agents still decide
their own verdicts, so a live run can legitimately end in FALLBACK instead.
"""
from __future__ import annotations

from contracts.models import ScenarioInput
from runtime.scenario_loader import EXAMPLE

RUNWAY_REOPENS_MIN = 45

DEMOS = {
    "clear": {
        "label": "All clear",
        "expected_outcome": "CONSENSUS",
        "description": "The airline's proposed plan already fits runway spacing, fuel and stands.",
    },
    "counter": {
        "label": "Counteroffer",
        "expected_outcome": "CONSENSUS or FALLBACK",
        "description": "Arrivals are 2 min apart and two aircraft share G1; agents counter and the best plan is chosen.",
    },
    "escalate": {
        "label": "Runway closed",
        "expected_outcome": "ESCALATED",
        "description": f"The runway is closed until +{RUNWAY_REOPENS_MIN} min; no catalog plan can land safely.",
    },
}


def _base() -> ScenarioInput:
    return ScenarioInput.model_validate_json(EXAMPLE.read_bytes())


def demo_scenario(demo_id: str) -> ScenarioInput:
    if demo_id not in DEMOS:
        raise KeyError(demo_id)
    s = _base()
    s.scenario_id = f"dfw-demo-{demo_id}"
    if demo_id == "clear":
        s.initial_plan_id = "P1"
        s.shared.disruption_note = (
            "Historical flight row seeds a synthetic DFW arrival-coordination scenario. "
            "T2 is blocked. The airline's proposed plan P1 already separates the arrivals "
            "and uses separate stands. F2/F3 are simulated traffic; every operational time, "
            "fuel value, exposure, gate and crew value is synthetic.")
    elif demo_id == "escalate":
        s.atc.runway_open_windows[0].start_min = RUNWAY_REOPENS_MIN
        s.shared.disruption_note = (
            "Historical flight row seeds a synthetic DFW arrival-coordination scenario. "
            f"The arrival runway is closed by an equipment failure until +{RUNWAY_REOPENS_MIN} min "
            "and T2 is blocked. Every catalog plan lands before the runway reopens. F2/F3 are "
            "simulated traffic; every operational time, fuel value, exposure, gate and crew "
            "value is synthetic.")
    return s


def demo_catalog() -> list[dict]:
    return [{"id": demo_id, **meta, "scenario_id": f"dfw-demo-{demo_id}"}
            for demo_id, meta in DEMOS.items()]
