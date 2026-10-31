# Real flight rows for scenario seeding

Source: [unchanged flights CSV](../../data/raw/flights.csv).
CSV row numbers are 1-based physical record numbers including the header as row 1.
These are deterministic source-order examples, not a representative evaluation set.
They contain historical timings and delay causes, not live telemetry or fuel/gate state.

## Eligibility categories

| Category | Supplied row count |
|---|---:|
| WEATHER_DELAY > 15 only | 32,525 |
| LATE_AIRCRAFT_DELAY > 20 only | 316,762 |
| Both predicates true | 9,487 |

## Complete example records

### weather_only: CSV row 48

| Field | Raw source value |
|---|---|
| YEAR | 2015 |
| MONTH | 1 |
| DAY | 1 |
| DAY_OF_WEEK | 4 |
| AIRLINE | AA |
| FLIGHT_NUMBER | 1057 |
| TAIL_NUMBER | N3ASAA |
| ORIGIN_AIRPORT | DFW |
| DESTINATION_AIRPORT | MIA |
| SCHEDULED_DEPARTURE | 0515 |
| DEPARTURE_TIME | 0703 |
| DEPARTURE_DELAY | 108 |
| TAXI_OUT | 15 |
| WHEELS_OFF | 0718 |
| SCHEDULED_TIME | 161 |
| ELAPSED_TIME | 155 |
| AIR_TIME | 133 |
| DISTANCE | 1121 |
| WHEELS_ON | 1031 |
| TAXI_IN | 7 |
| SCHEDULED_ARRIVAL | 0856 |
| ARRIVAL_TIME | 1038 |
| ARRIVAL_DELAY | 102 |
| DIVERTED | 0 |
| CANCELLED | 0 |
| CANCELLATION_REASON |  |
| AIR_SYSTEM_DELAY | 0 |
| SECURITY_DELAY | 0 |
| AIRLINE_DELAY | 0 |
| LATE_AIRCRAFT_DELAY | 0 |
| WEATHER_DELAY | 102 |

Operational overlays: none supplied for this example. Any gates, fuel limits,
crew shifts, turbulence or connections added later must be labelled separately.

### late_only: CSV row 2

| Field | Raw source value |
|---|---|
| YEAR | 2015 |
| MONTH | 1 |
| DAY | 1 |
| DAY_OF_WEEK | 4 |
| AIRLINE | AA |
| FLIGHT_NUMBER | 5 |
| TAIL_NUMBER | N376AA |
| ORIGIN_AIRPORT | DFW |
| DESTINATION_AIRPORT | HNL |
| SCHEDULED_DEPARTURE | 1305 |
| DEPARTURE_TIME | 1754 |
| DEPARTURE_DELAY | 289 |
| TAXI_OUT | 21 |
| WHEELS_OFF | 1815 |
| SCHEDULED_TIME | 515 |
| ELAPSED_TIME | 526 |
| AIR_TIME | 499 |
| DISTANCE | 3784 |
| WHEELS_ON | 2234 |
| TAXI_IN | 6 |
| SCHEDULED_ARRIVAL | 1740 |
| ARRIVAL_TIME | 2240 |
| ARRIVAL_DELAY | 300 |
| DIVERTED | 0 |
| CANCELLED | 0 |
| CANCELLATION_REASON |  |
| AIR_SYSTEM_DELAY | 11 |
| SECURITY_DELAY | 0 |
| AIRLINE_DELAY | 197 |
| LATE_AIRCRAFT_DELAY | 92 |
| WEATHER_DELAY | 0 |

Operational overlays: none supplied for this example. Any gates, fuel limits,
crew shifts, turbulence or connections added later must be labelled separately.

### both: CSV row 76

| Field | Raw source value |
|---|---|
| YEAR | 2015 |
| MONTH | 1 |
| DAY | 1 |
| DAY_OF_WEEK | 4 |
| AIRLINE | AA |
| FLIGHT_NUMBER | 1344 |
| TAIL_NUMBER | N200AA |
| ORIGIN_AIRPORT | DEN |
| DESTINATION_AIRPORT | DFW |
| SCHEDULED_DEPARTURE | 1735 |
| DEPARTURE_TIME | 1850 |
| DEPARTURE_DELAY | 75 |
| TAXI_OUT | 52 |
| WHEELS_OFF | 1942 |
| SCHEDULED_TIME | 115 |
| ELAPSED_TIME | 159 |
| AIR_TIME | 95 |
| DISTANCE | 641 |
| WHEELS_ON | 2217 |
| TAXI_IN | 12 |
| SCHEDULED_ARRIVAL | 2030 |
| ARRIVAL_TIME | 2229 |
| ARRIVAL_DELAY | 119 |
| DIVERTED | 0 |
| CANCELLED | 0 |
| CANCELLATION_REASON |  |
| AIR_SYSTEM_DELAY | 44 |
| SECURITY_DELAY | 0 |
| AIRLINE_DELAY | 0 |
| LATE_AIRCRAFT_DELAY | 40 |
| WEATHER_DELAY | 35 |

Operational overlays: none supplied for this example. Any gates, fuel limits,
crew shifts, turbulence or connections added later must be labelled separately.

## Boundary cautions

The file contains 389 rows with WEATHER_DELAY exactly 15 and
196 rows with LATE_AIRCRAFT_DELAY exactly 20.
Those equalities do not satisfy the respective strict comparison; these rows
still qualify because the other condition is true. Constructed negative
predicate tests must be labelled synthetic and cannot replace the required
real qualifying row in the demonstration.
