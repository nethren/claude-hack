# Inspected dataset contract

Snapshot: 2026-10-31, Asia/Singapore. Facts below were computed from the complete
user-supplied CSVs committed under data/raw. Hashes and exact machine-readable
profiles are in [the source register](source-register.md). This document must be
read before brainstorming or architecture decisions involving data.

## Inventory and actual availability

| ID | File | Rows excluding header | Columns | Purpose |
|---|---|---:|---:|---|
| DS-01 | [airlines.csv](../data/raw/airlines.csv) | 14 | 2 | Historical code/name lookup |
| DS-02 | [airports.csv](../data/raw/airports.csv) | 322 | 7 | Airport names, geography and coordinates |
| DS-03 | [flights.csv](../data/raw/flights.csv) | 358,774 | 31 | Historical disruption rows for agent scenario seeding |

The required flight file is now supplied and inspected; it is no longer a missing
input. Do not continue to describe only the two lookup tables as the available data.

## DS-01 - airlines

| Column | Meaning | Observed quality |
|---|---|---|
| IATA_CODE | Airline identifier, two-character source code | 14 distinct keys; no missing/duplicate keys |
| AIRLINE | Historical source airline name | No missing names |

359 bytes; no duplicate complete rows. Keep source-era labels; this is not a
current list of operating airlines. Full [Markdown lookup](data/airlines.md).

## DS-02 - airports

| Column | Meaning | Observed quality |
|---|---|---|
| IATA_CODE | Airport identifier, three-character source code | 322 distinct keys; no missing/duplicate keys |
| AIRPORT | Source airport name | No missing values |
| CITY | Source city label | No missing values |
| STATE | US state/territory-style source code | No missing values; do not assume only 50 values |
| COUNTRY | Source country label | All rows say USA |
| LATITUDE | Latitude in decimal degrees | 3 missing values; present values within -90 to 90 |
| LONGITUDE | Longitude in decimal degrees | 3 missing values; present values within -180 to 180 |

23,867 bytes; no duplicate complete rows. Both coordinates are missing for ECP,
PBG and UST. Preserve missing coordinates as null/unknown; never substitute 0,0.
These airports may still participate in non-map scenarios. Names include original
Unicode whitespace; do not silently rewrite raw data. Full
[Markdown lookup](data/airports.md).

This table supplies no runway orientation, runway geometry, taxiways, gates,
timezone, ICAO mapping, gate compatibility or weather station mapping.

## DS-03 - flights: observed full-file profile

- Size: 38,616,129 bytes; 358,774 data rows and 31 columns.
- Calendar span: 2015-01-01 through 2015-12-31.
- Present months: January-September, November and December. **October is absent.**
- 14 distinct airline codes, 322 distinct origin codes and 320 distinct
  destination codes. Every observed code matches its supplied lookup.
- Every row satisfies WEATHER_DELAY > 15 OR LATE_AIRCRAFT_DELAY > 20.
- 42,012 rows have WEATHER_DELAY > 15; 326,249 have LATE_AIRCRAFT_DELAY > 20;
  9,487 satisfy both (inclusive counts overlap).
- Weather-only eligible rows: 32,525. Late-aircraft-only eligible rows: 316,762.
- All CANCELLED and DIVERTED flags are 0. CANCELLATION_REASON is blank in every row.
- No other empty cells were found. All records have the expected column count.
- WEATHER_DELAY, LATE_AIRCRAFT_DELAY, ARRIVAL_DELAY and DEPARTURE_DELAY parsed
  as finite numeric values in every row.
- Ranges in minutes: weather delay 0-1,211; late-aircraft delay 0-1,331;
  arrival delay 16-1,598; departure delay -22 to 1,609.
- Complete-row duplication, flight-key uniqueness, all clock/calendar semantics,
  and causal attribution consistency were not comprehensively validated.

These observations are consistent with prior filtering; the actual transformation
history is not provided. Do not call this the complete 2015 flight universe or
claim that the missing month is an extraction error. The filename alone does not
establish upstream completeness.

### All 31 fields

Meanings below normalize standard BTS conventions to the supplied uppercase
headers. The actual headers, values and missingness are directly inspected.
The [BTS field reference](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ)
supports local-clock, delay-minute and distance-mile conventions. No explicit
timezone/UTC offset is included in these files; schema descriptions are not a
claim that every historical clock value is validated.

