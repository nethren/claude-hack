"""Coordinator validates independently of any teammate adapter's own checks."""
from contracts.models import AgentProtocolError, AgentReply, AgentRequest, ModelDecision
from runtime.catalog import hard_pass


def validate_decision(decision: ModelDecision, request: AgentRequest):
    def fail(code, detail):
        raise AgentProtocolError(code, request.role, request.request_id, detail)
    by_id = {v.plan.plan_id: v for v in request.candidates}
    current = by_id[request.current_plan_id]
    ranked = decision.ranked_alternative_ids
    if len(set(ranked)) != len(ranked):
        fail("MODEL_JSON_INVALID", "Duplicate ranked alternatives")
    if any(pid not in by_id for pid in ranked):
        fail("UNKNOWN_CANDIDATE", "Alternative is not in this catalog")
    if decision.verdict in ("ACCEPT", "REJECT") and ranked:
        fail("MODEL_JSON_INVALID", "ACCEPT/REJECT require empty alternatives")
    if decision.verdict == "ACCEPT" and not hard_pass(current.report):
        fail("INVALID_ACCEPT", "Current plan fails own hard checks")
    if decision.verdict == "COUNTER":
        if not ranked:
            fail("MODEL_JSON_INVALID", "COUNTER requires alternatives")
        for pid in ranked:
            if by_id[pid].plan_hash == current.plan_hash or not hard_pass(by_id[pid].report):
                fail("INVALID_COUNTER", "Alternative must differ and pass own hard checks")
    views = (request.candidates if decision.verdict == "REJECT" else
             [current, *(by_id[pid] for pid in ranked)])
    check_ids = {c.check_id for view in views for c in view.report.checks}
    if any(cid not in check_ids for cid in decision.cited_check_ids):
        fail("UNKNOWN_CHECK", "Citation is not an actual own-domain check in scope")


def validate_reply(reply: AgentReply, request: AgentRequest):
    reply = AgentReply.model_validate_json(reply.model_dump_json())
    for field in ("protocol_version", "run_id", "request_id", "role", "scenario_version",
                  "scenario_hash", "round_index", "proposal_id", "current_plan_id", "current_plan_hash"):
        if getattr(reply, field) != getattr(request, field):
            raise AgentProtocolError("STALE_REPLY", request.role, request.request_id,
                                     f"Reply {field} differs from the active request")
    validate_decision(reply.result.decision, request)
    return reply
