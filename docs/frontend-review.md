# Frontend review: two scenario runs

React + Vite on `codex/frontend-draft`. The user requested a simpler page, neutral
black surfaces, yellow-green selection, a larger map and a larger agent message
panel. The view now offers Arrival conflict and Crew delay, each with one
**Run scenario** action. It removes the scrubber and repeated replay labels.
Backend integration follows the user's review; this revision changes no Python
code or agent contract.

## Run flow

Each run starts at P0. The view shows original ATC, Pilot and Ground decisions,
then a new proposal and fresh second-round approvals. Aircraft move after a
valid result. The view stops when the last aircraft completes its stand window.
Switching scenarios cancels pending messages and resets the view. Reduced-motion
users get the same decisions with a final static traffic state.

Role icons differ in shape, symbol and color: a blue tower for ATC, a yellow-green
aircraft for Pilot and an amber vehicle for Ground. Approval badges use green;
counteroffers use amber; rejection and failed checks use red. Short summaries
come from the actual checks. Message disclosures use the exact plan each agent
reviewed. The export retains original decisions and source fields.

Details holds the demo-data scope and pending backend status. The primary view
uses historical callsigns instead of SIM labels. No live label or real-model
progress claim appears in the view.

## Requirement and data alignment

| Surface | C2 / JR support | Inputs and limits |
|---|---|---|
| Airfield and flight labels | C2-19 to C2-22; JR-01/JR-04 | Raw AIRLINE, FLIGHT_NUMBER, ORIGIN_AIRPORT and DESTINATION_AIRPORT. AA1344 uses row 76; display labels AA184/AA1068 use rows 20/49. Keep F2/F3 operational overlays synthetic. |
| Route and movement | C2-22; JR-02/JR-04 | Integer landing_min, gate_out_min, shared taxi minutes and gate/route IDs. Gate-in = landing + taxi. Geographic routes and positions remain illustrative. |
| Agent messages and verdicts | C2-01 to C2-07/C2-24/C2-26; JR-02/JR-04 | Original role, proposal, round, verdict and reports. Display summaries preserve the constraint and connection trade-offs; they do not replace the original evidence. |
| Plan comparison | C2-04/C2-06/C2-07; JR-03/JR-05 | Hard failures and deterministic metrics. A feasible alternative stays feasible. Connections count passengers; delay and overtime use scenario minutes. |
| Run and review | C2-05/C2-07/C2-08/C2-23/C2-25; JR-03/JR-04 | Separate rounds and new approvals; explicit outcomes and export. Two visible scenarios use prepared outputs, not new model generations. Backend limits/fallback remain unchanged. |

The checks still cover wake spacing, runway/taxiway access, throughput, fuel,
turbulence, passenger connections, gate/stand use, crew availability/overtime and
turnaround. The view moves details behind disclosures rather than dropping a
responsibility.

## Provenance and backend boundary

The actual seed remains CSV row 76: AA1344 DEN–DFW, WEATHER_DELAY=35 and
LATE_AIRCRAFT_DELAY=40 minutes. The provided raw row stays intact. All three
backend agents receive the same source envelope under the existing protocol.
Display aliases do not add another observed flight row to that contract.

The supplied CSV lacks geographic taxi routes, gates, fuel, wake classes,
passenger itineraries and crew state. OpenStreetMap supplies real geometry;
the scenario supplies labelled operational overlays. The view does not imply
that the cached 2015 flight identities share observed traffic positions.

The two Run flows use stored coordinator outputs and client-side presentation
timers. They do not call an LLM or backend. Details states **Demo data** and
**Prepared responses**, and lists backend integration as pending UI review.
The export includes the original messages, checks, source fields and display
identity provenance. The UI sends no airport instructions.

## Six-hour trade-off and checks

Keep one airport, three aircraft, two scenarios and cached geometry. Use one
frontend event boundary so a backend adapter can replace the prepared flow after
review. Avoid live traffic subscriptions, map keys, another agent SDK and changes
to teammate contracts.

Frontend checks cover the two cases, source labels, report-bound summaries,
fresh-round approvals, pending-event cancellation, movement and track retirement.
Browser checks cover Run through completion, colored decisions, map/flight
selection, keyboard scenario choice, mobile layout and accessible evidence.
The build and source/reference checks must pass before handoff. Keep earlier
backend/API verification separate from this frontend-only revision's evidence.
