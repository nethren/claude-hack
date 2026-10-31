# Decisions, assumptions and open questions

Recorded 2026-10-31, Asia/Singapore. A proposal is not an adopted implementation,
and a data check is not evidence that the application works.

## Confirmed context and documentation decisions

| ID | Status | Decision / evidence |
|---|---|---|
| DEC-01 | User-confirmed | Four builders; all can use Python/web apps; the user has work experience with multi-agent orchestration and another teammate has school ML experience. |
| DEC-02 | User-confirmed | Evaluate/build within a six-hour window. Exact submission deadline is not supplied. |
| DEC-03 | Working focus | Challenge #2 is the documentation/architecture focus, based on the user's preference, supplied screenshot and follow-up requests. #4 remains reference only. |
| DEC-04 | User-requested | Keep requirements, rubric and datasets in Markdown and require their use in brainstorming and architecture decisions. |
| DEC-05 | User-confirmed | Save under the existing CLAUDE HACK project folder; preserve the separate PROJECTS control repository. |
| DEC-06 | User-requested; private default | Create a GitHub repository and provide its link. Use private visibility; collaborator invitations/visibility changes are separate actions. |
| DEC-07 | Inspected | All three supplied CSV files are included unchanged and profiled; file hashes identify the exact snapshot. |
| DEC-08 | Adopted documentation guardrail | Source requirements and inspected facts take precedence over design suggestions; decisions require C2/JR/data alignment. |

## Proposed designs, not final implementation commitments

| ID | Proposal | Reason / next check |
|---|---|---|
| PROP-01 | Deterministic coordinator plus independent ATC/pilot/ground agents | C2-01, C2-03 to C2-08, C2-24; verify meaningful proposals/counteroffers rather than three wrappers around a prewritten answer. |
| PROP-02 | At most two complete proposal/evaluation rounds | C2-23, C2-25; organizer meaning of "turn" remains unconfirmed. |
| PROP-03 | One airport, three flights, two gates and one disruption | Six-hour starting scope; preserve every role objective in requirements coverage. |
| PROP-04 | Scenario overlays for missing operational state | Label every synthetic value and rule; define units and provenance; do not claim measured operations. |
| PROP-05 | Single state writer, immutable proposals/messages, deterministic hard checks | Skill context/fidelity guidance, C2-06, C2-07, C2-26. |
| PROP-06 | Deterministic and single-agent comparison baselines | JR-03, JR-05; same data/constraints/objectives. No results exist yet. |

## Open questions and constraints on claims

| ID | Question / gap | Effect on decisions |
|---|---|---|
| OPEN-01 | What exactly counts as a turn? | Show rounds and calls separately; do not assert literal compliance based only on the proposed interpretation. |
| OPEN-02 | Which numerical wake, fuel, safety and taxiway rules are used? | The brief gives responsibilities, not thresholds. Document simplified rules and limits; do not invent operational authority. |
| OPEN-03 | How will turbulence, passenger connections and crew shifts be represented? | No matching fields in supplied CSVs; retain as explicit coverage gaps until modelled. |
| OPEN-04 | Which preferences are negotiable and which limits are hard? | Code-owned hard constraints cannot be outvoted; weights and priorities need documentation. |
| OPEN-05 | What preprocessing produced the flight file and why is October absent? | Every row qualifies and none is cancelled/diverted; unknown selection history prevents broad prevalence/generalization claims. |
| OPEN-06 | What are the local-time zones and overnight dates for flight clock fields? | CSV has local HHMM-style values but no explicit timezone/UTC offset; do not subtract origin/destination clocks naively. |
| OPEN-07 | Which model/provider/framework and API budget are available? | Not selected or tested. User experience does not prove provider availability or runtime latency. |
| OPEN-08 | What is the submission procedure and deadline? | JR-06 requires valid submission timing and a three-minute presentation; details are not in the supplied material. |

## Entry template for later decisions

```text
Decision ID / date / status:
Proposal and alternatives:
Requirement IDs (C2):
Rubric IDs (JR):
Inspected data fields and units:
Missing/derived/simulated inputs and provenance:
Agent context, tools and message/state effects:
Deterministic checks, convergence and fallback:
Six-hour cost/trade-off:
Validation evidence or planned check:
Remaining uncertainty:
```
