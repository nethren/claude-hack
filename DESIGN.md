---
name: Groundline
description: Airport surface radar for reviewing a simulated disruption recovery recommendation.
colors:
  background: "#10191c"
  map: "#111d20"
  text: "#e7eeea"
  muted: "#96aaa6"
  quiet: "#879c99"
  line: "#2a3739"
  accent: "#d8ed91"
  accent-hover: "#e6f6b1"
  action-ink: "#243225"
  mint: "#a6d7bc"
  amber: "#e0b37e"
  rose: "#eda69b"
  map-grid: "#233236"
  raised-surface: "#1a282b"
  review-surface: "#1d2a27"
  selected-surface: "#1d2927"
  agreement-surface: "#1c2b27"
  escalation-surface: "#302822"
typography:
  headline:
    fontFamily: "'IBM Plex Sans', sans-serif"
    fontSize: "17px"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "-.25px"
  title:
    fontFamily: "'IBM Plex Sans', sans-serif"
    fontSize: "15px"
    fontWeight: 500
  body:
    fontFamily: "'IBM Plex Sans', sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "'IBM Plex Sans', sans-serif"
    fontSize: "10px"
    fontWeight: 400
  flight:
    fontFamily: "'IBM Plex Mono', monospace"
    fontSize: "12px"
    fontWeight: 500
  measurement:
    fontFamily: "'IBM Plex Mono', monospace"
    fontSize: "11px"
    fontWeight: 400
rounded:
  tag: "3px"
  action: "5px"
  control: "6px"
  stage: "8px"
  flight: "9px"
  tooltip: "10px"
  surface: "12px"
spacing:
  fine: "4px"
  small: "8px"
  compact: "12px"
  regular: "16px"
  inset: "20px"
  gutter: "24px"
  desktop: "30px"
  wide: "36px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.action}"
    padding: "12px 16px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-review:
    backgroundColor: "{colors.review-surface}"
    textColor: "#dbe7c8"
    rounded: "{rounded.action}"
    padding: "10px 5px"
    width: "100%"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    padding: "7px 0"
  source-select:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text}"
    rounded: "{rounded.action}"
    padding: "9px"
    width: "100%"
  traffic-selected:
    backgroundColor: "{colors.selected-surface}"
    rounded: "{rounded.control}"
    padding: "11px 12px"
  coordination-stage:
    backgroundColor: "{colors.agreement-surface}"
    rounded: "{rounded.stage}"
    padding: "14px 13px"
  coordination-escalated:
    backgroundColor: "{colors.escalation-surface}"
    textColor: "{colors.amber}"
  map-surface:
    backgroundColor: "{colors.map}"
    rounded: "{rounded.surface}"
  flight-card:
    backgroundColor: "#152326"
    rounded: "{rounded.flight}"
    padding: "13px 15px 12px"
    width: "260px"
---

# Design System: Groundline frontend draft

## Overview

**Creative North Star: "Airport surface radar"**

Groundline keeps the established controller review-desk direction: a low-light airport surface, quiet technical geometry and one illuminated aircraft/route selection. The map leads; concise operational explanations and independently labelled ATC, Pilot and Ground reviews sit beside it. Ruled sections carry information without a generic grid of dashboard cards. Its references remain airport CAD, flight progress strips, surface radar, marine charts, aerodrome diagrams, cockpit navigation displays and terminal wayfinding.

This is a scan of the implemented React + Vite review draft, refreshed on 2026-10-31 from `frontend/src/styles.css`, `App.jsx`, `AirportMap.jsx` and their movement/coordination helpers. IBM Plex fonts are bundled through Fontsource; interface icons and aircraft/map geometry are SVG. No approved raster comp or image asset establishes another identity. Desktop, 1280px and mobile review captures document this draft. The reviewer's final **Ship at fix-only scope** disposition followed restoration of the mobile evidence entry point; it does not establish finished-product approval, live-model performance or operational suitability. Product truth remains in [PRODUCT.md](PRODUCT.md); surface scope remains in [.impeccable/surfaces/frontend.md](.impeccable/surfaces/frontend.md).

**Key Characteristics:**

- Matte charcoal-green surfaces, subdued blue-green airport geometry and off-white reading text.
- Warm lime for selection, route guidance, primary action and keyboard focus.
- Compact sans-serif explanations with monospace flight IDs, times and measurements.
- Flat ruled sections; small bounded panels for grouping and overlays.
- Recorded replay, simulated movement, backend waiting and human review remain visibly distinct.

