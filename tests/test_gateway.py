"""Exercise real HTTP gateway/parsing/budgets with a mocked provider transport."""
import asyncio
import json

import httpx
import pytest

from agents import atc, ground, pilot
from app import default_agents
from contracts.models import AgentProtocolError, ModelDecision, ScenarioInput
from runtime.coordinator import run_negotiation
from runtime.model_gateway import AnthropicGateway, OfflineGateway
from runtime.scenario_loader import EXAMPLE


def provider(handler):
    return AnthropicGateway(model="test-model", api_key="test-secret-credential", transport=httpx.MockTransport(handler))


async def good_body(request):
    body = json.loads(request.content)
    user = body["messages"][0]["content"]
    role = json.loads(user)["candidates"][0]["report"]["role"]
    r = await OfflineGateway().complete(role=role, system_prompt=body["system"], user_json=user,
                                       timeout_s=1, max_output_tokens=1600)
    return {"content": [{"type": "text", "text": r.raw_text}], "model": "test-model",
            "stop_reason": "end_turn", "usage": {"input_tokens": 1000, "output_tokens": 200}}


def test_real_http_gateway_integrates_all_roles_and_counts_calls(tmp_path):
    requests = []

    async def handler(request):
        requests.append(request)
        assert request.headers["x-api-key"] == "test-secret-credential"
        if request.url.path.endswith("count_tokens"):
            return httpx.Response(200, json={"input_tokens": 1000})
        return httpx.Response(200, json=await good_body(request))

    r = asyncio.run(run_negotiation(EXAMPLE, default_agents(), provider(handler), log_dir=tmp_path))
    assert r.outcome == "CONSENSUS" and r.selected_plan_id == "P1"
    assert r.model_calls_attempted == r.model_calls_completed == 6
    assert len(r.usage) == 6 and sum(u.input_tokens for u in r.usage) == 6000
    assert sum(u.output_tokens for u in r.usage) == 1200
    assert len(requests) == 12  # 6 token-count requests, 6 model generations, no retries.
    # Each generation carries its own agent's declared output cap (ATC 800, pilot/ground 1600).
    caps = {"atc": atc.MAX_OUTPUT_TOKENS, "pilot": pilot.MAX_OUTPUT_TOKENS, "ground": ground.MAX_OUTPUT_TOKENS}
    for req in requests:
        if not req.url.path.endswith("count_tokens"):
            body = json.loads(req.content)
            role = json.loads(body["messages"][0]["content"])["candidates"][0]["report"]["role"]
            assert body["max_tokens"] == caps[role]
    assert "test-secret-credential" not in (tmp_path / r.event_log_ref).read_text()


@pytest.mark.parametrize("failure", ["invalid-json", "truncated", "wrong-types", "extra-field"])
def test_bad_provider_output_uses_fallback_and_retains_cost_evidence(tmp_path, failure):
    async def handler(request):
        if request.url.path.endswith("count_tokens"):
            return httpx.Response(200, json={"input_tokens": 1000})
        body = await good_body(request)
        if failure == "truncated":
            body["stop_reason"] = "max_tokens"
        elif failure == "invalid-json":
            body["content"][0]["text"] = "not JSON test-secret-credential"
        else:
            decision = json.loads(body["content"][0]["text"])
            if failure == "wrong-types":
                decision["reason"] = 9
            else:
                decision["invented"] = True
            body["content"][0]["text"] = json.dumps(decision)
        return httpx.Response(200, json=body)
    r = asyncio.run(run_negotiation(EXAMPLE, default_agents(), provider(handler), log_dir=tmp_path))
    assert r.outcome == "FALLBACK" and r.reason_code == "MODEL_JSON_INVALID"
    assert r.model_calls_attempted == r.model_calls_completed == 3
    assert len(r.usage) == 3 and sum(u.output_tokens for u in r.usage) == 600
    evidence = (tmp_path / r.event_log_ref).read_text()
    assert "test-secret-credential" not in evidence
    assert '"raw_text"' in evidence


def test_token_count_over_budget_never_generates(tmp_path):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"input_tokens": 8001})
    r = asyncio.run(run_negotiation(EXAMPLE, default_agents(), provider(handler), log_dir=tmp_path))
    assert r.outcome == "FALLBACK" and r.reason_code == "CONTEXT_BUDGET_EXCEEDED"
    assert r.model_calls_attempted == 0 and len(calls) == 3
    assert all(path.endswith("count_tokens") for path in calls)


def test_provider_transport_error_no_retry(tmp_path):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("count_tokens"):
            return httpx.Response(200, json={"input_tokens": 1000})
        return httpx.Response(503, text="transport diagnostics test-secret-credential")
    r = asyncio.run(run_negotiation(EXAMPLE, default_agents(), provider(handler), log_dir=tmp_path))
    assert r.outcome == "FALLBACK" and r.reason_code == "MODEL_UNAVAILABLE"
    assert r.model_calls_attempted == 3 and r.model_calls_completed == 0
    assert len(calls) == 6
    assert "test-secret-credential" not in (tmp_path / r.event_log_ref).read_text()


def test_missing_checks_never_form_a_valid_plan(tmp_path, monkeypatch):
    import domains.atc
    original = domains.atc.evaluate_atc
    def empty(*args, **kwargs):
        return original(*args, **kwargs).model_copy(update={"checks": []})
    monkeypatch.setattr(domains.atc, "evaluate_atc", empty)
    r = asyncio.run(run_negotiation(EXAMPLE, default_agents(), OfflineGateway(), log_dir=tmp_path))
    assert r.outcome == "ESCALATED" and r.reason_code == "EVALUATOR_ERROR"
    assert r.selected_plan is None and r.agent_invocations == 0
