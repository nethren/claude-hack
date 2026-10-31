# Groundline frontend draft

React + Vite. Use Node 20.19.x+ within Node 20, or Node 22.12+.

```sh
npm ci
npm run dev
```

Open the URL from Vite. Check the build and frontend logic with:

```sh
npm run build
npm test
```

## Run the integrated demo

Start the backend (API + fuel/CO2 panel) from the repository root, then the
frontend. Vite proxies `/api` to the backend on port 8000.

```sh
.venv/Scripts/python -m dev.serve          # offline test agents, no key needed
.venv/Scripts/python -m dev.serve --live   # live Claude agents (key from env or .env)
cd frontend && npm run dev
```

Choose a scenario and click **Run scenario**. The browser sends the scenario to
`POST /runs`; the coordinator invokes the ATC, Pilot and Ground agents
independently and checks every reply in code. The view then replays the run's
own recorded events. The header badge shows whether the agents were live
Claude calls or the offline test double. No API key enters the browser.

| Scenario | Story | Deterministic checks allow |
|---|---|---|
| **All clear** | The proposed plan P1 already passes every domain | CONSENSUS in round 1 |
| **Counteroffer** | P0 has a 2 min arrival gap and a shared stand | Counteroffers, P1 selected; CONSENSUS (or FALLBACK if a live agent times out) |
| **Runway closed** | Runway closed until +45 min; every plan lands earlier | ESCALATED to a controller |

Escalation shows an urgent alert with the soonest fuel-reserve deadline, the
rules that ruled out every plan and a **Take control** action. Plans with a
selected result show a modelled fuel/CO2 estimate from `/runs/{id}/fuel-co2`.
Live agents decide their own verdicts, so a live run can legitimately differ
from the offline outcome; the view shows whatever the run produced.

The map uses neutral black surfaces and yellow-green selection. The larger
message panel gives ATC, Pilot and Ground distinct icons and verdict colors,
plus each agent's own reason. Expand a message's checks or **Why this plan?**
for the supporting evidence. **Details** holds the data scope, model-call count
and evidence export.

## Hosted site (groundline.nethren.com)

`npm run deploy` publishes one Cloudflare Worker. It serves `dist/` and sends
`/api/*` to the Python backend running in a Cloudflare Container built from the
repository's `Dockerfile`, in live mode. Clicking **Run scenario** on the site
invokes the three Claude agents for real. The Worker forwards only the routes
the app uses, caps the scenario body and rate limits runs (3 a minute per
visitor, 10 site-wide). The Anthropic key is a Worker secret passed to the
container at start; it is in no file and not in the browser.

First deploy, from `frontend/`. Needs Docker running and the Workers Paid plan,
which Containers require:

```sh
npx wrangler login
npx wrangler secret put ANTHROPIC_API_KEY
npm run deploy
```

`npm run deploy:static` is the free fallback. It publishes a copy with no
backend that replays `public/data/runs/*.json`, one recorded live run per
scenario, labelled "Recorded live Claude run". Re-record those with the backend
running (`python -m dev.serve --live`) via `python frontend/scripts/record-runs.py`.

## Data and evidence

`public/data/demo-run.json` and `demo-crew.json` contain actual coordinator outputs
with scripted decisions and zero model generations. The hidden no-runway fixture
remains for regression checks. Keep these original messages, checks, identities
and source envelopes unchanged. Regenerate them from the repository root with:

```sh
.venv/bin/python frontend/scripts/build-demo-fixture.py
```

Display labels come from the supplied CSV: AA1344 on row 76, AA184 on row 20 and
AA1068 on row 49. `src/lib/flight-identities.js` holds those labels. F2/F3 keep
their original synthetic operational identity in the backend scenario. Their
historical labels do not establish observed positions, fuel or shared traffic.
Details and the export preserve that distinction.

`public/data/dfw-layout.json` contains 365 mapped features, including seven DFW
runway pairs and the central terminals. Geometry comes from OpenStreetMap; the
cache retains coordinates, source hashes and attribution. See the
[geographic license](public/data/LICENSE.txt) and
[OpenStreetMap attribution](https://www.openstreetmap.org/copyright).

The API's T1/T2/G1/G2 abstraction has no geographic waypoint contract. Map routes,
stand anchors and aircraft movement are illustrative. The map does not check
runway-crossing clearances or real stand availability. It provides a visual
explanation of the scenario, rather than an operational routing system.

`scripts/build-map.py <overpass.json> <terminal-area.osm>` prepares the geometry
cache from downloaded source files. Fontsource supplies IBM Plex fonts; Lucide
supplies interface icons.

## Review scope

Frontend changes stay on `codex/frontend-draft`. They do not alter the agent
protocol, domain evaluators or teammate merges. See
[review and alignment notes](../docs/frontend-review.md),
[product context](../PRODUCT.md) and [visual system](../DESIGN.md).
