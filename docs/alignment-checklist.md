# Requirement, data and evidence alignment

Read this with [requirements](challenge-2-requirements.md),
[rubric](judging-rubric.md), [dataset contract](datasets.md) and
[multi-agent guardrails](multi-agent-design-constraints.md) before making a
feature or architecture decision. Distinguish implemented backend checks from
live-model, operational and presentation evidence.

## Current state

Source conversion and full-file inspection are complete. The `coordinator`
branch now implements the backend with the merged Pilot/Ground agents and a
compatible reference ATC agent. Tests exercise actual adapters/evaluators,
scripted model replies, mocked provider HTTP and the local API. Real LLM
generation/timing and frontend/human review UX remain pending. See the
[backend handoff](backend.md) and executable tests for the evidence boundaries.
Gate/fuel/crew/turbulence/connection/separation inputs remain absent from the
CSVs; the fixture supplies labelled simulated state, not observed operational data.

The [frontend review draft](frontend-review.md) now renders the real DFW geometry
with explicitly illustrative routes/positions, agent decision/check disclosures,
alternative comparisons and distinct failure outcomes. Recorded scenarios use
scripted backend decisions; connected requests wait for terminal results rather
than faking streaming progress. Frontend review approval and live model evaluation
remain separate from backend/source verification.

| Requirement IDs | Data / design dependency | Required evidence | Current state |
|---|---|---|---|
| C2-01, C2-24 | Separate contexts, calls and tools | Three actual adapters and role-specific reports/contexts | Offline/mocked-provider integration verified; live LLM calls pending |
| C2-02 | Autonomous bounded negotiation | Successful run requires no user assistance; recommendation only | Backend verified offline; human review UX pending |
| C2-03 | Validated message schema and source references | Strict parsing, unknown IDs/checks and malformed replies fail visibly | Backend tests pass |
| C2-04, C2-06 | Cross-domain deterministic rule checks | Actual complete, hash-bound reports for all plans and final selection | Backend tests pass |
| C2-05, C2-07 | Versioned proposals and evidence log | Fresh round-two votes; stale identity/mutation rejected; original messages/log exported | Backend tests pass; live consent quality unmeasured |
| C2-08 | Deterministic fallback, no-validated-plan outcome | Outage/deadline/disagreement leads to checked fallback or explicit escalation | Backend tests pass |
| C2-09 | Synthetic wake classes/separation policy | Too-close sequence and equality boundary exercised | Reference ATC tests pass; no real separation policy claim |
| C2-10 | Synthetic blocked-route windows | Blockage and touching interval boundary exercised | Reference ATC tests pass; no collision-dynamics model |
| C2-11 | Simulated arrival demand and fixed horizon | Throughput reported and used in policy | Arrival proxy implemented; actual sector benefit unmeasured |
| C2-12, C2-13 | Synthetic reserve/holding/earliest/safety inputs | Reserve equality and below-limit rejection; hard limits stay outside model control | Pilot tests pass; holding-only safety subset |
| C2-14 | Synthetic exposure/cap by flight and slot | Cap/missing-exposure behavior and metrics exercised | Pilot tests pass; live comfort reasoning unmeasured |
| C2-15 | Synthetic passenger counts/transfer/deadline | Explicit zero-passenger N/A, deadline boundary and missed count | Pilot tests pass; actual itineraries absent |
| C2-16 | Synthetic gate compatibility/occupancy | Overlap/incompatibility rejected; fixed-horizon gate occupancy reported | Ground tests pass; full capacity benefit unmeasured |
| C2-17 | Synthetic crew shifts/availability | Overtime formula and crew-delay rerun | Ground and integration tests pass |
| C2-18 | Synthetic minimum service duration | Infeasible turn rejected; resulting delay reported | Ground tests pass |
| C2-19, C2-20 | DS-03; strict WEATHER_DELAY > 15 OR LATE_AIRCRAFT_DELAY > 20 | Committed source hash/row 76 checked; strict comparison boundaries tested | Backend verified |
| C2-21 | Same complete traceable row envelope | Every actual adapter receives identical raw fields in integration test | Offline/mocked-provider verified |
| C2-22 | Complete arrival/gate plans | P0 changes to P1, changed crew scenario selects P2 | Offline negotiation verified; live result pending |
| C2-23, C2-25 | Round/call/retry and elapsed budgets | Two rounds, six attempted generations max, no retries, bounded exits | Backend tested; organizer turn wording unresolved; live timing pending |
| C2-26 | Independent reply checks plus fresh final validation | Invalid acceptance and changed final checks cannot establish consensus | Backend tests pass within declared model |

## Judging evidence matrix

| Criterion | Evidence to collect | Current state |
|---|---|---|
| JR-01 | Named user, disruption workflow, present process and credible pain | Narrative not yet tested with a user |
| JR-02 | End-to-end inputs/outputs, appropriate LLM/code split and mutated scenarios | Backend passes offline/mocked HTTP tests; live run pending |
| JR-03 | Reproducible suite, baseline and visible failure | Default, mutated and failure tests pass; fallback chooses same P1; no multi-agent superiority/live success claim |
| JR-04 | Provenance, rule IDs, original messages, uncertainty and human review | Runtime evidence/export implemented and tested; frontend/reviewer workflow pending |
| JR-05 | Same-constraint comparison; measured vs estimated benefits | Modelled metrics verified; no actual operational savings validated |
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