## Colors

The sidecar’s eight-step tonal ramps are generated preview metadata, not additional implemented UI tokens; CSS and the extracted frontmatter remain the source of truth.

The palette is a dark operational field with one legible selected path. Frontmatter values are extracted from CSS, not a new palette proposal.

### Primary

- **Warm lime (`accent`)** links the selected aircraft, callsign, stand, proposed route, primary replay/run action and focus outline. `accent-hover` is the lighter fine-pointer button hover; `action-ink` supplies its dark text.

### Secondary

- **Muted mint (`mint`)** marks accepted decisions, pass evidence and the locally reviewed state.
- **Warm amber (`amber`)** marks counteroffers, restrictions and escalation. Initial guidance is amber and dashed. Fallback retains its explicit outcome label.
- **Soft rose (`rose`)** marks rejection, failed checks and unavailable runway state. Status pairs words and an icon with color.

### Neutral

- **Desk charcoal (`background`)** grounds the application and desktop review footer; **map charcoal (`map`)** is the clipped spatial field.
- **Off-white (`text`)**, **muted green-grey (`muted`)** and **quiet green-grey (`quiet`)** separate primary reading, supporting labels and peripheral cues.
- **Ruled green-grey (`line`)** divides regions and rows; **grid green-grey (`map-grid`)** draws the map grid.
- **Raised surface** groups settings; **review surface** and **selected surface** identify the review action and selected traffic row. **Agreement surface** supports the normal stage; **escalation surface** warms the stage on refusal/input error.
- Airport geometry stays behind guidance: subdued aprons/taxiways/terminals, wider runway shoulders, dashed centerlines and labelled construction outlines. Local geometry colors remain in CSS rather than becoming extra brand accents.

**The Evidence Color Rule.** Color alone never establishes agreement, validity or live status. Preserve the displayed outcome, verdict, provenance and applied-check wording.

## Typography

**Display and Body Font:** IBM Plex Sans, with sans-serif fallback.
**Label/Mono Font:** IBM Plex Mono, with monospace fallback, for flight identities, airport codes, plan IDs, simulation times, stand IDs and numeric outcomes.

The pairing is compact and technical without becoming a terminal. There is no hero/display scale. Fontsource loads Sans weights 400/500/600 and Mono 400; CSS disables font synthesis and specifies 500 for some mono identities. Preserve these family roles rather than adding a decorative face.

### Hierarchy

- **Headline:** airport-surface heading uses the frontmatter role; it becomes (16px) at the narrowest breakpoint.
- **Title:** coordination heading/stage uses the title role; the coordination heading has tracking (-.15px).
- **Body:** agent reasons use the body role and indent beneath the role name. Stacked layouts increase them to (13px), limited to (68ch).
- **Label:** supporting desktop metadata/status type is commonly (9–11px); narrow map attribution is (7px). These are observed densities, not an assertion that every label meets an accessibility target.
- **Flight and measurement:** mono roles support identities/results; playback uses (10px) and small plan/stand labels use (9px) or less.
- **Brand:** lowercase Sans wordmark (22px, weight 500, -.7px tracking), lime period and a skewed three-stroke mark; the wordmark becomes (21px) on narrow screens.

## Layout

The centered application has maximum width (1920px), minimum body width (360px), header height (64px) and conditions band minimum height (71px). Desktop uses a flexible map column and coordination column (376px), gap (24px), workspace padding (20px 30px), height `calc(100dvh - 239px)` and minimum height (660px). The right panel has a dividing rule, scrollable evidence area and nonshrinking review footer. Expanded evidence scrolls inside that desktop panel.

The map flexes with minimum height (360px); heading, playback and three adjacent traffic selectors frame it. Header, conditions, toolbar and disclosure share page gutters. Spacing tokens capture recurring steps; local insets remain in CSS.

| Viewport rule | Implemented change |
|---|---|
| At least 1600px | Coordination column (410px), gap (30px), workspace padding (24px 36px), shared gutters (36px). |
| At most 1240px | Column (352px), gap (18px), workspace padding (18px 22px). Hide surface tab, “International”, traffic phase labels and agent chevrons; compact supporting type. |
| At most 980px | Stack map/traffic before coordination and use page scrolling. Conditions become two columns. Map minimum (480px), surface workspace minimum (680px). Panel rule moves to the top; internal evidence scrolling ends. Header record action hides; labelled **Decision record** appears in the panel footer before human review. |
| At most 560px | Header (60px), gutters (16px), map minimum (450px), surface workspace minimum (650px). Flight overlay width (230px). Map control targets (36×38px). Traffic remains three across with wrapped contents. Toolbar wraps with a full-width action row; primary trailing arrow and playback caption hide. |

