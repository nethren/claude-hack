"""Integrated real adapters/evaluators, controlled model responses; no live AI."""
import asyncio
import json
from pathlib import Path

import pytest

from app import default_agents
from contracts.models import AgentProtocolError, AgentReply, ModelDecision, ModelResult, ScenarioInput, Usage
from runtime.coordinator import run_negotiation
from runtime.model_gateway import OfflineGateway
from runtime.models import Budgets
from runtime.scenario_loader import EXAMPLE


@pytest.fixture
def scenario():
    return ScenarioInput.model_validate_json(EXAMPLE.read_bytes())


class ScriptedGateway(OfflineGateway):
    def __init__(self, decisions=None):
        self.decisions = decisions or {}
        self.calls = []

    async def complete(self, **kwargs):
        role = kwargs["role"]
        payload = json.loads(kwargs["user_json"])
        round_index = payload["current_proposal"]["round_index"]
        self.calls.append((role, round_index, payload))
        override = self.decisions.get((role, round_index))
        if isinstance(override, Exception):
            raise override
        if override is None:
            return await super().complete(**kwargs)
        if callable(override):
            override = override(payload)
        d = ModelDecision.model_validate(override)
        return ModelResult(decision=d, raw_text=d.model_dump_json(), usage=Usage(provider="offline-test-double",
            model="scripted", input_tokens=None, output_tokens=None, model_calls=0, elapsed_ms=0))


def decision(verdict, ranked=(), cited=()):
    return dict(verdict=verdict, ranked_alternative_ids=list(ranked), cited_check_ids=list(cited),
                reason="Offline controlled response", uncertainty="Not a live model")


def run(scenario, tmp_path, model=None, agents=None, **kwargs):
    return asyncio.run(run_negotiation(scenario, agents or default_agents(), model or ScriptedGateway(),
                                      log_dir=tmp_path, **kwargs))


def events(result, directory):
    return [json.loads(line) for line in (directory / result.event_log_ref).read_text().splitlines()]


def test_full_negotiation_and_exact_context_boundaries(scenario, tmp_path):
    before = scenario.model_dump_json()
    model = ScriptedGateway()
    result = run(scenario, tmp_path, model)
    assert result.outcome == "CONSENSUS"
    assert result.selected_plan_id == "P1"
    assert result.rounds_completed == 2
    assert result.agent_invocations == len(model.calls) == 6
    assert result.model_calls_attempted == result.model_calls_completed == 0
    assert result.metrics == dict(throughput_count=3, additional_delay_min=2,
        turbulence_units=3, missed_connections=0, overtime_min=2, turnaround_delay_min=0, gate_busy_min=24)
    assert len(result.acceptances) == 3 and len(result.final_reports) == 3
    assert scenario.model_dump_json() == before
    for role, round_index, payload in model.calls:
        assert payload["source_and_scenario"]["shared"]["source_rows"] == scenario.shared.model_dump()["source_rows"]
        assert [key for key in payload if key.endswith("_domain_state")] == [f"{role}_domain_state"]
        assert all(c["report"]["role"] == role for c in payload["candidates"])
        assert all(c["report"]["scenario_hash"] == result.scenario_hash for c in payload["candidates"])
        if round_index == 1:
            assert "previous_messages" not in payload
        else:
            assert len(payload["previous_messages"]) == 3
            originals = [e["payload"]["reply"] for e in events(result, tmp_path)
                         if e["type"] == "AGENT_REPLIED" and e["payload"]["reply"]["round_index"] == 1]
            assert [m["decision"] for m in payload["previous_messages"]] == [r["result"]["decision"] for r in originals]
    trace = events(result, tmp_path)
    assert [e["sequence"] for e in trace] == list(range(1, len(trace)+1))
    assert trace[-1]["type"] == "RUN_FINISHED"
    assert (tmp_path / f"{result.run_id}.result.json").is_file()


def test_already_valid_initial_plan_consensus_one_round(scenario, tmp_path):
    scenario.initial_plan_id = "P1"
    r = run(scenario, tmp_path)
    assert r.outcome == "CONSENSUS" and r.rounds_completed == 1 and r.agent_invocations == 3


