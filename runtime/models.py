"""Coordinator output/configuration; agent wire contracts stay unchanged."""
from dataclasses import dataclass
from typing import Literal

from pydantic import Field

from contracts.models import AgentReply, DomainReport, Plan, Usage, Wire


@dataclass(frozen=True)
class Budgets:
    call_s: float = 15
    negotiation_s: float = 35
    whole_run_s: float = 40
    output_tokens: int = 1600
    input_bytes: int = 32000  # Conservative UTF-8 token upper bound, not chars/4.
    input_tokens: int = 8000

    def __post_init__(self):
        if not (0 < self.call_s <= 15 and
                0 < self.negotiation_s < self.whole_run_s <= 40):
            raise ValueError("Require call <= 15s and 0 < negotiation < whole run <= 40s")
        if not (0 < self.output_tokens <= 1600 and
                0 < self.input_tokens <= 8000 and self.input_bytes > 0):
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