| Field | Meaning / role | Representation / unit | Empty cells |
|---|---|---|---:|
| YEAR | Flight calendar year | integer year | 0 |
| MONTH | Flight calendar month | integer 1-12 | 0 |
| DAY | Day of month | integer calendar day | 0 |
| DAY_OF_WEEK | Day-of-week code, conventional Monday=1 through Sunday=7 | integer code; validate calendar consistency before relying on it | 0 |
| AIRLINE | Historical airline identifier; joins to airlines.IATA_CODE | string code | 0 |
| FLIGHT_NUMBER | Carrier flight number; not globally unique | identifier; preserve as string if needed | 0 |
| TAIL_NUMBER | Aircraft registration identifier; does not specify type or wake class | string identifier | 0 |
| ORIGIN_AIRPORT | Origin airport code; joins to airports.IATA_CODE | string code | 0 |
| DESTINATION_AIRPORT | Destination airport code; joins to airports.IATA_CODE | string code | 0 |
| SCHEDULED_DEPARTURE | Scheduled local departure clock | HHMM-style source string | 0 |
| DEPARTURE_TIME | Actual local departure clock | HHMM-style source string | 0 |
| DEPARTURE_DELAY | Departure delay; negative values can occur | numeric minutes | 0 |
| TAXI_OUT | Taxi-out duration | numeric minutes | 0 |
| WHEELS_OFF | Actual local wheels-off clock | HHMM-style source string | 0 |
| SCHEDULED_TIME | Scheduled elapsed flight duration | numeric minutes | 0 |
| ELAPSED_TIME | Actual elapsed flight duration | numeric minutes | 0 |
| AIR_TIME | Time airborne | numeric minutes | 0 |
| DISTANCE | Route distance | numeric miles under BTS convention | 0 |
| WHEELS_ON | Actual local wheels-on clock | HHMM-style source string | 0 |
| TAXI_IN | Taxi-in duration | numeric minutes | 0 |
| SCHEDULED_ARRIVAL | Scheduled local arrival clock; do not equate it to a runway slot | HHMM-style source string | 0 |
| ARRIVAL_TIME | Actual local arrival clock | HHMM-style source string | 0 |
| ARRIVAL_DELAY | Arrival delay | numeric minutes | 0 |
| DIVERTED | Diversion indicator | 0/1 source flag | 0 |
| CANCELLED | Cancellation indicator | 0/1 source flag | 0 |
| CANCELLATION_REASON | Cancellation reason code when supplied; entirely empty in this file | nullable source string | 358,774 |
| AIR_SYSTEM_DELAY | Delay attributed to the air system | numeric minutes | 0 |
| SECURITY_DELAY | Delay attributed to security | numeric minutes | 0 |
| AIRLINE_DELAY | Delay attributed to the airline | numeric minutes | 0 |
| LATE_AIRCRAFT_DELAY | Delay attributed to late-arriving aircraft; C2-20 threshold >20 | numeric minutes | 0 |
| WEATHER_DELAY | Delay attributed to weather; C2-20 threshold >15 | numeric minutes | 0 |

### Monthly coverage

| Month (2015) | Rows |
|---|---:|
| 01 | 34,136 |
| 02 | 34,585 |
| 03 | 32,451 |
| 04 | 27,198 |
| 05 | 32,684 |
| 06 | 44,751 |
| 07 | 41,261 |
| 08 | 34,378 |
| 09 | 18,705 |
| 10 | 0 |
| 11 | 22,422 |
| 12 | 36,203 |

## Scenario selection and joins

Use numeric comparisons with the strict OR from C2-20:

```python
eligible = (weather_delay > 15) or (late_aircraft_delay > 20)
```

Every supplied row currently qualifies. Retain this predicate so replacement data
is still checked; do not remove validation because this snapshot is prequalified.
Values equal to 15 or 20 do not pass their respective comparisons. There are 389
rows with weather delay exactly 15 and 196 with late-aircraft delay exactly 20;
the other predicate makes these rows eligible. Reject or explicitly mark unknown
missing/non-numeric values rather than changing raw source values.

