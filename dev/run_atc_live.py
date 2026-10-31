"""Run the ATC agent once against the fixture with a real Claude call.

Usage (needs ANTHROPIC_API_KEY, an `ant auth login` profile, or a line
`ANTHROPIC_API_KEY=...` in the repo's git-ignored .env file):
    .venv/Scripts/python -m dev.run_atc_live [P0|P1|P2]

This is a single-agent smoke test, not a negotiation: no pilot/ground agents,
no coordinator. Output is a live model result on simulated scenario data.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from agents.atc import MAX_OUTPUT_TOKENS, ATCAgent
from contracts.models import (
    AgentProtocolError,
    AgentRequest,
    CandidateView,
    ScenarioInput,
    plan_hash,
    scenario_hash,
)
from dev.claude_gateway import ClaudeGateway
from domains.atc import evaluate_atc, hard_checks_pass

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/examples/coordination-scenario-v1.json"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Read KEY=VALUE lines from .env without overriding variables already set."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def build_request(scenario: ScenarioInput, current: str) -> AgentRequest:
    digest = scenario_hash(scenario)
    views = [CandidateView(plan=p, plan_hash=plan_hash(p),
                           report=evaluate_atc(p, scenario.shared, scenario.atc, scenario_digest=digest))
             for p in scenario.plans]
    cur = next(v for v in views if v.plan.plan_id == current)
    return AgentRequest(
        protocol_version="1.0", run_id="atc-smoke", request_id="atc-smoke:r1:atc", role="atc",
        scenario_id=scenario.scenario_id, scenario_version=scenario.scenario_version,
        scenario_hash=digest, round_index=1, proposal_id="atc-smoke:r1", current_plan_id=current,
        current_plan_hash=cur.plan_hash, call_timeout_ms=15000, shared=scenario.shared,
        domain=scenario.atc, candidates=views, previous_messages=[],
    )


async def main(current: str) -> int:
    scenario = ScenarioInput.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    request = build_request(scenario, current)
    for view in request.candidates:
        print(f"{view.plan.plan_id}: ATC hard checks {'PASS' if hard_checks_pass(view.report) else 'FAIL'}"
              f"  metrics {view.report.metrics}")
    gateway = ClaudeGateway()
    print(f"\nCalling {gateway.model} as ATC on current proposal {current} "
          f"(max_tokens={MAX_OUTPUT_TOKENS}, effort={gateway.effort or "model default"}) ...")
    try:
        reply = await ATCAgent().decide(request, model=gateway)
    except AgentProtocolError as e:
        print(f"\nPROTOCOL ERROR {e.code}: {e.detail}")
        return 1
    except TypeError as e:
        if "authentication" not in str(e):
            raise
        print("\nNo Claude credentials found. Add `ANTHROPIC_API_KEY=...` to the repo's .env file "
              "(git-ignored), set the variable, or run `ant auth login`, then retry.")
        return 2
    d, u = reply.result.decision, reply.result.usage
    print(f"\nverdict: {d.verdict}\nranked: {d.ranked_alternative_ids}\ncited: {len(d.cited_check_ids)} check(s)"
          f"\nreason: {d.reason}\nuncertainty: {d.uncertainty}")
    print(f"\nmodel {u.model}, {u.input_tokens} in / {u.output_tokens} out tokens, {u.elapsed_ms} ms")
    return 0


if __name__ == "__main__":
    load_dotenv()
    sys.exit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "P0")))
