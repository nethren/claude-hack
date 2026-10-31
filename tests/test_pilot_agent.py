"""Pilot adapter tests with a fake gateway. Offline integration tests only;
these are not live model results."""
import asyncio
import json
from pathlib import Path

import pytest

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
from agents.pilot import MAX_OUTPUT_TOKENS, SYSTEM_PROMPT, PilotAgent
from domains.pilot import evaluate_pilot

FIXTURE = Path(__file__).resolve().parents[1] / "docs/examples/coordination-scenario-v1.json"


class FakeGateway:
    def __init__(self, decision: dict):
        self.decision = decision
        self.calls: list[dict] = []

    async def complete(self, *, role, system_prompt, user_json, timeout_s,
                       max_output_tokens):
        self.calls.append(dict(role=role, system_prompt=system_prompt,
                               user_json=user_json, timeout_s=timeout_s,
                               max_output_tokens=max_output_tokens))
        raw = json.dumps(self.decision)
        return ModelResult(
            decision=ModelDecision.model_validate_json(raw),
            raw_text=raw,
            usage=Usage(provider="fake", model="fake", input_tokens=None,
                        output_tokens=None, model_calls=1, elapsed_ms=0),
        )


@pytest.fixture
def scenario() -> ScenarioInput:
    return ScenarioInput.model_validate_json(FIXTURE.read_text())


def make_request(s: ScenarioInput, current: str = "P0", round_index: int = 1,
                 previous=None) -> AgentRequest:
    digest = scenario_hash(s)
    views = [
        CandidateView(plan=p, plan_hash=plan_hash(p),
                      report=evaluate_pilot(p, s.shared, s.pilot, scenario_digest=digest))
        for p in s.plans
    ]
    cur = next(v for v in views if v.plan.plan_id == current)
    return AgentRequest(
        protocol_version="1.0", run_id="run-1", request_id=f"run-1:r{round_index}:pilot",
        role="pilot", scenario_id=s.scenario_id, scenario_version=s.scenario_version,
        scenario_hash=digest, round_index=round_index,
        proposal_id=f"run-1:r{round_index}", current_plan_id=current,
        current_plan_hash=cur.plan_hash, call_timeout_ms=12000, shared=s.shared,
        domain=s.pilot, candidates=views, previous_messages=previous or [],
    )


def decision(verdict="ACCEPT", ranked=(), cited=()):
    return {"verdict": verdict, "ranked_alternative_ids": list(ranked),
            "cited_check_ids": list(cited), "reason": "test", "uncertainty": ""}


def decide(request, gateway):
    return asyncio.run(PilotAgent().decide(request, model=gateway))


def first_check(request, plan_id, rule="PILOT_FUEL"):
    view = next(c for c in request.candidates if c.plan.plan_id == plan_id)
    return next(c.check_id for c in view.report.checks if c.rule_id == rule)


def test_accept_valid_plan_copies_envelope_with_one_call(scenario):
    req = make_request(scenario, current="P1")
    gw = FakeGateway(decision(cited=[first_check(req, "P1")]))
    reply = decide(req, gw)

    assert len(gw.calls) == 1
    call = gw.calls[0]
    assert call["role"] == "pilot"
    assert call["system_prompt"] == SYSTEM_PROMPT
    assert call["timeout_s"] == 12.0
    assert call["max_output_tokens"] == MAX_OUTPUT_TOKENS == 1600
    for field in ("run_id", "request_id", "scenario_version", "scenario_hash",
                  "round_index", "proposal_id", "current_plan_id", "current_plan_hash"):
        assert getattr(reply, field) == getattr(req, field)
    assert reply.role == "pilot"
    assert reply.result.raw_text == json.dumps(gw.decision)


def test_context_has_source_row_and_only_pilot_domain(scenario):
    req = make_request(scenario, current="P1")
    gw = FakeGateway(decision())
    decide(req, gw)
    payload = json.loads(gw.calls[0]["user_json"])

    raw = payload["source_and_scenario"]["shared"]["source_rows"][0]["raw"]
    assert raw == scenario.shared.source_rows[0].raw
    assert payload["pilot_domain_state"]["role"] == "pilot"
    assert all(c["report"]["role"] == "pilot" for c in payload["candidates"])
    text = gw.calls[0]["user_json"]
    for foreign in ("wake_class_by_flight", "runway_open_windows", "crews", "occupied_windows"):
        assert foreign not in text
    assert "previous_messages" not in payload
    assert list(payload) == ["source_and_scenario", "current_proposal",
                             "pilot_domain_state", "candidates",
                             "output_schema", "final_reminder"]


