# Autonomous SG 2026 - Airbus Challenge #2

Multi-agent disruption-coordination prototype for a four-person, six-hour build.
The `coordinator` branch integrates the published Pilot/Ground agents and a
compatible reference ATC agent with a tested Python backend. Offline integration
and mocked-provider tests pass; live LLM performance is not yet evaluated.

## Run the backend

Use Python 3.11+ from this repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python app.py --mode offline
python -m pytest -q
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Offline mode exercises the real adapters and checks using scripted model replies;
it is not a live AI demonstration. For live configuration, API endpoints, frontend
integration and current limitations, read the [backend handoff](docs/backend.md).
Evidence and results are saved under ignored `logs/`.

## Review the frontend draft

The `codex/frontend-draft` branch adds a React + Vite airport surface dashboard:
real attributed DFW geometry, moving simulated aircraft, selected routes, agent
decisions/check evidence and scenario drills. From this branch:

```sh
cd frontend
npm ci
npm run dev
```

Open Vite's local URL. Recorded mode works without the Python server. Connection
settings can use the existing local backend. This is an interactive review draft;
scripted replay, simulated operating state and illustrative geographic routing
are explicit. Read [frontend setup](frontend/README.md) and
[review/alignment notes](docs/frontend-review.md).

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

For teammate implementation, start with the
[architecture and shared contract](docs/ai-orchestration-architecture.md) and its
[complete labelled integration fixture](docs/examples/coordination-scenario-v1.json).
The fixture includes one real source row and simulated operational state. The
backend suite runs it end to end; it is not a live-agent benchmark.

## Check the references

```sh
python3 scripts/check_alignment.py
```

Python's standard library is sufficient. The check verifies source hashes,
schemas, row counts, disruption eligibility, lookup joins, Markdown links and
requirement coverage. It does not establish that the intended system is built.
