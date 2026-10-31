# Airbus problem statements - normalized track reference

Source: [original PDF](../references/airbus-track.pdf), physical pages 1-6;
Autonomous SG 2026, Acacia Hackathon Society x NUS Product Club, 31 October 2026.
The appended rubric is separately normalized in [judging-rubric.md](judging-rubric.md).

This preserves the challenge outcomes, constraints, numerical details and named
datasets in readable form. It is not a verbatim typesetting transcription.
Statements attributed to the brief are not independently validated aviation or
market facts. Challenge #2 is the current project focus; other challenges are
reference material and must not silently expand its requirements.

The brief's dataset reference is
[the organizer Drive folder](https://drive.google.com/drive/u/1/folders/13h0JZnSqhYTX3rV8dGDGy5AiwaADQvJR).
Its availability/current contents were not verified. The supplied local files
are independently identified by hashes in [the source register](source-register.md).

## Challenge #1 - satellite collision avoidance (pages 1-2)

Use AI-driven technology to evaluate satellite/debris conjunction telemetry,
estimate collision probability Pc, and flag events needing maneuver planning.
The brief describes crowded LEO and too many encounter warnings for manual review.

Requested outputs: risk classification backed by probability; trajectories,
risk scores and miss distances in a dashboard; warnings and insights for events
inside the specified dangerous distance within a 24-hour frame.

The brief references the NASA Spacecraft Conjunction Assessment and Collision
Avoidance Best Practices Handbook, NASA/SP-20205011318, and ESA Space Debris
Office Standards. Treat the following as the brief's stated classification rules:

| Tier | Condition stated in the brief |
|---|---|
| Safe | Pc < 10^-6 AND miss distance > 5.0 km |
| Elevated | 10^-6 <= Pc < 10^-4 OR miss distance between 1.0 and 5.0 km |
| Critical / maneuver required | Pc >= 10^-4 (dataset risk >= -4.0) OR miss distance < 1.0 km |

The conditions overlap; precedence and endpoint handling are not fully specified.
Do not silently claim a complete, mutually exclusive operational policy.

Data: `Challenge #1/archive(1).zip`, containing `train_data` and `test_data`.
Train using telemetry relationships; predict unseen test encounters. `risk`
represents log10(Pc), to map to operational tiers. The allowed simplification
lists `event_id`, `time_to_tca`, `miss_distance`, `relative_speed`,
`relative_position_r`, `relative_position_t`, `relative_position_n`,
`c_object_type`, `c_sigma_r`, `t_sigma_r`, `max_risk_estimate`, `F10`, `AP`.
This dataset was not provided/inspected in this project snapshot.

## Challenge #2 - ATC, pilot and ground decisions (pages 2-3)

Help these operational roles coordinate faster when runway closures, weather
delays or equipment failures disrupt operations. Build independent agents that
exchange structured data, check cross-domain constraints and reach traceable
agreement with deterministic fallback.

All responsibilities, exclusions, exact delay thresholds and the under-three-turn
condition are maintained in [the canonical C2 requirements](challenge-2-requirements.md).
Data is described as 2015 US Department of Transportation delay/cancellation
data in `Challenge #2/DATA`. The supplied three CSVs are inspected in
[datasets.md](datasets.md).

## Challenge #3 - SAF supply chain in Kalimantan (pages 3-4)

Optimize sustainable aviation fuel logistics from agricultural/forestry residues
through depots and refineries to four airports. Minimize total OpEx + CapEx +
logistics while meeting demand. Output depot/refinery coordinates, facility sizes,
material flows and routing from farms to depots to refineries to airports.

| Facility | Size | Cost (USD) | Capacity as labelled in brief |
|---|---|---:|---:|
| Depot | Small | 2.25 million | 150 kt |
| Depot | Large | 4.5 million | 300 kt |
| Refinery | Small | 480 million | 500 kt |
| Refinery | Large | 765 million | 1,087 kt |

| Truck size | Farm to depot | Cost USD/tonne/km | Depot to refinery | Cost USD/tonne/km | Refinery to airport | Cost USD/tonne/km |
|---|---:|---:|---:|---:|---:|---:|
| Small | 3 t | 0.10 | 18 t | 0.12 | 16 t | 0.08 |
| Large | 9 t | 0.10 | 30 t | 0.12 | 32 t | 0.08 |

Feedstock: 6,800 kt across 80 biomass locations, each described as 20-100 kt.
Only these airports: Supadio Intl; Iskandar Intl; Sultan Aji Muhammad Sulaiman
Sepinggan Intl; Juwata Intl.

Data paths: `Challenge #3 - SAF/Airport location/airport.dat` (the prose also
mentions `data/airports.dat`) and
`Challenge #3 - SAF/Biomass locations/kalimantan_80_locations_6800kt_full_range.csv`.
These were not supplied/inspected. Demand quantities, conversion yields,
capacity time basis, capital annualization and road-network assumptions are
not specified in the visible brief. Do not infer them from this table.

## Challenge #4 - trusted technical information (pages 4-5)

Build traceable, context-aware search over multi-page regulated technical
documents such as airworthiness directives, maintenance manuals and accident
reports. Parse exact applicability rules and answer natural-language questions
with citations; refuse when evidence is ambiguous or insufficient.

- Every claim/sentence links to exact source metadata.
- The source demands zero hallucinated responses.
- Methodically evaluate conditional applicability, including serial-number ranges.
- Surface multiple document versions and which version is latest.
- Clearly express inability for out-of-scope, contradictory or ambiguous questions.
- Achieve sub-three-second retrieval across 1,000+ pages.
- Return structured information; avoid unformatted free text and filling gaps
  from pretrained model memory.

Data: `Challenge #4/432 entries of FAA Airworthiness Directives`, not supplied or
inspected here. A universal zero-hallucination claim is not established by a
small test; source aspiration and measured evidence must remain distinct.

## Challenge #5 - predictive airport capacity and delay risk (pages 5-6)

Use historical weather observations/forecasts (METAR/TAF, NOAA storm logs) and
flight performance to forecast hourly runway Arrival Acceptance Rate (AAR) and
departure-delay risk 3-12 hours before severe weather.

The brief attributes more than 70% of global air traffic delays to severe
weather; this contextual percentage is an unverified source claim here.

Required outputs/methods:

- Join weather and flight records by timestamps and airport station identifiers.
- Predict AAR and evaluate with Root Mean Squared Error.
- Classify severe flight-delay risk using delay > 45 minutes.
- Provide an interactive ATC dashboard with risk, historical trends and recommendations.
- Automatically download/process public datasets.
- Avoid future/arrival-time weather leakage into earlier forecasts.
- Compute crosswind/tailwind relative to runway direction; do not use raw wind
  speed alone.
- Design a generalized pipeline accepting dataset airport ICAO codes; avoid
  overfitting a single airport.
- Normalize delay comparisons for airport flight volume.

Provided data is described as airport weather for 2023-2025, including temperature,
precipitation, wind speed/gusts, pressure, snow depth and weather-condition nodes:
`Challenge #5/Flight_Data_With_Weather_Final.csv`.

Select only ATL (Atlanta Hartsfield-Jackson) and DFW (Dallas Fort Worth), for
departures and arrivals. The brief's simplifying runway headings are 80 degrees
for ATL and 180 degrees for DFW. This file was not supplied/inspected. These
headings and forecast requirements do not apply to Challenge #2.
