# Frontend draft: airport surface and recovery coordination

User-approved stack: React + Vite; code-first interactive draft. Implementation
is isolated on `codex/frontend-draft` for review while teammate branches merge.
The backend and protocol 1.0 wire contracts are unchanged.

## Review outcome and UI structure

Groundline is a provisional product name for this draft. A real DFW surface map
occupies the main workspace. A lime aircraft/route selection, flight hover/focus
details, paused/scrubbable motion and a three-flight strip make the plan tangible.
The conditions strip shows only supplied historical disruption and simulated
runway/route/ground state. The right panel exposes independently invoked ATC,
Pilot and Ground decisions, stated reasons, check evidence and alternatives.
Consensus, fallback, escalation and input error have distinct labels.

The draft replays actual stored coordinator events using explicitly scripted
model decisions. Replay pacing is for explanation and does not claim to be real
model timing. A connected run remains pending until the existing API returns;
only then are original decisions and reports rendered. No private chain-of-thought
or synthetic live transcript is requested or shown.

## Requirement/rubric/data alignment

| Surface | C2 / JR support | Exact consumed fields and limits |
|---|---|---|
| Airport conditions and selected flight | C2-09 to C2-22; JR-01/JR-04 | Source raw AIRLINE, FLIGHT_NUMBER, ORIGIN_AIRPORT, DESTINATION_AIRPORT, WEATHER_DELAY; historical minutes. Shared source row remains unchanged. ATC opening/blockage windows and Ground gate/crew arrays are labelled scenario state. |
| Motion, route and stand | C2-22; JR-02/JR-04 | Assignment landing_min/gate_out_min, shared taxi minutes, gate_id/taxi_route_id; derived gate-in = landing + taxi. Geographic mapping/position are missing from the backend and explicitly illustrative. No operational execution. |
| Independent agent panel | C2-01 to C2-07/C2-24/C2-26; JR-02/JR-04 | AgentReply role, round, current plan, ModelDecision verdict/reason/citations and DomainReport checks. Preserve original evidence, do not infer votes from prose. |
| Why this plan / alternatives | C2-04/C2-06/C2-07; JR-03/JR-05 | candidate_reports, actual hard failures and deterministic metrics. Delay/overtime in simulated minutes, connections in passenger counts, turbulence ordinal. Feasible alternatives stay labelled feasible, not unsafe. |
| Playback, rounds and export | C2-07/C2-08/C2-23/C2-25; JR-03/JR-04/JR-06 | Original event order, outcome/reason, rounds, agent invocations/model calls, retries. Explicit replay/pending state; backend two-round deadlines/fallback remain authoritative. |
| Human review | C2-02/C2-26; JR-04 | Local draft review state and full evidence export; qualified person reviews a recommendation. There is no invented backend approval/execution call. |

Every named responsibility remains available: ATC runway/wake/taxi checks and
arrival count; Pilot earliest arrival, fuel, turbulence and passenger connections;
Ground stands, crew availability, turnaround and overtime. The UI does not remove
a responsibility because the original CSV lacks its operational input.

## Real geography and simulation boundary

The map includes actual OpenStreetMap airport geometry, with visible ODbL
attribution and a dedicated license notice. It includes seven runway pairs and
the actual central terminal footprints. Original mapped coordinates, feature
identities and download hashes are retained in the cached map data.

The backend's single runway and T1/T2/G1/G2 abstraction does not designate a real
runway, taxiway or gate. Geographic routes and simulation stands are presentation
mapping, not a certified airport layout/clearance model. The moving positions are
derived animation, not ADS-B or live ground radar. Coordinates were not added to
the agent protocol and are never fed into its validators as purported real facts.
Historical flight row 76 and simulated operating state remain distinguishable.

This supports a polished explanation of the build; it cannot establish live
flight safety, authentic physical routing, measured fuel savings or actual
operational benefit. The same limitation applies to the prototype backend.

## Interaction and convergence

Frontend consumes backend results; it does not rank plans with AI, change hard
limits or override consensus. Replay uses the original two-round stored sequence.
Drills use separate scenario versions. An API failure produces a retryable error;
an escalated result hides the proposed route and disables recommendation review.
Backend consensus/fallback/escalation are distinct, and counts are never reset to
make multiple runs look like one. Individual live progress requires a future
backend job/event-stream contract rather than fabricated frontend timers.

## Scope trade-off and acceptance checks

One real airport, three scenario aircraft and cached vector geometry are the
six-hour trade-off. Avoid API-key map services, live traffic subscriptions, 3D,
another agent SDK and provider secrets in the browser. No backend contract or
domain evaluator was changed for this draft.

Acceptance: production frontend build; focused data/motion/fixture tests;
desktop/mobile browser inspection; moving aircraft stop at assigned stands;
selection/hover/focus and route visibility work; replay shows actual counteroffers
then fresh acceptance; crew drill changes the selected plan; closed-runway drill
escalates; connected API renders original evidence; reduced motion starts paused;
source hashes/reference checks still pass. Final verification evidence is recorded
with the handoff, not inferred from the design description.

## Verification snapshot

- Production frontend build passed; nine focused fixture/data/movement tests passed.
- Browser inspection covered 1440px, 1280px and 390px; mobile has no horizontal overflow.
- Browser verified moving/paused aircraft, hover details, agent check disclosure,
  alternative evidence, recorded counteroffers followed by acceptance, crew drill
  selecting P2, and no-runway escalation hiding the route/disabling review.
- The frontend submitted an actual request to the local Python API and rendered
  its returned result/events. The server used offline responses; no live model
  claim follows from this connection check.
- Reduced-motion emulation starts aircraft playback paused.
- Tracks retire when their declared stand occupancy ends; no invented outbound
  route or lingering icon blocks a later plan's use of the same stand.
- Mechanical design detector returned no findings. Independent visual review
  identified one mobile evidence-entry issue; the labelled action was restored
  and the reviewer scored that finding resolved. Its final Ship verdict is a
  fix-only verification, not certification of operational suitability.
- The full source/reference check passed, preserving original input hashes.

The user has not approved the visual direction as a finished product; this is
the concrete interactive draft requested for review. The local preview remains
available through Vite. No merge into main or public deployment is part of this draft.
