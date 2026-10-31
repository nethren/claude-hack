"""Coordinator output/configuration; agent wire contracts stay unchanged."""
from dataclasses import dataclass
from typing import Literal

from pydantic import Field

from contracts.models import AgentReply, DomainReport, Plan, Usage, Wire


@dataclass(frozen=True)
class Budgets:
    # Raised from 15/35/40 (DEC-21): live Pilot calls take 11-14 s and two rounds
    # of three parallel calls plus token counting did not fit 15 s per call.
    call_s: float = 25
    negotiation_s: float = 60
    whole_run_s: float = 70
    output_tokens: int = 1600
    input_bytes: int = 64000  # Conservative UTF-8 token upper bound, not chars/4.
    # Raised from 8,000 (DEC-19): measured live prompts on the 3-plan fixture are
    # 8.9k-12k tokens in round 1 and up to ~14.7k in round 2, mostly hash-bearing
    # check IDs that must be passed through verbatim.
    input_tokens: int = 16000

    def __post_init__(self):
        if not (0 < self.call_s <= 25 and
                0 < self.negotiation_s < self.whole_run_s <= 70):
            raise ValueError("Require call <= 25s and 0 < negotiation < whole run <= 70s")
        if not (0 < self.output_tokens <= 1600 and
                0 < self.input_tokens <= 16000 and self.input_bytes > 0):
            raise ValueError("Invalid context/output budget")


class RunResult(Wire):
    protocol_version: Literal["1.0"] = "1.0"
    run_id: str
    scenario_id: str | None = None
    scenario_version: int | None = None
    scenario_hash: str | None = None
    outcome: Literal["CONSENSUS", "FALLBACK", "ESCALATED", "INPUT_ERROR"]
    reason_code: str
    trigger_code: str | None = None
    proposal_id: str | None = None
    selected_plan_id: str | None = None
    selected_plan_hash: str | None = None
    selected_plan: Plan | None = None
    final_reports: list[DomainReport] = Field(default_factory=list)
    acceptances: list[AgentReply] = Field(default_factory=list)
    metrics: dict[str, int] | None = None
    rounds_completed: int = 0
    model_calls_attempted: int = 0
    model_calls_completed: int = 0
    agent_invocations: int = 0
    retries: Literal[0] = 0
    usage: list[Usage] = Field(default_factory=list)
    elapsed_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
    event_log_ref: str
    candidate_reports: dict[str, list[DomainReport]] = Field(default_factory=dict)
    selection_policy_version: str = "lexicographic-1.0"
