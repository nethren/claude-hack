# Groundline: Autonomous SG 2026, Airbus Challenge #2

Three independent Claude agents (ATC, Pilot and Ground) negotiate a flight-disruption
plan in at most two rounds, while Python enforces every safety rule. A deterministic
coordinator picks among complete plans by a fixed policy, never by vote, and returns one
of three outcomes for a human controller: **consensus**, a **checked fallback**, or an
urgent **escalation**. A React dashboard on a DFW airport map runs real agent calls on a
real 2015 DOT delayed flight and shows each agent's reasoning, the checks behind it and a
modelled fuel/CO₂ estimate.

## How it works

| Part | Uses an LLM for | Code is responsible for |
|---|---|---|
| ATC agent | Choosing and explaining among valid plans | Runway windows, wake separation, taxiway blockage, throughput, delay |
| Pilot agent | Choosing and explaining among valid plans | Fuel reserve after holding, turbulence cap, passenger connections |
| Ground agent | Choosing and explaining among valid plans | Stand conflicts, crew availability and overtime, turnaround |
| Coordinator | Nothing | Proposals, reply validation, ranking, deadlines, fallback, evidence log |

Each agent answers ACCEPT, COUNTER (ranked safe alternatives) or REJECT. A vote that
accepts a plan failing its own checks, cites a check that does not exist or is malformed
is rejected in code. Consensus needs all three to accept the same plan plus a final
re-check. Runs are bounded: at most 2 rounds and 6 model calls, no retries, 40 s.
Every result is a recommendation for a controller; nothing is executed.

## Run the demo

Python 3.11+ and Node 20.19+/22.12+, from the repository root:

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m dev.serve --live                   # live Claude agents
cd frontend && npm ci && npm run dev                        # in a second terminal
```

Live mode reads `ANTHROPIC_API_KEY` from the environment or a git-ignored `.env`
(see [.env.example](.env.example)); drop `--live` to run offline test agents with no key.
Open the Vite URL, choose a scenario and click **Run scenario**.

| Scenario | Situation | Outcome |
|---|---|---|
| All clear | The proposed plan already fits runway spacing, fuel and stands | Consensus in round 1 |
| Counteroffer | 2 min arrival gap (3 min required) and a shared stand | Agents counter; coordinator proposes P1; consensus in round 2 (fallback if a live agent times out) |
| Runway closed | Runway closed until +45 min; every plan lands earlier | Escalated: urgent controller alert with fuel deadlines |

All three reached these outcomes with live Claude agents on 31 Oct 2026. Flight identity
is real (CSV row 76); fuel, stands, crews and runway state are simulated and labelled.

## Test

```sh
.venv/Scripts/python -m pytest -q           # 206 backend tests
cd frontend && npm test && npm run build    # 24 frontend tests + build
.venv/Scripts/python scripts/check_alignment.py
```

The alignment check verifies source hashes, schemas, row counts, disruption eligibility,
lookup joins, Markdown links and requirement coverage.

## Project layout

| Path | Contents |
|---|---|
| `agents/`, `domains/` | ATC, Pilot and Ground LLM adapters and their deterministic checkers |
| `runtime/` | Coordinator, model gateway, scenario loader, demo scenarios, event log |
| `contracts/` | Shared protocol 1.0 types |
| `analysis/` | Fuel/CO₂ modelled estimate |
| `api.py`, `api_fuel.py`, `app.py` | FastAPI backend (with fuel panel) and CLI |
| `frontend/` | React + Vite dashboard ([setup](frontend/README.md)) |
| `dev/serve.py` | Starts the backend offline or live |
| `tests/` | Backend test suite |
| `docs/`, `data/raw/`, `references/` | Requirements, design, decisions, source data and the original brief |

## Known limits

Agents choose from a bounded catalog of plans, so an escalation does not prove no
feasible plan exists. Fuel is a holding-only model. The ranking order is a prototype
policy, not an aviation standard. The Pilot agent can exceed the 15 s per-call limit in
round 2, which ends the run in a safe fallback. See [backend notes](docs/backend.md) and
the [decision log](docs/decision-log.md).

## Start here

| Document | Purpose |
|---|---|
| [AGENTS.md](AGENTS.md) | Persistent project instructions and required decision checks |
| [CLAUDE.md](CLAUDE.md) | Entry point for Claude sessions |
| [Challenge #2 requirements](docs/challenge-2-requirements.md) | Complete selected-challenge requirements with stable IDs |
| [Judging rubric](docs/judging-rubric.md) | Official weights, scoring, strong/weak evidence |
| [Dataset contract](docs/datasets.md) | All three CSV schemas, full-file checks, joins, limits and examples |
| [Multi-agent constraints](docs/multi-agent-design-constraints.md) | Skill alignment and proposed coordination rules |
| [AI orchestration architecture](docs/ai-orchestration-architecture.md) | Protocol 1.0, teammate ownership, shared types, domain tools, integration and failure contracts |
| [Architecture explained simply](docs/architecture-explained.md) | Plain-language breakdown of the three AI agents, Python coordinator, negotiation and fallback |
| [Backend handoff](docs/backend.md) | Run/test instructions, API, integration provenance and verified limits |
| [Frontend review draft](docs/frontend-review.md) | Surface radar, agent review, geography/telemetry limits and verification |
| [Alignment checklist](docs/alignment-checklist.md) | Requirement-to-data-to-proof matrix |
| [Decision log](docs/decision-log.md) | Confirmed context, proposals, assumptions and unresolved questions |
| [Full track brief](docs/airbus-track-brief.md) | Normalized reference for all five challenges |
| [Source register](docs/source-register.md) | Source locations, exact hashes, provenance and conversion limits |

## Included source data

- [Airlines CSV](data/raw/airlines.csv): 14 rows, 2 columns.
- [Airports CSV](data/raw/airports.csv): 322 rows, 7 columns.
- [Flights CSV](data/raw/flights.csv): 358,774 rows, 31 columns.
- [Original challenge brief and rubric](references/airbus-track.pdf).
- [User's Challenge #2 screenshot](references/challenge-2-screenshot.png).

The flight file already satisfies the challenge's disruption predicate on every
row. It has no October rows, cancellations or diversions. Its earlier filtering
history is unknown. It supports replay scenarios; it is not a representative
sample for estimating general delay prevalence or a causal benchmark for fuel
and delay savings. Operational state such as fuel, gates and crew schedules is
absent and must be supplied and labelled separately.

Readable complete lookup tables are available for
[airlines](docs/data/airlines.md) and [airports](docs/data/airports.md).
[Flight examples](docs/data/flight-scenarios.md) preserve selected complete source
rows and identify their original CSV row numbers. The full flights CSV is kept
as the lossless source rather than duplicated into a very large Markdown table.
