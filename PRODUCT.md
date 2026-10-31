# Autonomous SG coordination prototype

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

User selected React + Vite and an interactive code-first review draft on 2026-10-31.
Python/FastAPI backend follows protocol 1.0; frontend development must preserve
its existing agent contracts and source-data requirements.

## Users

An airport controller reviewing a disruption recovery recommendation. Hackathon
judges and teammates also need to understand the autonomous agent coordination.

## Product Purpose

Show the affected aircraft, proposed arrival/taxi/gate plan, airport constraints,
and why independently invoked ATC, Pilot and Ground agents agree or object.
Keep the recommendation reviewable by a qualified person.

## Operating Context

Four builders, six-hour hackathon scope. Current scenario uses DFW and one actual
historical flight row. Operational conditions, extra traffic and route animations
are simulated. The backend currently returns completed results and evidence;
there is no event streaming or live position telemetry.

## Capabilities and Constraints

- Use real, attributed airport geometry. Keep the demo-data scope in Details;
  remove repeated replay/simulation labels from the main workspace.
- Highlight the selected aircraft and its proposed route. Expose details on hover,
  focus and click; move aircraft only according to the simulation timeline.
- Make three agents and their ACCEPT/COUNTER/REJECT statuses visible in plain language.
- Show stated reasons and applied check evidence, never private chain-of-thought.
- Keep CONSENSUS, FALLBACK, ESCALATED and INPUT_ERROR distinct.
- Do not fabricate live agent progress for an API that returns terminal results.
- A review draft is not permission to execute airport instructions.

## Brand Commitments

User requested a radar/plane tracker interface with illuminated route guidance,
an airport conditions section and simple aircraft icons. It should be polished,
understandable and restrained rather than a technical agent-debugging console.
The user now wants neutral black surfaces, yellow-green selection, a larger map,
larger agent messages, distinct role icons and colored verdicts. Use two scenarios
and one Run action; remove the scrubber. Apply stop-slop to the visible copy.

## Evidence on Hand

Challenge/rubric/dataset docs, complete protocol 1.0, backend source and tests,
the real row-76 scenario, and the user's radar reference image. No observed
fuel/crew/weather telemetry or airport-coordinate waypoints exist in that contract.

## Product Principles

- Let the airport and selected aircraft lead the screen.
- Explain a decision through visible constraints, alternatives and source evidence.
- Keep provenance and backend status in Details. Run the two local scenarios
  from start to finish; connect the backend after the user reviews this revision.
- Use plain operational labels; keep hashes, raw JSON and configuration in secondary views.