The stacked evidence entry stays in document flow. It opens the same inline record and scrolls it into view. On-map source credit remains at every size; only the additional bottom-disclosure attribution link hides below (980px).

## Elevation & Depth

There are **no CSS box shadows**. Tonal differences, thin borders, dividing rules, clipping and placement convey depth. Settings, selected-flight summary and hover/focus tooltip are solid opaque overlays. No glass or backdrop blur is used. The proposed route's SVG Gaussian blur (standard deviation 3, wide stroke at opacity .2) illuminates guidance, not panel elevation.

**The Flat Surface Rule.** Keep panels opaque and ruled; reserve glow for the selected proposed route.

## Shapes

The map/settings use `surface` corners, flight overlay `flight`, tooltip `tooltip`, stage `stage`, and smaller controls/selected traffic `control` or `action`. Plan tags use `tag`. Most rows remain square and ruled. Dots/range rings are circular; stands are small softened square markers. Interface SVGs use thin strokes (1.6); aircraft use a filled plan-view silhouette, dashed selection ring and small selection dot.

## Components

### Buttons and fields

The lime primary action starts replay or a backend run according to the chosen source. Its minimum height is (40px); narrow padding is (11px 12px). Disabled primary opacity is (.7); other disabled buttons use (.45). The full-width human-review action is dark green with a fine border, becomes mint with “Reviewed in this draft”, and is disabled during replay/waiting, refusal/input error and after review. It changes local UI state only; the footer states that no airport instructions are sent.

Text actions are quiet at rest, lime when active and off-white on fine-pointer hover. Native selects control source, scenario and speed; this surface has no text-entry form. The source field sits in the solid settings disclosure. The native timeline range is lime-accented. Buttons, links, summaries, selects and inputs use a lime keyboard outline (2px, offset 4px). Fine-pointer hover changes color/background without lifting or scaling controls.

### Header and conditions

The header provides brand/home, DFW context, current surface, session-source badge, desktop record action and settings. “Recorded demo”, “Backend · live models” and “Backend · scripted” identify coordination sources, never live aircraft tracking. Conditions show historical delay and scenario route/runway/ground fields, with a desktop “Not live telemetry” note.

### Airport map, selected aircraft and traffic

The SVG world uses a viewBox (1000×760), static grid/range rings, attributed real DFW geometry, north marker and approximate scale. T2's restriction is a labelled scenario overlay. G1/G2 are simulation stands rather than real DFW gate IDs. Geographic placement, approaches and routes are illustrative presentation overlays; the protocol supplies no geographic clearance or observed aircraft track.

Selection joins the map, flight summary and traffic row. Click or Enter/Space on the focusable SVG target selects an aircraft; traffic buttons provide the same choice with `aria-pressed`. Hover/focus shows a constrained tooltip with identity, movement phase, landing time and simulation stand. The persistent summary exposes selected details for click/touch. Aircraft icons/labels counter-scale to retain screen size while the world zooms. Zoom spans (.85×–2.4×) in (.2) steps; pointer drag pans within bounded offsets; reset restores the initial view; the eye toggles guidance.

Initial guidance is amber/dashed. Revised guidance is lime with a soft glow, dashed approach and outlined waypoints. Waiting makes prior guidance grey/dashed with “Previous recommendation”. Escalation/input error removes guidance and selected-stand emphasis and shows “No validated route”. Existing aircraft positions/initial assignments remain as context, not a validated recommendation.

### Playback and motion

One simulation clock starts at (T+09:24) and ends at (T+40:00), with pause/play, scrub step (.05min) and (10×/20×/40×) speeds; default (20×). Linear distance interpolation and segment heading drive approach/taxi motion. Aircraft queue until eight simulated minutes before landing, approach, taxi for the route duration and stop at the stand. At `gate_out_min`, the traffic/summary phase becomes “Turn complete” and the map track/tooltip retires (`visible: false`), freeing the stand visually for a later assignment. No departure route or motion is invented.

