"""Offline tests for the temporary Claude gateway, using a fake SDK client."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import anthropic
import httpx2 as httpx
import pytest

from contracts.models import AgentProtocolError
from dev.claude_gateway import DECISION_SCHEMA, ClaudeGateway

GOOD = {"verdict": "COUNTER", "ranked_alternative_ids": ["P1"], "cited_check_ids": [],
        "reason": "P0 fails wake separation.", "uncertainty": "Simulated separation values."}


class FakeClient:
    def __init__(self, *, text="", stop_reason="end_turn", error=None):
        self.text, self.stop_reason, self.error = text, stop_reason, error
        self.options, self.kwargs = None, None
        self.messages = SimpleNamespace(create=self._create)

    def with_options(self, **options):
        self.options = options
        return self

    async def _create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self.text)],
            stop_reason=self.stop_reason, stop_details=None, model="claude-opus-5-5",
            usage=SimpleNamespace(input_tokens=1200, output_tokens=90),
        )


def call(client: FakeClient, **options):
    gw = ClaudeGateway(client=client, **options)
    return asyncio.run(gw.complete(role="atc", system_prompt="sys", user_json="{}",
                                   timeout_s=9.5, max_output_tokens=800))


def test_valid_json_becomes_model_result_with_usage():
    client = FakeClient(text=json.dumps(GOOD))
    result = call(client)
    assert result.decision.verdict == "COUNTER" and result.raw_text == json.dumps(GOOD)
    assert result.usage.model_calls == 1 and result.usage.input_tokens == 1200
    assert client.options == {"timeout": 9.5, "max_retries": 0}
    assert client.kwargs["max_tokens"] == 800 and client.kwargs["model"] == "claude-opus-5-5"
    assert "output_config" not in client.kwargs  # default mirrors D's plain gateway call


def test_structured_mode_adds_schema_and_effort():
    client = FakeClient(text=json.dumps(GOOD))
    call(client, structured=True)
    assert client.kwargs["output_config"] == {
        "effort": "low", "format": {"type": "json_schema", "schema": DECISION_SCHEMA}}


def test_code_fenced_json_is_rejected_like_ds_gateway():
    with pytest.raises(AgentProtocolError) as err:
        call(FakeClient(text="```json\n" + json.dumps(GOOD) + "\n```"))
    assert err.value.code == "MODEL_JSON_INVALID"


@pytest.mark.parametrize("client, code", [
    (FakeClient(text='{"verdict": "COUNTER"'), "MODEL_JSON_INVALID"),
    (FakeClient(text=json.dumps({**GOOD, "extra": 1})), "MODEL_JSON_INVALID"),
    (FakeClient(text=json.dumps({**GOOD, "reason": ""})), "MODEL_JSON_INVALID"),
    (FakeClient(text="", stop_reason="max_tokens"), "MODEL_JSON_INVALID"),
    (FakeClient(text="", stop_reason="refusal"), "MODEL_UNAVAILABLE"),
    (FakeClient(error=anthropic.APITimeoutError(request=httpx.Request("POST", "https://x"))), "AGENT_TIMEOUT"),
    (FakeClient(error=anthropic.APIConnectionError(request=httpx.Request("POST", "https://x"))), "MODEL_UNAVAILABLE"),
])
def test_failures_raise_typed_protocol_errors(client, code):
    with pytest.raises(AgentProtocolError) as err:
        call(client)
    assert err.value.code == code and err.value.role == "atc"
