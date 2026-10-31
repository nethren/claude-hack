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

## Run a scenario

Choose **Arrival conflict** or **Crew delay**, then click **Run scenario**.
The view starts at P0, shows the agents' objections, proposes a new plan and
collects fresh approvals. Aircraft then move through their assigned arrivals and
stands. Completed tracks leave the map at gate-out. Switch scenarios to reset.

The map uses neutral black surfaces and yellow-green selection. The larger
message panel gives ATC, Pilot and Ground distinct icons and verdict colors.
Expand a message's checks or **Why this plan?** for the supporting evidence.
**Details** holds the data scope, model-call count and evidence export.

The user requested frontend review before backend integration. The Run action
uses prepared backend outputs through `src/lib/scenario-runner.js`; it makes no
provider or backend request. A future adapter can feed the same original reply
and result events into the view. No API key enters the browser.

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
