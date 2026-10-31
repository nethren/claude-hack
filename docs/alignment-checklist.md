# Requirement, data and evidence alignment

Read this with [requirements](challenge-2-requirements.md),
[rubric](judging-rubric.md), [dataset contract](datasets.md) and
[multi-agent guardrails](multi-agent-design-constraints.md) before making a
feature or architecture decision. This is a planned evidence matrix, not a list
of completed application tests.

## Current state

Source conversion and full-file data inspection are complete. All application
requirements remain **not implemented / not tested**. Gate/fuel/crew/turbulence/
connection/separation inputs remain **missing from supplied CSVs**. Flight-row
selection is **data-ready**, but passing a row through running agents is untested.
The [protocol 1.0 architecture](ai-orchestration-architecture.md) now defines
teammate interfaces, role tools, budgets, failure handling and acceptance checks.
Its [integration fixture](examples/coordination-scenario-v1.json) supplies labelled
simulated operational state; it does not turn those inputs into observed data
or establish that application requirements have been implemented.

| Requirement IDs | Data / design dependency | Required evidence | Current state |
|---|---|---|---|
| C2-01, C2-24 | Separate contexts, calls and tools | Trace shows three independent invocations and domain-specific decisions | Not implemented |
| C2-02 | Autonomous bounded negotiation | No user assistance during a successful negotiation; final recommendation review remains possible | Not implemented |
| C2-03 | Validated message schema and source references | Original structured messages parse; malformed ones fail visibly | Not implemented |
| C2-04, C2-06 | Cross-domain deterministic rule checks | Actual check records for a proposal, not self-reported LLM safety | Not implemented |
| C2-05, C2-07 | Versioned proposals and immutable event log | All accept the same proposal/scenario; stale votes cannot establish agreement | Not implemented |
| C2-08 | Deterministic fallback, no-feasible-plan outcome | LLM unavailable or deadline exhausted; checked fallback or explicit escalation | Not implemented |
| C2-09 | Missing wake category and separation policy | Too-close sequence rejected under documented scenario rule | Inputs missing |
| C2-10 | Missing taxiway state | Route using a blocked segment rejected | Inputs missing |
| C2-11 | Modelled demand, available slots and time horizon | Throughput measure and trade-off under stated assumptions | Inputs missing |
| C2-12, C2-13 | Missing fuel reserves, holding budget and safety limits | Fuel/holding boundary rejected; safety margins cannot be modified by agents | Inputs missing |
| C2-14 | Missing turbulence/route-exposure information | Different exposure produces a reasoned preference or hard-limit decision | Inputs missing |
| C2-15 | Missing passenger connections and transfer windows | Connection impact compared across candidate plans | Inputs missing |
| C2-16 | Missing gate occupancy and compatibility | Gate-overlap/incompatible allocation rejected; utilization reported | Inputs missing |
| C2-17 | Missing crew shifts and required crew work | Overtime trade-off visible and threshold behaviour checked | Inputs missing |
| C2-18 | Missing turnaround state/minimum duration | Infeasible turnaround rejected; resulting delay measured | Inputs missing |
| C2-19, C2-20 | DS-03; strict WEATHER_DELAY > 15 OR LATE_AIRCRAFT_DELAY > 20 | Source hash, selected raw row number and numerical predicate result | Data inspected; application untested |
| C2-21 | Selected source-row envelope for all agents | Trace links every agent input to the same row and source hash | Not implemented |
| C2-22 | Arrival/gate/flight-plan decision fields and applicable rules | At least one negotiated adjustment changes the proposal | Not implemented |
| C2-23, C2-25 | Turn interpretation, bounded rounds, deadlines and retry budget | Round, call, retry and wall-clock counts; repetition/limit exit | Not implemented; wording unresolved |
| C2-26 | Code-owned hard constraints; final validation | Agents agreeing on an invalid plan still cannot finalize it | Not implemented |

## Judging evidence matrix

| Criterion | Evidence to collect | Current state |
|---|---|---|
| JR-01 | Named user, disruption workflow, present process and credible pain | Narrative not yet tested with a user |
| JR-02 | End-to-end inputs/outputs, appropriate LLM/code split and unseen scenarios | No build |
| JR-03 | Reproducible scenario suite, baseline, measured results and visible failure | No application results |
| JR-04 | Raw-row provenance, applied rule IDs, original messages, uncertainty and human review | Sources documented; runtime absent |
| JR-05 | Same-constraint baseline comparison; measured modelled benefits separated from estimates | No benefit claims validated |
| JR-06 | Valid submission timestamp and rehearsed presentation within three minutes | Not submitted/rehearsed |

## Minimum proposed evaluation cases

1. Feasible disruption: independent objections/counteroffers produce a valid change.
2. Fuel/holding boundary: no accepted plan exceeds the configured allowance.
3. Wake separation and blocked taxiway: deterministic rejection remains effective.
4. Gate overlap and short turnaround: each affected rule is exercised.
5. Turbulence, connection and overtime trade-off: preferences visibly affect ranking.
6. All agents accept an invalid plan: final validator still rejects it.
7. Scenario/proposal changes: stale acceptances are invalidated.
8. Malformed message, unknown identifier or invented rule: rejected before propagation.
9. Timeout, repeated proposal and exhausted retry/round budget: bounded exit.
10. No feasible plan: explicit escalation; fallback never masquerades as consensus.

Recommended baselines: a deterministic scheduler and a single-agent approach on
the same scenarios, inputs, objectives and validator. A single-agent baseline is
evaluation only; it cannot replace the three-agent challenge entry. Report
feasible-plan rate, consensus/fallback/escalation rates, modelled delay and other
defined preference outcomes, wall time, calls, retries and tokens. Do not assume
multi-agent coordination will outperform the deterministic baseline.

## Decision checklist

- Cite relevant C2 and JR IDs.
- Name actual fields used and how missing operational inputs will be supplied.
- State provenance and distinguish observed, derived and simulated values.
- Identify the hard-check and failure behaviour affected.
- Explain context boundaries, message fidelity and state ownership.
- Describe the six-hour trade-off and planned acceptance evidence.
- Record the decision/status in [the log](decision-log.md).
