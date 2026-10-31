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
| DEC-09 | User-requested | Author and push an architecture document so three teammates can build domain agents independently and integrate through a shared interface. |
| DEC-10 | Backend implemented; live evaluation pending | [Protocol 1.0](ai-orchestration-architecture.md): unchanged agent wire types, independent role adapters/evaluators and deterministic bounded coordinator. Offline integration and mocked HTTP verified; live generations/frontend pending. |
| DEC-11 | User-authorized implementation | Pull teammates' code and implement/test the backend on branch `coordinator` before frontend work. Merge Pilot 834f8da and Ground 690a957, preserving their history/interfaces. |
| DEC-12 | User-authorized compatible ATC | No ATC branch was available; user requested a compatible reference implementation. Keep ownership/provenance visible so the teammate can replace/review it through the same interface. |
| DEC-13 | Adopted integration setting | Match the merged adapters' 1,600 output-token cap; retain two rounds/six generation attempts, zero retries and existing deadlines. Live token counting enforces the complete 8,000-token prompt cap. |

## Proposed designs, not final implementation commitments

| ID | Proposal | Reason / next check |
|---|---|---|
| PROP-01 | Deterministic coordinator plus independent ATC/pilot/ground agents | C2-01, C2-03 to C2-08, C2-24; verify meaningful proposals/counteroffers rather than three wrappers around a prewritten answer. |
| PROP-02 | At most two complete proposal/evaluation rounds | C2-23, C2-25; organizer meaning of "turn" remains unconfirmed. |
| PROP-03 | One airport, three flights, two gates and one disruption | Six-hour starting scope; preserve every role objective in requirements coverage. |
| PROP-04 | Scenario overlays for missing operational state | Label every synthetic value and rule; define units and provenance; do not claim measured operations. |
| PROP-05 | Single state writer, immutable proposals/messages, deterministic hard checks | Skill context/fidelity guidance, C2-06, C2-07, C2-26. |
| PROP-06 | Deterministic and single-agent comparison baselines | JR-03, JR-05; same data/constraints/objectives. No results exist yet. |
| PROP-07 | Live disruption test with a deterministic "why this plan / why not another" view | Coordinator/UI enhancement; preserve the existing agent interface. Invalidate old scenario approvals, rerun checks and start a new bounded negotiation. Show actual evidence and fallback/escalation; do not claim this is implemented. |

PROP-01/PROP-05 now have concrete interface and state-machine definitions in
the architecture. PROP-02 remains an unconfirmed interpretation of "turn";
two rounds and at most six calls are explicit engineering limits. PROP-04 has
one labelled synthetic operational fixture with a real row-76 source envelope.
At the original design snapshot no application result existed. The backend
implementation update below supersedes that state; live results remain pending.

### Protocol 1.0 implementation defaults

- Reference doc: [AI orchestration architecture](ai-orchestration-architecture.md).
- C2/JR/data alignment, role ownership and test evidence are mapped in its section 12.
- Context is isolated by role; all three receive identical required source-row
  parameters, plus only their own domain overlays/reports and validated messages.
- Deterministic checks retain veto power. The fallback ordering is a documented
  lexicographic policy; its preference trade-offs are not an aviation standard.
- Two rounds, six calls maximum, no automatic retries, 15-second call timeout,
  35-second negotiation budget and 40-second whole-run budget are unbenchmarked
  defaults. Model/provider/budget availability and organizer turn wording remain open.
- One shared module owner handles schema changes; the four-person build split
  and first-hour integration checkpoint are defined in the architecture.

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
| OPEN-09 | Resolved in coordinator backend | Gateway and architecture now use 1,600 output tokens to match merged adapters. No agent-wire/interface change. Real-model budget/latency testing remains pending under OPEN-07. |
| OPEN-10 | Is the candidate catalog broad enough for the scenario? | The 12-plan cap is an unbenchmarked engineering limit. Wider deterministic search with a bounded LLM shortlist has been discussed but is not adopted in the published v1 contract. |

## Historical coordinator readiness and proposed demonstration

Snapshot checked 2026-10-31. Shared main remains the documentation baseline at
17af294. Unmerged remote branches include Pilot at 834f8da and Ground at 690a957.
Their `contracts/models.py` blobs match, and both expose the expected independent
adapter/evaluator interfaces. An ATC implementation was not visible on the shared
remote branches at this check; unpublished teammate work is unknown. This is
enough to begin coordinator implementation, not proof of end-to-end readiness.

PROP-07 would present a completed recommendation, inject a labelled simulated
crew disruption, mark the previous recommendation obsolete, and start a new run
under an incremented scenario version/hash. The agent models, methods and message
shapes remain unchanged. Each new run keeps its own two-round/six-call budget;
the demo must also report cumulative calls across runs. Do not reset counters to
hide additional negotiation or reuse previous acceptances.

