"""Export a truthful, explicitly scripted backend run for the frontend review.

Run from repository root with .venv/bin/python frontend/scripts/build-demo-fixture.py.
This is a recorded test double, not a live model or a fictional stream endpoint.
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app import default_agents
from contracts.models import ModelDecision, ModelResult, Usage
from runtime.coordinator import run_negotiation
from runtime.scenario_loader import EXAMPLE, load_scenario


class ReviewGateway:
    mode = "offline"

    async def complete(self, *, role, system_prompt, user_json, timeout_s, max_output_tokens):
        payload = json.loads(user_json)
        current = payload["current_proposal"]["current_plan_id"]
        views = payload["candidates"]
        view = next(v for v in views if v["plan"]["plan_id"] == current)
        bad = [c for c in view["report"]["checks"] if c["severity"] == "HARD" and c["status"] != "PASS"]
        valid = [v["plan"]["plan_id"] for v in views if v["plan"]["plan_id"] != current
                 and all(c["status"] in ("PASS", "NOT_APPLICABLE") for c in v["report"]["checks"] if c["severity"] == "HARD")]
        verdict = "COUNTER" if bad and valid else "REJECT" if bad else "ACCEPT"
        reasons = {
            ("atc", "COUNTER"): "The first two arrivals are only 2 minutes apart. A revised slot restores the required 3-minute separation.",
            ("atc", "ACCEPT"): "Arrival spacing, runway availability and taxiway checks pass for all three flights.",
            ("pilot", "ACCEPT"): "Fuel reserves and turbulence limits are protected. The earlier arrival keeps both connecting passengers on time.",
            ("ground", "COUNTER"): "The initial gate assignments overlap. Use separate stands to keep both turnarounds moving.",
            ("ground", "ACCEPT"): "Stand assignments no longer overlap. Crew availability and minimum turnaround checks pass.",
        }
        reason = reasons.get((role, verdict), "No candidate meets this role's hard constraints.")
        if role == 'ground' and verdict == 'COUNTER' and any(c['rule_id']=='GROUND_CREW' for c in bad):
            reason = "Crew C2 is not available when service would begin. A later arrival lets the turnaround fit the available shift."
        if role == 'pilot' and verdict == 'ACCEPT' and view['report']['metrics'].get('missed_connections'):
            reason = "Fuel reserves and turbulence limits pass, but both connecting passengers miss their transfer. This remains a visible trade-off."
        d = ModelDecision(verdict=verdict, ranked_alternative_ids=valid if verdict == "COUNTER" else [],
                          cited_check_ids=[c["check_id"] for c in (bad or view["report"]["checks"][:1])],
                          reason=reason, uncertainty="Scripted review replay with synthetic operational inputs.")
        return ModelResult(decision=d, raw_text=d.model_dump_json(),
                           usage=Usage(provider="offline-test-double", model="frontend-review-fixture",
                                       input_tokens=None, output_tokens=None, model_calls=0, elapsed_ms=0))


async def main():
    scenario = load_scenario(EXAMPLE)
    with tempfile.TemporaryDirectory(prefix="groundline-demo-") as temporary:
        for name in ('run','crew','closed'):
            current = scenario.model_copy(deep=True)
            if name == 'crew':
                current.scenario_version = 2
                current.ground.crews[1].available_windows[0].start_min = 20
            elif name == 'closed':
                current.scenario_version = 3
                current.atc.runway_open_windows = []
            result = await run_negotiation(current, default_agents(), ReviewGateway(), log_dir=Path(temporary))
            events = [json.loads(line) for line in (Path(temporary) / result.event_log_ref).read_text().splitlines()]
            output = {"kind": "recorded-scripted-replay", "scenario": current.model_dump(mode="json"),
                      "result": result.model_dump(mode="json"), "events": events,
                      "presentation_note": "Real backend run with scripted decisions. Geographic routes and motion are illustrative."}
            path = ROOT / f"frontend/public/data/demo-{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(output, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
            print(f"Exported {name}: {result.outcome} {result.selected_plan_id}; {result.agent_invocations} adapter invocations, {result.model_calls_attempted} model calls")


if __name__ == "__main__":
    asyncio.run(main())
