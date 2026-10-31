# Autonomous SG 2026 - Airbus Challenge #2

Requirements and data reference repository for a four-person, six-hour build of
a multi-agent disruption-coordination demonstration. No application has been
implemented or evaluated in this initial documentation commit.

## Start here

| Document | Purpose |
|---|---|
| [AGENTS.md](AGENTS.md) | Persistent project instructions and required decision checks |
| [CLAUDE.md](CLAUDE.md) | Entry point for Claude sessions |
| [Challenge #2 requirements](docs/challenge-2-requirements.md) | Complete selected-challenge requirements with stable IDs |
| [Judging rubric](docs/judging-rubric.md) | Official weights, scoring, strong/weak evidence |
| [Dataset contract](docs/datasets.md) | All three CSV schemas, full-file checks, joins, limits and examples |
| [Multi-agent constraints](docs/multi-agent-design-constraints.md) | Skill alignment and proposed coordination rules |
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

## Check the references

```sh
python3 scripts/check_alignment.py
```

Python's standard library is sufficient. The check verifies source hashes,
schemas, row counts, disruption eligibility, lookup joins, Markdown links and
requirement coverage. It does not establish that the intended system is built.
