# Challenge #2 - canonical requirements

Source: [original PDF](../references/airbus-track.pdf), physical pages 2-3
(printed 2/6 and 3/6); corroborating
[screenshot](../references/challenge-2-screenshot.png). The screenshot ends at
the avoidance list and does not include the data instructions or turn limit.
Prepared 2026-10-31, Asia/Singapore. This is a faithful structured normalization;
implementation interpretations are explicitly separated below.

## Problem and intended outcome

Help air traffic controllers, pilots and ground operations staff make faster,
better decisions when runway closure, weather delay or equipment failure creates
disruption. The brief describes manual calls and software updates that cause
cascading delays, excessive holding and fuel use. It requests a Multi-Agent
Communication Framework that negotiates trade-offs across organizational domains.

## Requirements from the brief

| ID | Source requirement | Source page |
|---|---|---:|
| C2-01 | Include independently operating ATC AI, pilot AI and ground operations AI agents. | 2 |
| C2-02 | Agents negotiate disruption resolutions autonomously until consensus, without human intervention during that negotiation. | 2 |
| C2-03 | Agents exchange structured data/messages. | 2 |
| C2-04 | Evaluate cross-domain constraints. | 2 |
| C2-05 | Converge on an agreed solution. | 2 |
| C2-06 | Perform explicit constraint checking. | 2 |
| C2-07 | Provide a traceable consensus log. | 2 |
| C2-08 | Provide a deterministic non-AI fallback. | 2 |
| C2-09 | ATC accounts for runway wake separation. | 2 |
| C2-10 | ATC accounts for taxiway blockage. | 2 |
| C2-11 | ATC seeks to maximize sector throughput. | 2 |
| C2-12 | Pilot preserves fuel reserves. | 2 |
| C2-13 | Pilot ensures flight safety. | 2 |
| C2-14 | Pilot seeks to minimize turbulence. | 2 |
| C2-15 | Pilot protects passengers' connections. | 2 |
| C2-16 | Ground seeks to optimize gate utilization. | 2 |
| C2-17 | Ground seeks to avoid ground-crew overtime. | 2 |
| C2-18 | Ground seeks to minimize turnaround delays. | 2 |
| C2-19 | Use the provided US Department of Transportation 2015 flight delays and cancellations data in the Challenge #2/DATA folder. | 2 |
| C2-20 | Select a row satisfying WEATHER_DELAY > 15 OR LATE_AIRCRAFT_DELAY > 20. | 2 |
| C2-21 | Pass the parameters from that row into all three agents. | 2 |
| C2-22 | Demonstrate negotiation of revised arrival time, gate assignment, or flight-plan adjustment. The source uses "or". | 3 |
| C2-23 | Demonstrate this negotiation "in under 3 turns". | 3 |
| C2-24 | Do not combine the three roles into one prompt call; independent-domain coordination is the point. | 2 |
| C2-25 | Avoid endless unconstrained LLM conversation; provide convergence logic and turn limits. | 2 |
| C2-26 | Agents must not accept solutions that disregard safety margins or operational constraints. | 2 |

These requirements do not specify an SDK, model/provider, central LLM supervisor,
number of airports/flights/gates, simulator implementation, training requirement,
or numerical wake/fuel/turbulence limits. They do not guarantee feasible consensus
for every possible input. Do not invent those details as source requirements.

## Eligibility rule and boundaries

Treat delay fields as numeric minutes after validation. Strict comparisons apply:

| WEATHER_DELAY | LATE_AIRCRAFT_DELAY | Eligible? |
|---:|---:|---|
| 15 | 20 | No |
| 16 | 20 | Yes |
| 15 | 21 | Yes |
| 0 | 21 | Yes |

Missing values are unknown; do not rewrite the original row to make it qualify.
Retain a stable row identifier and source hash. See [dataset facts](datasets.md)
for the actual provided file; all 358,774 supplied rows qualify.

## Interpretation register

- **Turn terminology:** "turn" is not defined in the PDF. Two complete
  proposal/evaluation rounds is a proposed interpretation, not an organizer
  clarification. Publish both round and individual model-call counts, and avoid
  claiming literal turn compliance until the interpretation is confirmed.
- **Hard limits and preferences:** exact classifications and thresholds need
  documented scenario rules. Safety constraints are mandatory; relative weights
  for throughput, comfort, connections and overtime are not supplied.
- **Autonomy and human control:** the challenge requires autonomous negotiation;
  [JR-04](judging-rubric.md) requires qualified-person control. The proposed
  reconciliation is autonomous plan negotiation followed by human review of the
  recommendation, without operational execution. This is a project interpretation.
- **Real time:** the source describes real-time disruptions, but supplies static
  history. Label a replay/simulation honestly; do not describe historical CSV
  rows as live airport state.

## Completion evidence

Use the [alignment matrix](alignment-checklist.md). A conversation transcript
alone is insufficient: show the actual row, independent calls, structured
messages, applied checks, changed proposal, agreement on a specific plan version,
and deterministic fallback/failure behaviour. Initial implementation status for
all requirements is **not implemented / not tested**.
