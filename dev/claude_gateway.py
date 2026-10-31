"""TEMPORARY Claude ModelGateway for testing the ATC agent live.

Person D owns the real gateway (runtime/model_gateway.py). This one follows
the same contract so ATC can be exercised before integration: one call, SDK
retries disabled, per-call timeout, JSON-only output parsed strictly into
ModelDecision once. Failures raise AgentProtocolError; nothing is repaired.
"""
from __future__ import annotations

import os
import time

import anthropic
from pydantic import ValidationError

from contracts.models import AgentProtocolError, ModelDecision, ModelResult, Role, Usage

DEFAULT_MODEL = "claude-opus-5-5"

# Hand-written rather than ModelDecision.model_json_schema(): structured outputs
# accept a subset of JSON Schema, so length bounds are enforced by the strict
# Pydantic parse afterwards instead.
DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["ACCEPT", "COUNTER", "REJECT"]},
        "ranked_alternative_ids": {"type": "array", "items": {"type": "string"}},
        "cited_check_ids": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
        "uncertainty": {"type": "string"},
    },
    "required": ["verdict", "ranked_alternative_ids", "cited_check_ids", "reason", "uncertainty"],
    "additionalProperties": False,
}


class ClaudeGateway:
    def __init__(self, *, model: str | None = None, effort: str = "low",
                 client: anthropic.AsyncAnthropic | None = None):
        self.model = model or os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)
        self.effort = effort
        self.client = client or anthropic.AsyncAnthropic(max_retries=0)

    async def complete(
        self, *, role: Role, system_prompt: str, user_json: str,
        timeout_s: float, max_output_tokens: int
    ) -> ModelResult:
        def fail(code: str, detail: str) -> AgentProtocolError:
            return AgentProtocolError(code, role, "gateway", detail)

        started = time.monotonic()
        try:
            response = await self.client.with_options(timeout=timeout_s, max_retries=0).beta.messages.create(
                model=self.model,
                max_tokens=max_output_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_json}],
                output_config={
                    "effort": self.effort,
                    "format": {"type": "json_schema", "schema": DECISION_SCHEMA},
                },
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.APITimeoutError as e:
            raise fail("AGENT_TIMEOUT", f"no response within {timeout_s:.1f}s") from e
        except anthropic.APIStatusError as e:
            raise fail("MODEL_UNAVAILABLE", f"HTTP {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise fail("MODEL_UNAVAILABLE", f"connection error: {e}") from e
        elapsed_ms = int((time.monotonic() - started) * 1000)

        raw_text = "".join(b.text for b in response.content if b.type == "text")
        if response.stop_reason == "refusal":
            raise fail("MODEL_UNAVAILABLE", f"model declined: {getattr(response.stop_details, 'category', None)}")
        if response.stop_reason == "max_tokens":
            raise fail("MODEL_JSON_INVALID",
                       f"output cut off at max_tokens={max_output_tokens} before the JSON was complete")
        try:
            decision = ModelDecision.model_validate_json(raw_text)
        except ValidationError as e:
            raise fail("MODEL_JSON_INVALID", f"{e.error_count()} schema error(s): {e.errors()[0]['msg']}") from e

        return ModelResult(
            decision=decision,
            raw_text=raw_text,
            usage=Usage(
                provider="anthropic",
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model_calls=1,
                elapsed_ms=elapsed_ms,
            ),
        )
