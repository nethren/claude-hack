"""Fuel and CO2 panel: a MODELLED ESTIMATE, never measured fuel (JR-05, C2-12).

Pure and deterministic; reads a scenario and plans, never changes them, and
plays no part in validation, negotiation or plan selection.

Model, using the same holding-only fuel model as the pilot evaluator:
  holding_min(f) = max(0, landing_min(f) - earliest_landing_min(f))
  fuel_kg(f)     = holding_min(f) * holding_burn_kg_per_min(f)
  co2_kg         = fuel_kg * 3.16   (standard kg CO2 per kg of jet fuel)

The burn rate is the per-aircraft value in the pilot overlay (simulated); the
supplied CSVs carry no aircraft type or fuel data. Cruise, vectoring, taxi and
APU fuel are not modelled.

Baseline "landing in scheduled order" is a runway-only first-come-first-served
reference sequence: flights land in scheduled order at the earliest minute that
respects their earliest landing time, the declared wake separation / runway
occupancy and the runway open windows. It ignores gates, crew and taxiways, so
it can be operationally infeasible; it is a reference, not a catalog plan.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from contracts.models import Plan, ScenarioInput, Wire

CO2_KG_PER_KG_FUEL = 3.16
MODEL_VERSION = "fuel-co2-estimate-1.0"
ESTIMATE_LABEL = "MODELLED ESTIMATE - not measured fuel"

ASSUMPTIONS = [
    "Holding-only fuel model: fuel = holding minutes x per-aircraft holding burn rate.",
    "Holding burn rates come from the pilot scenario overlay (simulated); the dataset has no aircraft type or fuel data.",
    "CO2 = fuel x 3.16 kg CO2 per kg of jet fuel (standard conversion factor).",
    "Cruise, vectoring, taxi and APU fuel are not modelled.",
    "Baseline is a runway-only scheduled-order (first-come-first-served) sequence; it ignores gates, crew and taxiways.",
    "Times are simulation minutes, not converted CSV clock times.",
]


class FlightEstimate(Wire):
    flight_id: str
    landing_min: int
    earliest_landing_min: int
    holding_min: int
    holding_burn_kg_per_min: int
    fuel_kg: int
    co2_kg: float
    evidence_refs: list[str]


class PlanEstimate(Wire):
    plan_id: str
    status: Literal["ESTIMATED", "UNKNOWN"]
    unknown_reason: str | None
    flights: list[FlightEstimate]
    holding_min: int
    fuel_kg: int
    co2_kg: float


class Comparison(Wire):
    plan_id: str
    status: Literal["ESTIMATED", "UNKNOWN"]
    hard_constraints: Literal["PASS", "FAIL", "NOT_CHECKED"]
    # Positive: plan burns less than the baseline. None when there is no estimate
    # or the plan fails hard constraints (no achievable saving to report).
    fuel_saved_kg: int | None
    co2_saved_kg: float | None
    headline: str


class FuelCO2Panel(Wire):
    label: str
    model_version: str
    co2_kg_per_kg_fuel: float
    scenario_id: str
    scenario_version: int
    baseline: PlanEstimate
    plans: list[PlanEstimate]
    comparisons: list[Comparison]
    assumptions: list[str]


def _co2(fuel_kg: int) -> float:
    return round(fuel_kg * CO2_KG_PER_KG_FUEL, 1)


def scheduled_order_baseline(s: ScenarioInput) -> tuple[dict[str, int] | None, str | None]:
    """Landing minute per flight for the scheduled-order reference, or a reason."""
    limits = {lim.flight_id: lim for lim in s.pilot.limits}
    atc = s.atc
    ordered = sorted(s.shared.flights, key=lambda f: (f.scheduled_landing_min, f.flight_id))
    windows = sorted(atc.runway_open_windows, key=lambda w: w.start_min)
    landings: dict[str, int] = {}
    prev: str | None = None
    for f in ordered:
        lim = limits.get(f.flight_id)
        if lim is None:
            return None, f"no pilot limits for {f.flight_id}"
        t = max(f.scheduled_landing_min, lim.earliest_landing_min)
        if prev is not None:
            lc = atc.wake_class_by_flight.get(prev)
            fc = atc.wake_class_by_flight.get(f.flight_id)
            sep = atc.separation_min.get(lc, {}).get(fc) if lc and fc else None
            if sep is None:
                return None, f"no declared wake separation for {prev} -> {f.flight_id}"
            t = max(t, landings[prev] + max(sep, atc.runway_occupancy_min))
        occupancy = atc.runway_occupancy_min
        slot = next((max(t, w.start_min) for w in windows
                     if max(t, w.start_min) + occupancy <= w.end_min), None)
        if slot is None:
            return None, f"no open runway window for {f.flight_id} at or after minute {t}"
        landings[f.flight_id] = slot
        prev = f.flight_id
    return landings, None


def estimate_landings(s: ScenarioInput, plan_id: str,
                      landings: dict[str, int]) -> PlanEstimate:
    limits = {lim.flight_id: lim for lim in s.pilot.limits}
    sources = {f.flight_id: f"source:{f.source_id}" for f in s.shared.flights if f.source_id}
    flights: list[FlightEstimate] = []
    for f in s.shared.flights:
        lim = limits.get(f.flight_id)
        landing = landings.get(f.flight_id)
        if lim is None or landing is None:
            missing = "pilot limits" if lim is None else "a landing time"
            return PlanEstimate(plan_id=plan_id, status="UNKNOWN",
                                unknown_reason=f"{f.flight_id} has no {missing}",
                                flights=[], holding_min=0, fuel_kg=0, co2_kg=0.0)
        holding = max(0, landing - lim.earliest_landing_min)
        fuel = holding * lim.holding_burn_kg_per_min
        refs = [r for r in (sources.get(f.flight_id),) if r] + ["overlay:pilot"]
        flights.append(FlightEstimate(
            flight_id=f.flight_id, landing_min=landing,
            earliest_landing_min=lim.earliest_landing_min, holding_min=holding,
            holding_burn_kg_per_min=lim.holding_burn_kg_per_min, fuel_kg=fuel,
            co2_kg=_co2(fuel), evidence_refs=refs))
    fuel_total = sum(x.fuel_kg for x in flights)
    return PlanEstimate(plan_id=plan_id, status="ESTIMATED", unknown_reason=None,
                        flights=flights, holding_min=sum(x.holding_min for x in flights),
                        fuel_kg=fuel_total, co2_kg=_co2(fuel_total))


def estimate_plan(s: ScenarioInput, plan: Plan) -> PlanEstimate:
    return estimate_landings(s, plan.plan_id,
                             {a.flight_id: a.landing_min for a in plan.assignments})


def compare(plan: PlanEstimate, baseline: PlanEstimate,
            hard_constraints: str = "NOT_CHECKED") -> Comparison:
    if plan.status != "ESTIMATED" or baseline.status != "ESTIMATED":
        reason = plan.unknown_reason or baseline.unknown_reason
        return Comparison(plan_id=plan.plan_id, status="UNKNOWN",
                          hard_constraints=hard_constraints, fuel_saved_kg=None,
                          co2_saved_kg=None,
                          headline=f"No estimate for {plan.plan_id}: {reason}.")
    saved = baseline.fuel_kg - plan.fuel_kg
    co2 = _co2(abs(saved))
    if hard_constraints == "FAIL":
        # An infeasible plan's lower fuel is not a saving anyone could realise, so
        # the numeric fields are withheld too; API clients must not render them.
        headline = (f"{plan.plan_id} fails hard constraints; its fuel figure is not "
                    "an achievable saving.")
        return Comparison(plan_id=plan.plan_id, status="ESTIMATED",
                          hard_constraints=hard_constraints, fuel_saved_kg=None,
                          co2_saved_kg=None, headline=f"{headline} ({ESTIMATE_LABEL}.)")
    if saved > 0:
        headline = (f"{plan.plan_id} saves about {co2:g} kg CO2 ({saved} kg fuel) "
                    "against landing in scheduled order.")
    elif saved < 0:
        headline = (f"{plan.plan_id} uses about {co2:g} kg more CO2 ({-saved} kg more fuel) "
                    "than landing in scheduled order.")
    else:
        headline = f"{plan.plan_id} uses the same estimated fuel as landing in scheduled order."
    return Comparison(plan_id=plan.plan_id, status="ESTIMATED",
                      hard_constraints=hard_constraints, fuel_saved_kg=saved,
                      co2_saved_kg=round(saved * CO2_KG_PER_KG_FUEL, 1),
                      headline=f"{headline} ({ESTIMATE_LABEL}.)")


def build_panel(s: ScenarioInput, plans: list[Plan] | None = None, *,
                hard_pass: dict[str, bool] | None = None) -> FuelCO2Panel:
    """Estimate every given plan (default: the whole catalog) against the baseline.

    hard_pass maps plan_id to the code-owned all-domain hard-check result
    (see hard_check_results); plans absent from it are NOT_CHECKED.
    """
    landings, reason = scheduled_order_baseline(s)
    if landings is None:
        baseline = PlanEstimate(plan_id="BASELINE_SCHEDULED_ORDER", status="UNKNOWN",
                                unknown_reason=reason, flights=[], holding_min=0,
                                fuel_kg=0, co2_kg=0.0)
    else:
        baseline = estimate_landings(s, "BASELINE_SCHEDULED_ORDER", landings)
    estimates = [estimate_plan(s, p) for p in (plans if plans is not None else s.plans)]
    hard_pass = hard_pass or {}

    def checked(plan_id: str) -> str:
        if plan_id not in hard_pass:
            return "NOT_CHECKED"
        return "PASS" if hard_pass[plan_id] else "FAIL"

    return FuelCO2Panel(
        label=ESTIMATE_LABEL, model_version=MODEL_VERSION,
        co2_kg_per_kg_fuel=CO2_KG_PER_KG_FUEL, scenario_id=s.scenario_id,
        scenario_version=s.scenario_version, baseline=baseline, plans=estimates,
        comparisons=[compare(e, baseline, checked(e.plan_id)) for e in estimates],
        assumptions=ASSUMPTIONS)


def hard_check_results(s: ScenarioInput) -> dict[str, bool]:
    """All-domain hard-check result per catalog plan, from the existing evaluators.

    Read-only reuse of runtime.catalog; the panel never decides validity itself.
    """
    from contracts.models import scenario_hash
    from runtime.catalog import evaluate, globally_valid

    digest = scenario_hash(s)
    return {p.plan_id: globally_valid(evaluate(p, s, digest)) for p in s.plans}


class RunNotFound(LookupError):
    pass


def load_run(log_dir: Path, run_id: str):
    """Scenario as the run validated it, plus its RunResult, from the logs."""
    from runtime.models import RunResult

    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise RunNotFound(f"invalid run id {run_id!r}")
    result_path = Path(log_dir) / f"{run_id}.result.json"
    events_path = Path(log_dir) / f"{run_id}.jsonl"
    if not result_path.is_file() or not events_path.is_file():
        raise RunNotFound(f"no finished run {run_id} in {log_dir}")
    result = RunResult.model_validate_json(result_path.read_text(encoding="utf-8"))
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["type"] == "INPUT_VALIDATED":
            return ScenarioInput.model_validate(event["payload"]["scenario"]), result
    raise RunNotFound(f"run {run_id} has no validated scenario event")


def panel_for_run(log_dir: Path, run_id: str) -> tuple[FuelCO2Panel, str | None]:
    """Panel for a finished coordinator run and the plan it selected (if any).

    Validity comes from the run's own recorded reports via runtime.catalog.
    """
    from runtime.catalog import globally_valid

    s, result = load_run(log_dir, run_id)
    hard_pass = {plan_id: globally_valid(reports)
                 for plan_id, reports in result.candidate_reports.items()}
    return build_panel(s, hard_pass=hard_pass), result.selected_plan_id


def render_text(panel: FuelCO2Panel, *, highlight: str | None = None) -> str:
    """Plain-text panel for the CLI; the estimate label leads and closes it."""
    line = "=" * 72
    out = [line, f"FUEL & CO2 PANEL - {panel.label}", line]
    b = panel.baseline
    if b.status == "ESTIMATED":
        seq = ", ".join(f"{x.flight_id}@{x.landing_min}" for x in b.flights)
        out.append(f"Baseline (scheduled order, runway-only): {seq}")
        out.append(f"  holding {b.holding_min} min | fuel {b.fuel_kg} kg | CO2 {b.co2_kg:g} kg")
    else:
        out.append(f"Baseline unavailable: {b.unknown_reason}")
    out.append("")
    out.append(f"{'Plan':<8}{'Hard checks':>12}{'Holding min':>12}{'Fuel kg':>10}"
               f"{'CO2 kg':>10}{'Saved CO2 kg':>15}")
    for est, cmp in zip(panel.plans, panel.comparisons):
        mark = "*" if est.plan_id == highlight else " "
        if est.status != "ESTIMATED":
            out.append(f"{mark}{est.plan_id:<7}  unknown: {est.unknown_reason}")
            continue
        if cmp.hard_constraints == "FAIL":
            saved = "infeasible"
        else:
            saved = "n/a" if cmp.co2_saved_kg is None else f"{cmp.co2_saved_kg:+g}"
        out.append(f"{mark}{est.plan_id:<7}{cmp.hard_constraints:>12}{est.holding_min:>12}"
                   f"{est.fuel_kg:>10}{est.co2_kg:>10g}{saved:>15}")
    if highlight:
        chosen = next((c for c in panel.comparisons if c.plan_id == highlight), None)
        if chosen:
            out += ["", chosen.headline]
    out += ["", "Assumptions:"] + [f"  - {a}" for a in panel.assumptions]
    out += [f"CO2 factor {panel.co2_kg_per_kg_fuel} kg/kg | {panel.model_version}",
            f"{panel.label}.", line]
    return "\n".join(out)
