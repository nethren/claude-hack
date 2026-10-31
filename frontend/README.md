# Groundline interactive frontend draft

React + Vite review draft, following the user's airport surface radar brief.
Use Node 20.19.x+ within Node 20, or Node 22.12+ (tested with Node 23.6).
Run from this folder:

```sh
npm ci
npm run dev
```

Open the URL printed by Vite. For a production build and focused data-alignment
checks:

```sh
npm run build
npm test
```

No Python server, provider key or internet map connection is required for the
recorded demo. Fonts, geometry and recorded results are served locally.

## Review the draft

- Hover, focus or click an aircraft; use the traffic row as a keyboard/touch alternative.
- The highlighted aircraft's route and assigned simulation stand use warm lime.
- Pause/play, scrub or change speed. Taxiing aircraft move; aircraft at stands stop.
- Completed tracks retire at gate-out, so a later aircraft can reuse the stand.
- Replay coordination to see initial objections, counteroffers, a new proposal,
  and independent acceptance. The sequence is explicitly recorded replay.
- Expand an agent for actual report checks; expand an alternative for its evidence.
- Select Crew delay drill to see P1 fail crew availability and P2 selected.
- Select No runway drill to see explicit escalation with no proposed route.
- Mark the recommendation reviewed locally, or export its original decision evidence.

The top-right connection settings switch between the recorded demo and the
existing Python backend. Start that backend from the repository root:

```sh
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Vite proxies `/api` to `http://127.0.0.1:8000`; set `BACKEND_URL` when starting
Vite to change the target. The UI submits ScenarioInput to `POST /runs` and
fetches `/runs/{run_id}/events` after the RunResult returns. During the request
it displays pending status. It does not fabricate streaming agent progress.
Actual model/provider mode remains configured on the server; no key enters the browser.

## Evidence and data boundaries

`public/data/demo-run.json`, `demo-crew.json` and `demo-closed.json` are exports
of actual coordinator runs with explicitly scripted ModelDecision replies.
They preserve actual reports, original decision messages and all 31 raw source
fields. The fixture generator records zero real model calls. Regenerate from
the repository root using:

```sh
.venv/bin/python frontend/scripts/build-demo-fixture.py
```

`public/data/dfw-layout.json` includes 365 mapped features: taxiway centerlines,
aprons, terminal footprints and all seven DFW runway pairs. Geographic data was
downloaded from OpenStreetMap's Overpass API and official central-area map API.
Its metadata retains source hashes and attribution. See
[geographic license notice](public/data/LICENSE.txt) and
[OpenStreetMap attribution](https://www.openstreetmap.org/copyright).

The API's T1/T2, G1/G2 and integer time values have no geographic waypoint or
live track contract. Mapping them onto the airport is an **illustrative
presentation overlay**. The preparer follows mapped centerlines where possible,
but does not evaluate runway-crossing clearances, routing restrictions or
actual stand availability. G1/G2 are simulation stands, not real DFW gate IDs.
The dashboard labels simulated movement, routes and operating conditions.
No wind, visibility, live weather or other unprovided telemetry is invented.

Map preparation script: `scripts/build-map.py <overpass.json> <terminal-area.osm>`.
It accepts downloaded source files rather than making hidden network requests.
Fonts: IBM Plex Sans/Mono through Fontsource. Icons: Lucide.

## Scope

This is a frontend review branch based on the tested coordinator backend. It
does not merge teammates' ongoing main changes. UI approval remains local to
this draft; no airport action or backend approval endpoint is invented.
True incremental agent updates require a future backend streaming/job contract.
See [frontend alignment and review notes](../docs/frontend-review.md),
[PRODUCT.md](../PRODUCT.md) and [DESIGN.md](../DESIGN.md).