def test_conflicting_counters_use_policy_not_votes_or_rank_position(scenario, tmp_path):
    model = ScriptedGateway({("atc", 1): decision("COUNTER", ["P2", "P1"]),
                             ("pilot", 1): decision("COUNTER", ["P2"]),
                             ("ground", 1): decision("COUNTER", ["P1"])})
    r = run(scenario, tmp_path, model)
    assert r.outcome == "CONSENSUS" and r.selected_plan_id == "P1"


def test_pool_only_contains_actual_counters_not_entire_catalog(scenario, tmp_path):
    model = ScriptedGateway({(role, 1): decision("COUNTER", ["P2"]) for role in ("atc", "pilot", "ground")})
    r = run(scenario, tmp_path, model)
    assert r.outcome == "CONSENSUS" and r.selected_plan_id == "P2"


def test_disagreement_after_round_two_uses_checked_global_fallback(scenario, tmp_path):
    model = ScriptedGateway({("pilot", 2): decision("COUNTER", ["P2"])})
    r = run(scenario, tmp_path, model)
    assert r.outcome == "FALLBACK" and r.reason_code == "ROUND_LIMIT" and r.selected_plan_id == "P1"
    assert r.rounds_completed == 2 and r.acceptances == [] and r.proposal_id is None


@pytest.mark.parametrize("override,code", [
    (decision("COUNTER", ["invented"]), "UNKNOWN_CANDIDATE"),
    (decision("COUNTER", ["P1", "P1"]), "MODEL_JSON_INVALID"),
    (decision("ACCEPT"), "INVALID_ACCEPT"),
    (decision("COUNTER", ["P1"], ["invented-rule"]), "UNKNOWN_CHECK"),
    (AgentProtocolError("MODEL_UNAVAILABLE", "atc", "test", "Provider unavailable"), "MODEL_UNAVAILABLE"),
])
def test_bad_reply_fails_closed_to_fallback(scenario, tmp_path, override, code):
    r = run(scenario, tmp_path, ScriptedGateway({("atc", 1): override}))
    assert r.outcome == "FALLBACK" and r.selected_plan_id == "P1"
    assert r.reason_code == code and r.acceptances == []


class BypassAgent:
    """Deliberately omit adapter validation to exercise coordinator's own boundary."""
    def __init__(self, field=None, value=None, mutate=False, duplicate=False):
        self.field, self.value, self.mutate, self.duplicate = field, value, mutate, duplicate

    async def decide(self, request, *, model):
        from agents.atc import SYSTEM_PROMPT
        from agents.pilot import build_user_json
        result = await model.complete(role=request.role, system_prompt=SYSTEM_PROMPT,
            user_json=build_user_json(request), timeout_s=request.call_timeout_ms/1000, max_output_tokens=1600)
        if self.duplicate:
            await model.complete(role=request.role, system_prompt=SYSTEM_PROMPT,
                user_json=build_user_json(request), timeout_s=1, max_output_tokens=1600)
        if self.mutate:
            request.shared.source_rows[0].raw["WEATHER_DELAY"] = "900"
        keys = ("protocol_version", "run_id", "request_id", "role", "scenario_version", "scenario_hash",
                "round_index", "proposal_id", "current_plan_id", "current_plan_hash")
        reply = AgentReply(**{k: getattr(request, k) for k in keys}, result=result)
        return reply.model_copy(update={self.field: self.value}) if self.field else reply


@pytest.mark.parametrize("field,value", [("scenario_version", 2), ("scenario_hash", "0"*64),
    ("run_id", "old"), ("request_id", "old"), ("proposal_id", "old"), ("round_index", 2),
    ("current_plan_id", "P2"), ("current_plan_hash", "0"*64), ("role", "pilot")])
def test_every_stale_identity_is_rejected(scenario, tmp_path, field, value):
    agents = default_agents()
    agents["atc"] = BypassAgent(field, value)
    r = run(scenario, tmp_path, agents=agents)
    assert r.outcome == "FALLBACK" and r.reason_code == "STALE_REPLY"


