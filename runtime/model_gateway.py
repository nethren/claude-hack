"""One-call gateways: labelled offline smoke test or configured Anthropic REST.

No SDK retries or model repair. Provider exceptions never include request headers
in persisted errors. The transport can be injected for offline HTTP tests.
"""
import asyncio
import json
import os
import time

import httpx
from pydantic import ValidationError

from contracts.models import AgentProtocolError, ModelDecision, ModelResult, Usage


class OfflineGateway:
    """Deterministic test double exercising actual adapters, never a live AI claim."""
    mode = "offline"

    async def complete(self, *, role, system_prompt, user_json, timeout_s, max_output_tokens):
        p = json.loads(user_json)
        candidates = p["candidates"]
        current = p["current_proposal"]["current_plan_id"]

        def valid(view):
            hard = [c for c in view["report"]["checks"] if c["severity"] == "HARD"]
            return bool(hard) and all(c["status"] in ("PASS", "NOT_APPLICABLE") for c in hard)

        own = next(c for c in candidates if c["plan"]["plan_id"] == current)
        alternatives = [c["plan"]["plan_id"] for c in candidates if c["plan"]["plan_id"] != current and valid(c)]
        verdict = "ACCEPT" if valid(own) else "COUNTER" if alternatives else "REJECT"
        decision = ModelDecision(verdict=verdict,
                                 ranked_alternative_ids=alternatives if verdict == "COUNTER" else [],
                                 cited_check_ids=[own["report"]["checks"][0]["check_id"]],
                                 reason="Offline test double: decision from supplied own-domain checks.",
                                 uncertainty="Scripted integration test, not an LLM result.")
        return ModelResult(decision=decision, raw_text=decision.model_dump_json(),
                           usage=Usage(provider="offline-test-double", model="rules-smoke-test",
                                       input_tokens=None, output_tokens=None, model_calls=0, elapsed_ms=0))


class AnthropicGateway:
    mode = "live"

    def __init__(self, *, model: str, api_key: str, base_url="https://api.anthropic.com", transport=None):
        if not model or not api_key:
            raise ValueError("Set ANTHROPIC_MODEL and ANTHROPIC_API_KEY for live mode")
        self.model, self._api_key = model, api_key
        self.base_url, self.transport = base_url.rstrip("/"), transport

    async def count_input_tokens(self, system_prompt, user_json, timeout_s, *, role):
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=timeout_s) as client:
                response = await client.post(self.base_url + "/v1/messages/count_tokens",
                    headers={"x-api-key": self._api_key, "anthropic-version": "2023-06-01"},
                    json={"model": self.model, "system": system_prompt,
                          "messages": [{"role": "user", "content": user_json}]})
                response.raise_for_status()
                count = response.json()["input_tokens"]
                if type(count) is not int or count < 0:
                    raise ValueError
                return count
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise AgentProtocolError("CONTEXT_COUNT_UNAVAILABLE", role, f"gateway:count:{role}",
                                     "Provider token count unavailable; do not send unbounded context") from exc

    async def complete(self, *, role, system_prompt, user_json, timeout_s, max_output_tokens):
        started = time.monotonic()
        request_id = f"gateway:{role}"
        raw = ""
        usage = None
        async with httpx.AsyncClient(transport=self.transport, timeout=timeout_s) as client:
            try:
                async with asyncio.timeout(timeout_s):
                    response = await client.post(self.base_url + "/v1/messages",
                        headers={"x-api-key": self._api_key, "anthropic-version": "2023-06-01"},
                        json={"model": self.model, "max_tokens": max_output_tokens,
                              "system": system_prompt, "messages": [{"role": "user", "content": user_json}]})
                    response.raise_for_status()
                    data = response.json()
                raw = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
                # A known secret is removed before parsing or recording any returned text.
                raw = raw.replace(self._api_key, "[REDACTED]")
                u = data.get("usage", {})
                usage = Usage(provider="anthropic", model=data.get("model", self.model),
                              input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"),
                              model_calls=1, elapsed_ms=int((time.monotonic()-started)*1000))
                if data.get("stop_reason") != "end_turn":
                    raise ValueError("Provider did not finish a complete decision")
                decision = ModelDecision.model_validate_json(raw)
                return ModelResult(decision=decision, raw_text=raw, usage=usage)
            except (httpx.TimeoutException, TimeoutError) as exc:
                raise AgentProtocolError("AGENT_TIMEOUT", role, request_id, "Provider call exceeded deadline") from exc
            except httpx.HTTPError as exc:
                raise AgentProtocolError("MODEL_UNAVAILABLE", role, request_id, "Provider HTTP/transport failure; no retry") from exc
            except (ValueError, KeyError, TypeError, ValidationError) as exc:
                err = AgentProtocolError("MODEL_JSON_INVALID", role, request_id, "Provider returned incomplete/invalid ModelDecision JSON")
                err.raw_text = raw
                err.usage = usage
                raise err from exc


def gateway_from_environment(mode="offline"):
    if mode == "offline":
        return OfflineGateway()
    if mode != "live":
        raise ValueError("mode must be offline or live")
    return AnthropicGateway(model=os.environ.get("ANTHROPIC_MODEL", ""),
                            api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