`requestAnimationFrame` updates SVG transforms directly; clock text refreshes roughly every (120ms). There is no decorative sweep/pulse or easing on constant movement. UI color/border transitions use (160ms), `cubic-bezier(.23,1,.32,1)`. Reduced-motion preference is read on mount: aircraft start paused, replay does not automatically restart them, record scrolling is instant and CSS transitions use (0ms). Users can still choose playback. Playback/scrubbing disable during coordination replay, backend waiting and terminal refusal.

### Independent agent reviews and checks

ATC, Pilot and Ground each have a ruled row with role icon, responsibility, verdict icon/word and original stated reason. Verdicts read “Accepted”, “Counteroffer” and “Rejected”. Expanded rows show grouped deterministic checks for the displayed plan; nested disclosures show observed/required text and affected flights. Groups read “Pass”, “Not met” or “Unknown”. Preserve fuel, turbulence, connections, crew and turnaround responsibilities even when collapsed. These are stated reasons and rule evidence, not private chain-of-thought.

### Coordination, replay and terminal states

The stage combines icon, headline, explanation and a three-step tracker. Replay moves through “Initial plan”, “Checking constraints”, “Counteroffers exchanged”, “Revised plan proposed”, “Confirming agreement”, then the recorded outcome. Presentation phases occur at (0/.6/2/3.8/5.1/7.7s); second-round replies reveal at (5.65/6.35/7s). These are explanatory timings over stored backend events, not measured model latency. Counts separate rounds, agent reviews and model calls; do not equate rounds with the source's unresolved “under 3 turns”.

| State | Visible treatment and interaction |
|---|---|
| Backend waiting | “Coordination in progress” / “Waiting for the completed run”; every role says “Awaiting result”. Prior checks say “Previous run’s checks”. Motion pauses, prior recommendation stays visible, and no per-agent live progress is invented. |
| CONSENSUS | “Agreement reached”, shield/check and “All three agents accepted the same plan”. Selected metrics appear; local qualified-person review is available. |
| FALLBACK | “Checked fallback” / “A checked plan is available without consensus”; tracker ends “Fallback”. Actual verdicts remain. Selected plan/review stay available; the normal green stage does not establish agreement. |
| ESCALATED | Warm stage/warning, “Controller review needed”, tracker “Escalation”. Guidance/metrics hide; review/playback disable; explanation states no catalog candidate passed every operational constraint. |
| INPUT_ERROR | Warm refusal treatment with distinct “Scenario needs attention” and an input-correction message/banner. Original outcome/reason remain in the record. |
| Loading / service error | Centered “Loading DFW surface” with `aria-busy`; initial failure has alert/reload. Later errors use a dismissible warm banner. Backend requests abort after (45s) with an explicit timeout message. |

### Alternatives, decision record and human review

“Why this plan?” uses compact delay, connections and overtime metrics. Alternatives expose “Feasible” or “Ruled out” plus actual check/comparison summaries. Expanded alternatives show observed/required evidence without a new explanation model.

The inline record lists source row, original outcome/reason, simulated scope and attempts/retries; export downloads original bundle JSON. Desktop opens it from the header. At (980px) and below, labelled **Decision record** stays above “Mark recommendation reviewed”; this is the repaired mobile evidence entry point. Opening scrolls to the record; its close icon collapses it. The toolbar offers original, crew-delay and no-runway recorded drills plus replay/run. Bottom disclosure retains “INTERACTIVE REVIEW DRAFT” and identifies scripted replay or connected results.

## Do's and Don'ts

### Do:

- **Do** let real airport geometry and the selected aircraft lead the review surface.
- **Do** preserve lime selection/focus, text-plus-icon statuses and the quiet ruled hierarchy.
- **Do** retain map attribution and historical, simulated, recorded and connected-source labels at responsive sizes.
- **Do** keep mobile Decision record access visible before the local human-review action.
- **Do** render original agent reasons, applied checks and backend outcomes without manufacturing progress.
- **Do** use simulation time, stop aircraft at the assigned stand and retire the map track when occupancy ends.

### Don't:

- **Don't** add decorative gradients, glass, oversized metric tiles, generic card grids, fake chat bubbles or process jargon to this radar direction.
- **Don't** label fallback as consensus or refusal as a validated route.
- **Don't** describe static history, illustrative motion or scripted replay as live telemetry or measured model performance.
- **Don't** turn simulation stands/geographic overlays into real gate IDs, routing clearances or airport instructions.
- **Don't** hide evidence access when desktop navigation collapses.
- **Don't** replace the user-selected code-first review draft with a new identity or unapproved raster comp.