def test_coordinator_does_not_trust_adapter_acceptance(scenario, tmp_path):
    agents = default_agents()
    agents["atc"] = BypassAgent()
    r = run(scenario, tmp_path, ScriptedGateway({("atc", 1): decision("ACCEPT")}), agents)
    assert r.outcome == "FALLBACK" and r.reason_code == "INVALID_ACCEPT"


def test_mutation_and_extra_calls_rejected(scenario, tmp_path):
    for flag, code in (("mutate", "REQUEST_MUTATED"), ("duplicate", "CALL_BUDGET_EXCEEDED")):
        directory = tmp_path / flag
        agents = default_agents()
        agents["atc"] = BypassAgent(**{flag: True})
        r = run(scenario, directory, agents=agents)
        assert r.outcome == "FALLBACK" and r.reason_code == code
        assert r.selected_plan_id == "P1"


def test_timeout_is_bounded_and_late_response_cannot_vote(scenario, tmp_path):
    class SlowGateway(ScriptedGateway):
        async def complete(self, **kwargs):
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                await asyncio.sleep(.005)
            return await super().complete(**kwargs)
    r = run(scenario, tmp_path, SlowGateway(), budgets=Budgets(call_s=.01, negotiation_s=.5, whole_run_s=1))
    assert r.outcome == "FALLBACK" and r.reason_code == "AGENT_TIMEOUT"
    assert r.elapsed_ms < 1000 and r.acceptances == []
    assert r.model_calls_completed == 0


def test_repeated_current_proposal_exits_without_third_round(scenario, tmp_path):
    scenario.initial_plan_id = "P1"
    r = run(scenario, tmp_path, ScriptedGateway({("pilot", 1): decision("COUNTER", ["P2"])}))
    assert r.outcome == "FALLBACK" and r.reason_code == "REPEATED_PROPOSAL"
    assert r.agent_invocations == 3


def test_no_feasible_candidate_escalates_without_fake_consensus(scenario, tmp_path):
    scenario.atc.runway_open_windows = []
    r = run(scenario, tmp_path)
    assert r.outcome == "ESCALATED" and r.reason_code == "NO_VALID_PLAN_IN_CATALOG"
    assert r.selected_plan is None and r.final_reports == [] and r.metrics is None and r.acceptances == []


def test_insufficient_context_does_not_drop_constraints(scenario, tmp_path):
    r = run(scenario, tmp_path, budgets=Budgets(input_bytes=10))
    assert r.outcome == "FALLBACK" and r.reason_code == "CONTEXT_BUDGET_EXCEEDED"
    assert r.model_calls_attempted == 0


def test_fuel_limit_and_changed_crew_scenario_invalidate_old_plan(scenario, tmp_path):
    old = run(scenario, tmp_path)
    scenario.scenario_version += 1
    scenario.ground.crews[1].available_windows[0].start_min = 20
    new = run(scenario, tmp_path)
    assert old.selected_plan_id == "P1" and new.selected_plan_id == "P2"
    assert new.outcome == "CONSENSUS" and new.rounds_completed == 2
    assert old.run_id != new.run_id and old.scenario_hash != new.scenario_hash
    assert all(r.scenario_version == 2 and r.scenario_hash == new.scenario_hash for r in new.acceptances)
    failures = [c for r in new.candidate_reports["P1"] for c in r.checks if c.status == "FAIL"]
    assert any(c.rule_id == "GROUND_CREW" and c.flight_ids == ["F2"] for c in failures)
    # Equality with F3's configured reserve remains valid.
    fuel = next(c for r in new.final_reports for c in r.checks if c.rule_id == "PILOT_FUEL" and c.flight_ids == ["F3"])
    assert fuel.status == "PASS" and "fuel_at_landing_kg=800" in fuel.observed


def test_fallback_reproducible_across_candidate_order(scenario, tmp_path):
    decisions = {("atc", 1): AgentProtocolError("MODEL_UNAVAILABLE", "atc", "test", "unavailable")}
    a = run(scenario, tmp_path, ScriptedGateway(decisions))
    scenario.plans.reverse()
    scenario.scenario_version += 1
    b = run(scenario, tmp_path, ScriptedGateway(decisions))
    assert a.selected_plan_hash == b.selected_plan_hash and a.metrics == b.metrics
