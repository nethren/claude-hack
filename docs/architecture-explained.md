# How Our AI Agent Architecture Works

Our system has **three AI agents and one Python coordinator**.

The AI agents evaluate plans and negotiate from different perspectives.
The coordinator manages the process using fixed rules.

This explains the protocol 1.0 design. The agents and application still need
to be implemented and tested.

## 1. The four components

| Component | Responsibility |
|---|---|
| ATC AI agent | Runway availability, wake separation, blocked taxiways and throughput |
| Pilot AI agent | Fuel reserves, safety, turbulence and passenger connections |
| Ground AI agent | Gates, turnaround time, crew availability and overtime |
| Python coordinator | Proposals, message routing, agreement checks, deadlines and fallback |

The coordinator is **regular Python code**, rather than a fourth LLM agent.
It does not need a prompt or an LLM call to run the workflow.

Everything runs in one Python application. Each AI agent has its own prompt,
context and module, so teammates can build their agents independently without
deploying three separate servers.

## 2. Each AI agent has two parts

**Deterministic checker:** Python code calculates whether its domain's
constraints pass and computes relevant metrics.

**LLM adapter:** The model reads those results, considers its priorities and
returns a structured JSON decision:

- **ACCEPT:** accept the current proposal.
- **COUNTER:** propose another candidate plan.
- **REJECT:** no candidate can be validated locally.

The model cannot change safety limits, invent operational facts or override
failed checks. Each agent receives the same required flight-row parameters,
plus its own domain state and check results.

## 3. How negotiation works

1. Load a real qualifying flight row and a labelled simulation overlay.
2. Prepare a catalog of up to 12 candidate plans.
3. Publish one current proposal to all three agents.
4. Run the agents independently, in parallel.
5. Collect their structured decisions and counteroffers.
6. If necessary, check the counteroffers and publish a revised proposal.
7. Run the second round and determine the final outcome.

Each plan specifies landing times, taxi routes, gates and gate-out times.

In round two, agents receive the original messages from round one. They still
receive only their own domain state and check results. The coordinator routes
messages without rewriting what another agent said.

## 4. What counts as agreement?

Consensus requires:

- All three agents accept the **same proposal version**.
- Every applicable hard constraint passes.
- The final Python validator checks the exact selected plan again.

Two agents agreeing cannot override a failed fuel or separation check.
Votes for an earlier proposal cannot approve a revised proposal.

For example, imagine two flights are two minutes apart while the simulation
requires a three-minute gap, and their gate bookings overlap. ATC identifies
the separation problem; Ground identifies the gate conflict. The agents can
counteroffer a different schedule and gate assignment. Pilot then checks that
the revised plan respects its own fuel and safety constraints.

That example illustrates the intended behaviour; it is not a measured result
from a running agent system.

## 5. What happens when negotiation fails?

The coordinator runs a **deterministic fallback**, without another model call.

It checks the candidate catalog and selects a valid plan using the documented
ranking policy. An invalid proposal, timeout or malformed model response must
never be silently converted into agreement.

Possible outcomes are:

- **CONSENSUS:** unanimous acceptance plus passing final checks.
- **FALLBACK:** a checked recommendation without unanimous agent agreement.
- **ESCALATED:** no candidate could be validated within the budget.
- **INPUT_ERROR:** the scenario or source data failed input validation.

Fallback is never presented as agent consensus. Escalation does not prove that
no feasible plan exists outside the small candidate catalog.

## 6. Data and simulation

All three agents receive the same complete source-row envelope, including its
source identifier and file hash.

The selected real row must satisfy:

```text
WEATHER_DELAY > 15 OR LATE_AIRCRAFT_DELAY > 20
```

The CSVs do not contain operational fuel, gates, crew shifts, turbulence or
passenger connections. Those inputs must be supplied separately and clearly
labelled as simulated.

Scheduling uses integer minutes from a simulation origin. Historical CSV clock
values are preserved as evidence, rather than treated as live airport state.
Historical weather-delay minutes do not represent remaining fuel or holding time.

## 7. Limits and traceability

The initial engineering limits are:

- Two negotiation rounds.
- At most six model calls: three agents times two rounds.
- No automatic model retries.
- Up to 15 seconds per call, shortened by the remaining negotiation budget.
- A 35-second negotiation budget and 40-second whole-run budget.

These are design defaults that still need runtime measurements. The brief's
phrase "under 3 turns" remains ambiguous. We display both round counts and
individual model-call counts instead of assuming they mean the same thing.

The log preserves proposals, original agent messages, check results, versions,
usage and final outcomes. A human reviews the resulting recommendation.
The prototype does not execute real airport operations.

## 8. Team split

- **Person A:** ATC checker and AI adapter.
- **Person B:** Pilot checker and AI adapter.
- **Person C:** Ground checker and AI adapter.
- **Person D:** Shared types, coordinator, model gateway, logging and interface.

Everyone imports the same shared contract. The integrator publishes that
contract first so the three agents can connect without incompatible interfaces.

The agents reason about their domain and exchange proposals. The coordinator
keeps the negotiation bounded, traceable and consistent with the declared rules.

## Full implementation contract

For shared Python types, evaluator formulas, fixtures and integration checks,
see the [AI orchestration architecture on GitHub](https://github.com/nethren/claude-hack/blob/main/docs/ai-orchestration-architecture.md).
