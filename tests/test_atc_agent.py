"""ATC adapter tests with a fake ModelGateway (offline; not live AI results)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agents.atc import ATCAgent, MAX_OUTPUT_TOKENS, SYSTEM_PROMPT
from contracts.models import (
    AgentProtocolError,
    AgentRequest,
    CandidateView,
    ModelDecision,
    ModelResult,
    PublicMessage,
    ScenarioInput,
    Usage,
    plan_hash,
    scenario_hash,
)
from domains.atc import evaluate_atc

FIXTURE = Path(__file__).resolve().parents[1] / "docs/examples/coordination-scenario-v1.json"


class FakeGateway:
    def __init__(self, decision: dict):
        self.decision = ModelDecision.model_validate(decision)
        self.calls: list[dict] = []

    async def complete(self, *, role, system_prompt, user_json, timeout_s, max_output_tokens):
        self.calls.append(dict(role=role, system_prompt=system_prompt, user_json=user_json,
                               timeout_s=timeout_s, max_output_tokens=max_output_tokens))
        return ModelResult(
            decision=self.decision,
            raw_text=self.decision.model_dump_json(),
            usage=Usage(provider="fake", model="fake", input_tokens=None, output_tokens=None,
                        model_calls=1, elapsed_ms=0),
        )


def make_request(current: str = "P0", *, round_index: int = 1, previous=None, timeout_ms: int = 15000,
                 scenario: ScenarioInput | None = None) -> AgentRequest:
    s = scenario or ScenarioInput.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    digest = scenario_hash(s)
    views = [CandidateView(plan=p, plan_hash=plan_hash(p),
                           report=evaluate_atc(p, s.shared, s.atc, scenario_digest=digest))
             for p in s.plans]
    cur = next(v for v in views if v.plan.plan_id == current)
    return AgentRequest(
        protocol_version="1.0", run_id="run-1", request_id=f"run-1:r{round_index}:atc", role="atc",
        scenario_id=s.scenario_id, scenario_version=s.scenario_version, scenario_hash=digest,
        round_index=round_index, proposal_id=f"run-1:r{round_index}", current_plan_id=current,
        current_plan_hash=cur.plan_hash, call_timeout_ms=timeout_ms, shared=s.shared, domain=s.atc,
        candidates=views, previous_messages=previous or [],
    )


def check_id(request: AgentRequest, plan_id: str, rule: str, *flights: str) -> str:
    view = next(v for v in request.candidates if v.plan.plan_id == plan_id)
    return next(c.check_id for c in view.report.checks if c.rule_id == rule and c.flight_ids == list(flights))


def decide(request: AgentRequest, decision: dict):
    gateway = FakeGateway(decision)
    return asyncio.run(ATCAgent().decide(request, model=gateway)), gateway


def decision(verdict: str, ranked=(), cited=(), reason="r", uncertainty="") -> dict:
    return dict(verdict=verdict, ranked_alternative_ids=list(ranked), cited_check_ids=list(cited),
                reason=reason, uncertainty=uncertainty)


def test_counter_from_p0_to_p1_returns_matching_envelope():
    req = make_request("P0")
    cited = [check_id(req, "P0", "ATC_WAKE", "F1", "F2"), check_id(req, "P1", "ATC_WAKE", "F1", "F2")]
    reply, gw = decide(req, decision("COUNTER", ["P1", "P2"], cited))
    assert reply.result.decision.verdict == "COUNTER"
    for field in ("protocol_version", "run_id", "request_id", "scenario_version", "scenario_hash",
                  "round_index", "proposal_id", "current_plan_id", "current_plan_hash"):
        assert getattr(reply, field) == getattr(req, field)
    assert reply.role == "atc"
    assert len(gw.calls) == 1
    call = gw.calls[0]
    assert call["role"] == "atc" and call["system_prompt"] == SYSTEM_PROMPT
    assert call["timeout_s"] == 15.0 and call["max_output_tokens"] == MAX_OUTPUT_TOKENS == 800


def test_accept_valid_current_plan():
    req = make_request("P1")
    reply, _ = decide(req, decision("ACCEPT", cited=[check_id(req, "P1", "ATC_WAKE", "F1", "F2")]))
    assert reply.result.decision.verdict == "ACCEPT"


def test_timeout_passed_through_in_seconds():
    _, gw = decide(make_request("P1", timeout_ms=9000), decision("ACCEPT"))
    assert gw.calls[0]["timeout_s"] == 9.0


def test_context_contains_source_row_and_only_atc_state():
    req = make_request("P0")
    _, gw = decide(req, decision("COUNTER", ["P1"]))
    payload = json.loads(gw.calls[0]["user_json"])
    # Same layout as the pilot/ground adapters and the coordinator's offline gateway.
    assert list(payload) == ["source_and_scenario", "current_proposal", "atc_domain_state",
                             "candidates", "output_schema", "final_reminder"]
    assert payload["current_proposal"] == {
        "round_index": 1, "proposal_id": req.proposal_id,
        "current_plan_id": "P0", "current_plan_hash": req.current_plan_hash,
    }
    assert [c["plan"]["plan_id"] for c in payload["candidates"]] == ["P0", "P1", "P2"]
    assert all(c["report"]["role"] == "atc" and len(c["report"]["checks"]) == 8 for c in payload["candidates"])
    assert payload["source_and_scenario"]["shared"]["source_rows"][0]["raw"]["WEATHER_DELAY"] == "35"
    for other_domain_field in ("reserve_kg", "fuel_at_earliest_landing_kg", "crew_id", "occupied_windows"):
        assert other_domain_field not in gw.calls[0]["user_json"]


def test_round_two_includes_original_previous_messages():
    msg = PublicMessage(role="pilot", proposal_id="run-1:r1", plan_hash="a" * 64,
                        decision=ModelDecision.model_validate(decision("COUNTER", ["P1"], reason="fuel margin")))
    req = make_request("P1", round_index=2, previous=[msg])
    _, gw = decide(req, decision("ACCEPT"))
    payload = json.loads(gw.calls[0]["user_json"])
    assert payload["previous_messages"][0]["decision"]["reason"] == "fuel margin"
    assert list(payload)[-3:] == ["previous_messages", "output_schema", "final_reminder"]
    assert payload["current_proposal"]["round_index"] == 2


def test_round_one_omits_previous_messages():
    _, gw = decide(make_request("P1"), decision("ACCEPT"))
    assert "previous_messages" not in json.loads(gw.calls[0]["user_json"])


def test_rejected_vote_keeps_original_model_output():
    with pytest.raises(AgentProtocolError) as err:
        decide(make_request("P0"), decision("ACCEPT", reason="looks fine"))
    assert err.value.code == "INVALID_ACCEPT"
    assert err.value.result.decision.reason == "looks fine"


@pytest.mark.parametrize("current, bad, code", [
    ("P0", decision("ACCEPT"), "INVALID_ACCEPT"),
    ("P1", decision("ACCEPT", ["P2"]), "MODEL_JSON_INVALID"),
    ("P0", decision("COUNTER", []), "MODEL_JSON_INVALID"),
    ("P0", decision("COUNTER", ["P0"]), "MODEL_JSON_INVALID"),
    ("P1", decision("COUNTER", ["P0"]), "MODEL_JSON_INVALID"),
    ("P0", decision("COUNTER", ["P9"]), "UNKNOWN_CANDIDATE"),
    ("P0", decision("COUNTER", ["P1", "P1"]), "MODEL_JSON_INVALID"),
    ("P0", decision("REJECT", ["P1"]), "MODEL_JSON_INVALID"),
    ("P1", decision("ACCEPT", cited=["atc:made-up"]), "UNKNOWN_CHECK"),
])
def test_invalid_decisions_raise_protocol_error(current, bad, code):
    with pytest.raises(AgentProtocolError) as err:
        decide(make_request(current), bad)
    assert err.value.code == code and err.value.role == "atc"


def test_accept_cannot_cite_checks_from_another_plan():
    req = make_request("P1")
    with pytest.raises(AgentProtocolError) as err:
        decide(req, decision("ACCEPT", cited=[check_id(req, "P2", "ATC_WAKE", "F1", "F2")]))
    assert err.value.code == "UNKNOWN_CHECK"


def test_wrong_role_request_never_calls_model():
    req = make_request("P0").model_copy(update={"role": "pilot"})
    gw = FakeGateway(decision("REJECT"))
    with pytest.raises(AgentProtocolError) as err:
        asyncio.run(ATCAgent().decide(req, model=gw))
    assert err.value.code == "INPUT_SCHEMA_INVALID" and gw.calls == []


def test_report_bound_to_other_scenario_is_rejected_before_call():
    req = make_request("P0")
    req = req.model_copy(update={"scenario_hash": "f" * 64})
    gw = FakeGateway(decision("REJECT"))
    with pytest.raises(AgentProtocolError):
        asyncio.run(ATCAgent().decide(req, model=gw))
    assert gw.calls == []
