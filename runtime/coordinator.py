"""Bounded deterministic coordinator; contains no LLM scheduling decisions."""
import asyncio
import json
import time
from pathlib import Path
from uuid import uuid4

from contracts.models import (AgentProtocolError, AgentRequest, CandidateView,
                              ModelResult, PublicMessage, plan_hash, scenario_hash)
from runtime.catalog import ROLES, evaluate, globally_valid, metrics, rank
from runtime.event_log import EventLog
from runtime.models import Budgets, RunResult
from runtime.reply_validation import validate_reply
from runtime.scenario_loader import InputError, ROOT, load_scenario
from runtime.scenario_store import claim_revision

WARNINGS = [
    "Historical replay with explicitly simulated operational inputs; not live telemetry.",
    "Two rounds is the project's interpretation of 'under 3 turns'; organizer wording is unconfirmed.",
    "Bounded catalog, simplified holding fuel/single-runway model; no aviation safety certification or global optimality.",
    "Recommendation requires qualified human review; this backend does not execute airport actions.",
]


class CallLedger:
    def __init__(self):
        self.attempted = 0
        self.completed = 0
        self.usage = []


class ScopedGateway:
    """One gateway call per request, with independent role/deadline/budget caps."""
    def __init__(self, gateway, request, budgets, ledger, log, negotiation_deadline):
        self.gateway, self.request, self.budgets = gateway, request, budgets
        self.ledger, self.log = ledger, log
        self.deadline = negotiation_deadline
        self.calls = 0
        self.active = True
        self.result = None

    async def complete(self, *, role, system_prompt, user_json, timeout_s, max_output_tokens):
        req = self.request
        def error(code, detail):
            return AgentProtocolError(code, req.role, req.request_id, detail)
        if not self.active or self.calls or role != req.role:
            raise error("CALL_BUDGET_EXCEEDED", "Exactly one call for the assigned role is permitted")
        self.calls += 1
        if len((system_prompt + user_json).encode("utf-8")) > self.budgets.input_bytes:
            raise error("CONTEXT_BUDGET_EXCEEDED", "Complete context exceeds configured byte ceiling")
        remaining = min(timeout_s, req.call_timeout_ms / 1000, self.deadline-time.monotonic())
        if remaining <= 0:
            raise error("AGENT_TIMEOUT", "No negotiation time remains")
        if max_output_tokens > self.budgets.output_tokens:
            raise error("OUTPUT_BUDGET_EXCEEDED", "Adapter output cap exceeds the shared budget")
        # Count endpoint is not a model generation; live providers must report it.
        if hasattr(self.gateway, "count_input_tokens"):
            async with asyncio.timeout(remaining):
                count = await self.gateway.count_input_tokens(system_prompt, user_json, remaining, role=role)
            self.log.emit("CONTEXT_COUNTED", {"role": role, "input_tokens": count}, proposal_id=req.proposal_id)
            if count > self.budgets.input_tokens:
                raise error("CONTEXT_BUDGET_EXCEEDED", "Full prompt exceeds input token cap")
        if not self.active:
            raise error("AGENT_TIMEOUT", "Request was cancelled")
        if getattr(self.gateway, "mode", None) != "offline":
            self.ledger.attempted += 1
        try:
            async with asyncio.timeout(min(remaining, self.deadline-time.monotonic())):
                result = await self.gateway.complete(role=role, system_prompt=system_prompt, user_json=user_json,
                    timeout_s=min(remaining, self.deadline-time.monotonic()), max_output_tokens=max_output_tokens)
        except AgentProtocolError as exc:
            if self.active and getattr(exc, "usage", None) is not None:
                self.ledger.usage.append(exc.usage)
                self.ledger.completed += exc.usage.model_calls
            raise
        if not self.active:
            raise error("STALE_REPLY", "Discarded late provider result")
        result = ModelResult.model_validate_json(result.model_dump_json())
        self.ledger.usage.append(result.usage)
        self.ledger.completed += result.usage.model_calls
        self.log.emit("MODEL_COMPLETED", {"role": role, "result": result.model_dump(mode="json")}, proposal_id=req.proposal_id)
        if result.decision != result.decision.model_validate_json(result.raw_text):
            raise error("MODEL_JSON_INVALID", "Parsed decision differs from original response JSON")
        if result.usage.output_tokens is not None and result.usage.output_tokens > max_output_tokens:
            raise error("OUTPUT_BUDGET_EXCEEDED", "Provider exceeded output token ceiling")
        self.result = result
        return result