def test_round_two_includes_previous_original_messages(scenario):
    r1 = make_request(scenario, current="P0")
    msg = PublicMessage(role="atc", proposal_id="run-1:r1",
                        plan_hash=r1.current_plan_hash,
                        decision=ModelDecision(verdict="COUNTER",
                                               ranked_alternative_ids=["P1"],
                                               cited_check_ids=[], reason="wake",
                                               uncertainty=""))
    req = make_request(scenario, current="P1", round_index=2, previous=[msg])
    gw = FakeGateway(decision())
    decide(req, gw)
    payload = json.loads(gw.calls[0]["user_json"])
    assert payload["previous_messages"][0] == msg.model_dump(mode="json")


def test_counter_to_valid_alternative(scenario):
    req = make_request(scenario, current="P0")
    reply = decide(req, FakeGateway(decision("COUNTER", ["P1", "P2"],
                                             [first_check(req, "P1")])))
    assert reply.result.decision.ranked_alternative_ids == ["P1", "P2"]


def expect_error(req, gw, code):
    with pytest.raises(AgentProtocolError) as err:
        decide(req, gw)
    assert err.value.code == code
    assert err.value.role == "pilot"
    assert err.value.request_id == req.request_id


def test_accept_with_own_hard_fail_is_invalid_accept(scenario):
    next(l for l in scenario.pilot.limits if l.flight_id == "F3").fuel_at_earliest_landing_kg = 999
    expect_error(make_request(scenario, current="P2"), FakeGateway(decision()),
                 "INVALID_ACCEPT")


def test_counter_to_locally_invalid_plan_rejected(scenario):
    next(l for l in scenario.pilot.limits if l.flight_id == "F3").fuel_at_earliest_landing_kg = 999
    expect_error(make_request(scenario, current="P0"),
                 FakeGateway(decision("COUNTER", ["P2"])), "INVALID_COUNTER")


def test_counter_naming_current_plan_rejected(scenario):
    expect_error(make_request(scenario, current="P1"),
                 FakeGateway(decision("COUNTER", ["P1"])), "MODEL_JSON_INVALID")


def test_counter_without_alternatives_rejected(scenario):
    expect_error(make_request(scenario), FakeGateway(decision("COUNTER")),
                 "MODEL_JSON_INVALID")


def test_reject_with_alternatives_rejected(scenario):
    expect_error(make_request(scenario), FakeGateway(decision("REJECT", ["P1"])),
                 "MODEL_JSON_INVALID")


def test_accept_with_alternatives_rejected(scenario):
    expect_error(make_request(scenario, current="P1"),
                 FakeGateway(decision("ACCEPT", ["P2"])), "MODEL_JSON_INVALID")


def test_duplicate_ranked_ids_rejected(scenario):
    expect_error(make_request(scenario), FakeGateway(decision("COUNTER", ["P1", "P1"])),
                 "MODEL_JSON_INVALID")


def test_unknown_candidate_rejected(scenario):
    expect_error(make_request(scenario), FakeGateway(decision("COUNTER", ["P9"])),
                 "UNKNOWN_CANDIDATE")


def test_unknown_check_rejected(scenario):
    expect_error(make_request(scenario, current="P1"),
                 FakeGateway(decision(cited=["atc:made-up:ATC_WAKE:F1:F2"])),
                 "UNKNOWN_CHECK")


def test_check_from_unranked_plan_rejected(scenario):
    req = make_request(scenario, current="P1")
    expect_error(req, FakeGateway(decision(cited=[first_check(req, "P2")])),
                 "UNKNOWN_CHECK")


def test_reject_may_cite_checks_from_any_candidate(scenario):
    req = make_request(scenario, current="P1")
    cited = [first_check(req, pid) for pid in ("P0", "P1", "P2")]
    reply = decide(req, FakeGateway(decision("REJECT", cited=cited)))
    assert reply.result.decision.cited_check_ids == cited


def test_reject_still_rejects_invented_checks(scenario):
    expect_error(make_request(scenario, current="P1"),
                 FakeGateway(decision("REJECT", cited=["pilot:made-up:PILOT_FUEL:F1"])),
                 "UNKNOWN_CHECK")


def test_rejected_reply_keeps_original_model_output(scenario):
    gw = FakeGateway(decision("COUNTER", ["P9"]))
    with pytest.raises(AgentProtocolError) as err:
        decide(make_request(scenario), gw)
    assert err.value.result.raw_text == json.dumps(gw.decision)


def test_non_pilot_request_rejected_before_model_call(scenario):
    req = make_request(scenario).model_copy(update={"role": "atc"})
    gw = FakeGateway(decision())
    expect_error(req, gw, "INPUT_SCHEMA_INVALID")
    assert gw.calls == []


def test_request_not_mutated(scenario):
    req = make_request(scenario, current="P1")
    before = req.model_dump_json()
    decide(req, FakeGateway(decision()))
    assert req.model_dump_json() == before
