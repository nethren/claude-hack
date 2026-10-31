"""Shared protocol 1.0 wire types.

TEMPORARY COPY for the ATC branch. Person D owns this module; the content is
copied verbatim from docs/ai-orchestration-architecture.md section 5 so the ATC
evaluator and adapter can be built before D publishes it. Replace this file with
D's published version when integrating; do not edit it here.
"""
from __future__ import annotations

import hashlib
import json

from typing import Annotated, Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field

Role = Literal["atc", "pilot", "ground"]
Minute = Annotated[int, Field(ge=0)]
NonNegative = Annotated[int, Field(ge=0)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

class Wire(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class Interval(Wire):
    start_min: Minute
    end_min: Minute

class SourceRow(Wire):
    source_id: str
    dataset_sha256: Digest
    csv_row_number: Annotated[int, Field(ge=2)]
    raw: dict[str, str]  # Exactly the 31 committed flights.csv headers.

class Flight(Wire):
    flight_id: str
    identity_origin: Literal["source_csv", "simulated"]
    source_id: str | None
    scheduled_landing_min: Minute  # Simulated target in v1, not raw gate clock.

class Assignment(Wire):
    flight_id: str
    landing_min: Minute
    taxi_route_id: str
    gate_id: str
    gate_out_min: Minute

class Plan(Wire):
    plan_id: str
    assignments: list[Assignment]

class Route(Wire):
    route_id: str
    taxi_in_min: Annotated[int, Field(ge=1)]
    blocked_windows: list[Interval]

class ATCState(Wire):
    role: Literal["atc"]
    runway_open_windows: list[Interval]
    runway_occupancy_min: Annotated[int, Field(ge=1)]
    wake_class_by_flight: dict[str, str]
    separation_min: dict[str, dict[str, Minute]]  # Leader class -> follower class.
    routes: list[Route]

class PilotLimits(Wire):
    flight_id: str
    earliest_landing_min: Minute
    fuel_at_earliest_landing_kg: NonNegative
    reserve_kg: NonNegative
    holding_burn_kg_per_min: Annotated[int, Field(ge=1)]
    max_turbulence_units: Annotated[int, Field(ge=0, le=3)]
    turbulence_by_landing_min: dict[str, Annotated[int, Field(ge=0, le=3)]]
    connecting_passengers: NonNegative
    connection_deadline_min: Minute | None
    transfer_min: Minute | None

class PilotState(Wire):
    role: Literal["pilot"]
    limits: list[PilotLimits]

class Gate(Wire):
    gate_id: str
    compatible_flight_ids: list[str]
    occupied_windows: list[Interval]

class Crew(Wire):
    crew_id: str
    available_windows: list[Interval]
    shift_end_min: Minute

class GroundService(Wire):
    flight_id: str
    crew_id: str
    min_turnaround_min: Annotated[int, Field(ge=1)]

class GroundState(Wire):
    role: Literal["ground"]
    gates: list[Gate]
    crews: list[Crew]
    services: list[GroundService]

DomainState = Annotated[
    ATCState | PilotState | GroundState, Field(discriminator="role")
]

class Options(Wire):
    landing_min_by_flight: dict[str, list[Minute]]
    gate_out_min_by_flight: dict[str, list[Minute]]
    taxi_route_ids: list[str]
    gate_ids: list[str]

class SharedInput(Wire):
    airport_iata: str
    horizon_end_min: Annotated[int, Field(ge=1)]
    source_rows: Annotated[list[SourceRow], Field(min_length=1, max_length=3)]
    flights: Annotated[list[Flight], Field(min_length=1, max_length=3)]
    options: Options
    taxi_in_min_by_route: dict[str, Annotated[int, Field(ge=1)]]
    disruption_note: Annotated[str, Field(max_length=1000)]
    simulated_fields: list[str]  # Explicit field prefixes, e.g. "pilot".

class ScenarioInput(Wire):
    protocol_version: Literal["1.0"]
    scenario_id: str
    scenario_version: Annotated[int, Field(ge=1)]
    initial_plan_id: str
    shared: SharedInput
    atc: ATCState
    pilot: PilotState
    ground: GroundState
    plans: Annotated[list[Plan], Field(min_length=1, max_length=12)]

class Check(Wire):
    check_id: str
    rule_id: str
    flight_ids: list[str]
    severity: Literal["HARD", "SOFT"]
    status: Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
    observed: str
    required: str
    evidence_refs: list[str]

class DomainReport(Wire):
    role: Role
    scenario_hash: Digest
    plan_hash: Digest
    checks: list[Check]
    metrics: dict[str, NonNegative]  # Only the role's registered metric keys.

class CandidateView(Wire):
    plan: Plan
    plan_hash: Digest
    report: DomainReport  # Only this role's report; never another role's state.

class ModelDecision(Wire):
    verdict: Literal["ACCEPT", "COUNTER", "REJECT"]
    ranked_alternative_ids: Annotated[list[str], Field(max_length=12)]
    cited_check_ids: list[str]
    reason: Annotated[str, Field(min_length=1, max_length=1000)]
    uncertainty: Annotated[str, Field(max_length=500)]

class PublicMessage(Wire):
    role: Role
    proposal_id: str
    plan_hash: Digest
    decision: ModelDecision  # Preserved original structured decision.

class AgentRequest(Wire):
    protocol_version: Literal["1.0"]
    run_id: str
    request_id: str
    role: Role
    scenario_id: str
    scenario_version: Annotated[int, Field(ge=1)]
    scenario_hash: Digest
    round_index: Annotated[int, Field(ge=1, le=2)]
    proposal_id: str
    current_plan_id: str
    current_plan_hash: Digest
    call_timeout_ms: Annotated[int, Field(ge=1, le=15000)]
    shared: SharedInput
    domain: DomainState
    candidates: Annotated[list[CandidateView], Field(min_length=1, max_length=12)]
    previous_messages: list[PublicMessage]  # Round 2: validated round-1 originals.

class Usage(Wire):
    provider: str
    model: str
    input_tokens: NonNegative | None
    output_tokens: NonNegative | None
    model_calls: Annotated[int, Field(ge=0, le=1)]
    elapsed_ms: NonNegative

class ModelResult(Wire):
    decision: ModelDecision
    raw_text: str
    usage: Usage

class AgentReply(Wire):
    protocol_version: Literal["1.0"]
    run_id: str
    request_id: str
    role: Role
    scenario_version: Annotated[int, Field(ge=1)]
    scenario_hash: Digest
    round_index: Annotated[int, Field(ge=1, le=2)]
    proposal_id: str
    current_plan_id: str
    current_plan_hash: Digest
    result: ModelResult

class ModelGateway(Protocol):
    async def complete(
        self, *, role: Role, system_prompt: str, user_json: str,
        timeout_s: float, max_output_tokens: int
    ) -> ModelResult: ...

class DomainAgent(Protocol):
    async def decide(
        self, request: AgentRequest, *, model: ModelGateway
    ) -> AgentReply: ...

def plan_hash(plan: Plan) -> str:
    ids = [a.flight_id for a in plan.assignments]
    if len(ids) != len(set(ids)):
        raise ValueError(f"plan {plan.plan_id} has duplicate flight assignments")
    body = {"assignments": [
        a.model_dump(mode="json")
        for a in sorted(plan.assignments, key=lambda a: a.flight_id)
    ]}
    wire = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()

def scenario_hash(scenario: ScenarioInput) -> str:
    wire = json.dumps(
        scenario.model_dump(mode="json"),
        sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


class AgentProtocolError(Exception):
    """Section 8: one typed error for protocol violations. Owned by D."""

    def __init__(self, code: str, role: Role, request_id: str, detail: str) -> None:
        super().__init__(f"{code} [{role}/{request_id}]: {detail}")
        self.code = code
        self.role = role
        self.request_id = request_id
        self.detail = detail