def _discard_task(task):
    # Retrieve late exceptions; no late task can cast a vote or modify canonical state.
    if not task.cancelled():
        task.exception()


async def run_negotiation(scenario, agents, model, *, budgets=None, log_dir=None, source_root=ROOT) -> RunResult:
    budgets = budgets or Budgets()
    started = time.monotonic()
    negotiation_deadline = started + budgets.negotiation_s
    whole_deadline = started + budgets.whole_run_s
    run_id = uuid4().hex
    log_dir = Path(log_dir) if log_dir is not None else ROOT / "logs"
    log = EventLog(run_id, log_dir, started=started)
    ledger = CallLedger()
    s, digest, reports = None, None, {}
    rounds, invocations = 0, 0
    warnings = list(WARNINGS)
    if getattr(model, "mode", None) == "offline":
        warnings.append("OFFLINE TEST DOUBLE: real adapters/evaluators, scripted model replies; no live LLM calls.")

    def emit(kind, payload=None, proposal=None):
        log.emit(kind, payload, proposal_id=proposal)

    def finish(outcome, reason, *, selected=None, final=None, acceptances=None, proposal=None, trigger=None):
        result = RunResult(run_id=run_id, scenario_id=s.scenario_id if s else None,
            scenario_version=s.scenario_version if s else None, scenario_hash=digest,
            outcome=outcome, reason_code=reason, trigger_code=trigger,
            proposal_id=proposal if outcome == "CONSENSUS" else None,
            selected_plan_id=selected.plan_id if selected else None,
            selected_plan_hash=plan_hash(selected) if selected else None, selected_plan=selected,
            final_reports=final or [], acceptances=acceptances or [], metrics=metrics(final) if final else None,
            rounds_completed=rounds, agent_invocations=invocations,
            model_calls_attempted=ledger.attempted, model_calls_completed=ledger.completed,
            usage=ledger.usage, elapsed_ms=int((time.monotonic()-started)*1000), warnings=warnings,
            event_log_ref=log.path.name, candidate_reports=reports)
        emit("RUN_FINISHED", {"outcome": outcome, "reason_code": reason, "trigger_code": trigger,
                              "selected_plan_id": result.selected_plan_id,
                              "rounds_completed": rounds, "model_calls_attempted": ledger.attempted,
                              "model_calls_completed": ledger.completed, "agent_invocations": invocations})
        result_path = log_dir / f"{run_id}.result.json"
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        log.close()
        return result

    def recheck(plan):
        if time.monotonic() >= whole_deadline:
            raise TimeoutError
        final = evaluate(plan, s, digest)
        if time.monotonic() >= whole_deadline:
            raise TimeoutError
        emit("FINAL_VALIDATED", {"plan_id": plan.plan_id,
                               "reports": [r.model_dump(mode="json") for r in final]})
        return final

    def fallback(trigger):
        emit("FALLBACK_STARTED", {"trigger_code": trigger})
        try:
            # Re-evaluate every candidate, rather than trust model votes or stale caches.
            valid = []
            for plan in s.plans:
                final = recheck(plan)
                if globally_valid(final):
                    valid.append((plan, final))
            if not valid:
                unknown = any(c.status == "UNKNOWN" for rs in reports.values() for r in rs for c in r.checks)
                return finish("ESCALATED", "CHECK_UNKNOWN" if unknown else "NO_VALID_PLAN_IN_CATALOG", trigger=trigger)
            selected, _ = min(valid, key=lambda pair: rank(*pair))
            final = recheck(selected)
            if not globally_valid(final):
                return finish("ESCALATED", "FINAL_VALIDATION_FAILED", trigger=trigger)
            return finish("FALLBACK", trigger, selected=selected, final=final, trigger=trigger)
        except TimeoutError:
            return finish("ESCALATED", "FALLBACK_BUDGET_EXHAUSTED", trigger=trigger)
        except Exception:
            emit("CHECK_FAILED", {"code": "EVALUATOR_ERROR"})
            return finish("ESCALATED", "EVALUATOR_ERROR", trigger=trigger)

    try:
        s = load_scenario(scenario, root=source_root)
        # This serialization is the sole canonical state; no collaborator receives it by reference.
        snapshot = s.model_dump_json()
        digest = scenario_hash(s)
        log.scenario_version, log.scenario_hash = s.scenario_version, digest
        if set(agents) != set(ROLES):
            raise InputError("INPUT_SCHEMA_INVALID", "Provide exactly atc, pilot and ground agents")
        claim_revision(log_dir, s.scenario_id, s.scenario_version, digest)
        emit("INPUT_VALIDATED", {"scenario": json.loads(snapshot),
            "agent_versions": {role: {"prompt": getattr(agents[role], "prompt_version", "unknown"),
                                      "rules": getattr(agents[role], "rules_version", "unknown")} for role in ROLES},
            "budgets": vars(budgets)})
        for plan in s.plans:
            if time.monotonic() >= whole_deadline:
                return finish("ESCALATED", "FALLBACK_BUDGET_EXHAUSTED")
            reports[plan.plan_id] = evaluate(plan, s, digest)
            emit("DOMAIN_CHECKED", {"plan_id": plan.plan_id,
                 "reports": [r.model_dump(mode="json") for r in reports[plan.plan_id]]})
    except InputError as exc:
        emit("INPUT_REJECTED", {"code": exc.code, "detail": exc.detail})
        return finish("INPUT_ERROR", exc.code)
    except Exception:
        emit("CHECK_FAILED", {"code": "EVALUATOR_ERROR"})
        return finish("ESCALATED", "EVALUATOR_ERROR")

    current = next(p for p in s.plans if p.plan_id == s.initial_plan_id)
    previous, visited = [], set()
    for round_index in (1, 2):
        if time.monotonic() >= negotiation_deadline:
            return fallback("NEGOTIATION_BUDGET_EXHAUSTED")
        proposal = f"{run_id}:r{round_index}"
        visited.add(plan_hash(current))
        emit("PROPOSAL_PUBLISHED", {"round_index": round_index, "plan": current.model_dump(mode="json"),
                                    "plan_hash": plan_hash(current)}, proposal)
        requests, scopes, private_requests, tasks = {}, {}, {}, {}
        timeout = min(budgets.call_s, negotiation_deadline-time.monotonic())
        for index, role in enumerate(ROLES):
            req = AgentRequest(protocol_version="1.0", run_id=run_id, request_id=f"{proposal}:{role}",
                role=role, scenario_id=s.scenario_id, scenario_version=s.scenario_version, scenario_hash=digest,
                round_index=round_index, proposal_id=proposal, current_plan_id=current.plan_id,
                current_plan_hash=plan_hash(current), call_timeout_ms=max(1, min(15000, int(timeout*1000))),
                shared=s.shared, domain=getattr(s, role),
                candidates=[CandidateView(plan=p, plan_hash=plan_hash(p), report=reports[p.plan_id][index]) for p in s.plans],
                previous_messages=previous)
            requests[role] = AgentRequest.model_validate_json(req.model_dump_json())
            private = AgentRequest.model_validate_json(req.model_dump_json())
            private_requests[role] = private
            scope = ScopedGateway(model, requests[role], budgets, ledger, log, negotiation_deadline)
            scopes[role] = scope
            emit("AGENT_STARTED", {"request": requests[role].model_dump(mode="json")}, proposal)
            invocations += 1
            tasks[role] = asyncio.create_task(agents[role].decide(private, model=scope))
        try:
            done, pending = await asyncio.wait(tasks.values(), timeout=timeout, return_when=asyncio.FIRST_EXCEPTION)
        except asyncio.CancelledError:
            for scope in scopes.values():
                scope.active = False
            for task in tasks.values():
                task.cancel()
                task.add_done_callback(_discard_task)
            emit("RUN_CANCELLED", {"reason": "Caller cancelled; pending votes invalidated"}, proposal)
            log.close()
            raise
        failure = None
        replies = []
        for role in ROLES:
            task, req = tasks[role], requests[role]
            if task not in done:
                continue
            try:
                reply = task.result()
                if private_requests[role].model_dump_json() != req.model_dump_json():
                    raise AgentProtocolError("REQUEST_MUTATED", role, req.request_id, "Agent changed its input snapshot")
                if scopes[role].calls != 1 or scopes[role].result is None:
                    raise AgentProtocolError("INVALID_MODEL_CALL_COUNT", role, req.request_id, "Agent did not finish one gateway call")
                reply = validate_reply(reply, req)
                if reply.result != scopes[role].result:
                    raise AgentProtocolError("MODEL_JSON_INVALID", role, req.request_id, "Reply result differs from gateway result")
                replies.append(reply)
                emit("AGENT_REPLIED", {"reply": reply.model_dump(mode="json")}, proposal)
            except AgentProtocolError as exc:
                failure = failure or exc.code
                payload = {"role": role, "code": exc.code, "detail": exc.detail}
                if hasattr(exc, "result"):
                    payload["original_result"] = exc.result.model_dump(mode="json")
                if hasattr(exc, "raw_text"):
                    payload["raw_text"] = exc.raw_text
                emit("REPLY_REJECTED", payload, proposal)
            except TimeoutError:
                failure = failure or "AGENT_TIMEOUT"
                emit("AGENT_FAILED", {"role": role, "code": "AGENT_TIMEOUT"}, proposal)
            except BaseException as exc:
                if not isinstance(exc, (Exception, asyncio.CancelledError)):
                    raise
                failure = failure or "AGENT_ERROR"
                emit("AGENT_FAILED", {"role": role, "code": "AGENT_ERROR", "exception_type": type(exc).__name__}, proposal)
        for scope in scopes.values():
            scope.active = False
        if pending:
            pending_code = "PEER_CANCELLED" if failure else "AGENT_TIMEOUT"
            for role, task in tasks.items():
                if task in pending:
                    emit("AGENT_FAILED", {"role": role, "code": pending_code}, proposal)
            failure = failure or "AGENT_TIMEOUT"
        for task in pending:
            task.cancel()
            task.add_done_callback(_discard_task)
            emit("LATE_REPLY_DISCARDED", {"reason": "Request closed; pending response cannot vote"}, proposal)
        if pending or failure:
            return fallback(failure or "AGENT_TIMEOUT")
        rounds += 1
        if all(r.result.decision.verdict == "ACCEPT" for r in replies):
            try:
                final = recheck(current)
                if globally_valid(final):
                    return finish("CONSENSUS", "UNANIMOUS_ACCEPT", selected=current,
                                  final=final, acceptances=replies, proposal=proposal)
            except TimeoutError:
                return fallback("FINAL_VALIDATION_BUDGET_EXHAUSTED")
            except Exception:
                return fallback("EVALUATOR_ERROR")
            return fallback("FINAL_VALIDATION_FAILED")
        if round_index == 2:
            return fallback("ROUND_LIMIT")
        pool = {current.plan_id}
        for reply in replies:
            if reply.result.decision.verdict == "COUNTER":
                pool.update(reply.result.decision.ranked_alternative_ids)
        candidates = [p for p in s.plans if p.plan_id in pool and globally_valid(reports[p.plan_id])]
        if not candidates:
            return fallback("NO_ELIGIBLE_COUNTER")
        selected = min(candidates, key=lambda p: rank(p, reports[p.plan_id]))
        if plan_hash(selected) in visited:
            return fallback("REPEATED_PROPOSAL")
        emit("PROPOSAL_SELECTED", {"pool": sorted(pool), "selected_plan_id": selected.plan_id,
                                   "rank": list(rank(selected, reports[selected.plan_id]))}, proposal)
        previous = [PublicMessage(role=r.role, proposal_id=r.proposal_id, plan_hash=r.current_plan_hash,
                                  decision=r.result.decision) for r in replies]
        current = selected
    return fallback("ROUND_LIMIT")