Concrete fixture demonstration: preserve the actual row-76 source envelope
(`WEATHER_DELAY=35`, `LATE_AIRCRAFT_DELAY=40`) and all raw data. Change only
Ground crew C2's simulated availability window to start at scenario minute 20.
P1 needs F2 service at [16,24), so its GROUND_CREW check fails. P2 starts that
service at [20,28), so it remains acceptable to the Ground evaluator. The Pilot
evaluator also continues to pass P2. The original scenario hash changes, making
old votes inapplicable. All operational times/fuel/gates/crew values are simulated.

Evidence collected during this assessment: the published Ground/Pilot evaluators
were loaded into an isolated temporary snapshot and exercised on the original
fixture and the changed crew window. Original P1 passed Ground; modified P1
failed GROUND_CREW for F2; modified P2 passed Ground and Pilot. No coordinator,
ATC runtime check, UI, live model call or complete negotiation was tested.

Implementation placement: scenario/version ownership, stale-result rejection,
revalidation, the new run and event persistence belong to the coordinator. The
UI reads original rule results and policy comparisons for its explanation. It
does not add an explanation LLM or generate a fictional conversation. Display
the first failed hard constraint or first decisive ranking criterion, such as
"P1 needs crew at minute 16; availability begins at minute 20."

This supports C2-04 to C2-08, C2-17, C2-25/C2-26 and JR-02 to JR-05. It uses
existing shared-row/context isolation and validation paths; only scenario inputs
change. A candidate that still passes all domains can enter a fresh negotiation;
if none validates, show explicit escalation. Do not promise recovery outside the
catalog or label a fallback result consensus.

Timebox estimate: 45-90 additional minutes after a working coordinator and basic
UI, not a measured build duration. If core integration is late, retain only the
deterministic "why this plan / why not another" view using existing reports.
Acceptance evidence: changed version/hash; no stale acceptance reused; P1's
actual failure shown; correctly labelled new consensus/fallback/escalation;
modelled delay/connections/overtime and measured rerun time/calls displayed.
Compare to reusing the old recommendation and to deterministic fallback under
the same changed scenario; do not claim unmeasured real-world benefit.

Dynamic rechecking is established assurance practice, not a claim of novel core
technology; see [NASA's dynamic-assurance research](https://ntrs.nasa.gov/citations/20230008541).
The proposed differentiator is an interactive, traceable demonstration of how
the system handles a changing disruption. This remains a proposal pending build
scope selection; it has not changed the published agent contract.

## Coordinator implementation update

Implemented under the user's requested `coordinator` branch, with the existing
agent protocol kept intact. Three role adapters call a scoped gateway independently;
deterministic Python owns source verification, semantic preflight, complete
reports, candidate selection, original message routing, consensus, fallback,
scenario revisions and evidence. The application returns recommendations only.
No frontend was added. See [backend handoff](backend.md) for API/run instructions.

Supports C2-01 through C2-26 within the simplified scenario model; live negotiation
quality and literal organizer turn compliance remain unproven. JR-02 to JR-04
receive concrete backend evidence; JR-01 stakeholder realism, JR-05 actual benefit,
and JR-06 submission/presentation still require separate evidence.

Inputs: original CSV row 76 and all 31 raw fields, with AIRLINE/origin/destination
lookup joins; WEATHER_DELAY=35 and LATE_AIRCRAFT_DELAY=40 minutes satisfy the
strict OR. Integer simulation minutes, kg and kg/min, ordinal turbulence,
passenger counts, gates and crews are labelled overlays. No inferred UTC slots,
live telemetry or measured operational fuel values are claimed.

Validation: actual Pilot/Ground code, compatible reference ATC, full two-round
coordinator, CLI and local API run with scripted replies. HTTP tests exercise
the real Anthropic adapter against a mocked provider, including token counts,
usage for malformed replies and zero retries. Boundary/stale/mutation/deadline/
failure tests cover consensus/fallback/escalation distinction. The complete test
suite and reference validator are the reproducible evidence, not live AI results.

The backend portion of PROP-07 now exists: changed version/hash starts fresh
votes; changed crew availability makes P1 fail and P2 eligible; the comparison
endpoint exposes actual failed checks or first differing ranking metric. Reusing
an existing version with altered data is rejected before model calls. The
interactive UI remains unimplemented. Calls across separate runs remain separate
and must be summed in any demonstration.

Trade-off: preserve all teammate interfaces, one process and the existing finite
catalog to finish the backend first. Avoid a framework migration, new planner,
new supervisor LLM or frontend work. The cap of 12 catalog plans remains a scope
limit rather than completeness evidence. Live credentials/model were unavailable;
the live endpoint must still be exercised and timed before the hackathon demo.
The deterministic fallback picks the same P1 as the offline negotiation under
the default scenario; no superiority over the baseline is claimed.

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