| Relationship | Join key | Expected relationship | Observed orphan codes |
|---|---|---|---:|
| Flight to airline label | flights.AIRLINE -> airlines.IATA_CODE | Many flights to one lookup row | 0 |
| Flight to origin | flights.ORIGIN_AIRPORT -> airports.IATA_CODE | Many flights to one lookup row | 0 |
| Flight to destination | flights.DESTINATION_AIRPORT -> airports.IATA_CODE | Many flights to one lookup row | 0 |

Use explicit origin/destination aliases to avoid overwriting one airport's fields
with the other. Preserve codes as strings and report unmatched keys on new data.
Do not join carrier AIRLINE to the lookup AIRLINE name column.

For C2-21, provide all agents with a traceable envelope containing source filename
and hash, source row number, original row parameters and the predicate result.
Each agent may receive additional relevant domain state. Keep that overlay separate
from the raw row. [Complete real example rows](data/flight-scenarios.md) are provided
for weather-only, late-aircraft-only and dual-cause cases.

## Clock and identity cautions

- Keep HHMM-like clock values as source strings, including leading zeroes. Validate
  hour/minute ranges and handle any special 2400 representation explicitly when
  encountered; no global validity claim is made by this documentation.
- Origin and destination clocks are local. Calendar date plus HHMM does not
  establish a UTC instant or arrival-day rollover. Timezones are not in airports.csv.
- Scheduled arrival is not automatically a runway-arrival slot. Account for
  taxi/elapsed-time assumptions explicitly if constructing runway proposals.
- Historical WEATHER_DELAY is attributed past delay, not a current weather
  forecast or remaining airborne holding allowance.
- TAIL_NUMBER is not aircraft type, wake category, fuel quantity or fuel burn.
- FLIGHT_NUMBER alone is not a stable unique row identifier. Keep the source hash
  plus row number; document a separate scenario/flight ID if needed.
- These rows span many days and airports. They do not represent one simultaneous
  airport traffic snapshot. Additional traffic must be selected consistently or
  introduced as labelled scenario state.

## Missing operational inputs and affected responsibilities

| Needed input | Responsibility / requirement | Status in supplied CSVs | Decision implication |
|---|---|---|---|
| Wake classes and minimum separation | C2-09 | Absent | Supply documented scenario classes/rules; do not infer from tail number |
| Taxiway topology and blocked segments | C2-10 | Absent | Label a scenario network/blockage |
| Sector demand, slots and capacity | C2-11 | Absent as current state | Define horizon and traffic assumptions |
| Fuel on board, reserve, consumption and holding budget | C2-12, C2-13 | Absent | Use declared limits/model; do not claim measured fuel savings |
| Turbulence exposure or forecast | C2-14 | Absent | Supply labelled route/slot exposure or record an unresolved coverage gap |
| Passenger itineraries and connection deadlines | C2-15 | Absent | Supply labelled passenger/transfer assumptions |
| Gate occupancy, compatibility and availability | C2-16 | Absent | Use labelled gate state and no-overlap rules |
| Crew shifts, staffing and overtime | C2-17 | Absent | Supply labelled staffing/shift model |
| Turnaround readiness and minimum service duration | C2-18 | Absent | Do not equate taxi-in/out with turnaround |

These gaps do not make the brief impossible: the provided row can seed a replay,
with explicitly labelled operational overlays. They do prevent claiming that all
constraint inputs or benefits were observed in the flight dataset.

## What this file can and cannot establish

Supported: real source identities/timings/delay causes for a disruption seed;
lookup enrichment; strict row eligibility; historical scenario provenance.

Not established: live telemetry, actual runway/gate allocations, available fuel,
weather forecasts, full scheduled traffic, passenger impacts, causal improvements,
or representative prevalence of delay/cancellation/diversion. All rows qualify,
so this subset cannot by itself evaluate a delayed-vs-normal classifier or
estimate general airport delay probability. Do not add ML training solely because
a teammate has ML experience; it is not required by Challenge #2.

## Updating data

Keep raw sources unchanged. On explicit selection of replacement data, update
[source manifest](../references/source-manifest.json),
[dataset profile](../references/dataset-profile.json), this contract, complete
lookup Markdown tables and selected-row examples together. Recheck eligibility,
keys, missingness and temporal coverage before using the replacement in decisions.
Run `python3 scripts/check_alignment.py` from the project root.
