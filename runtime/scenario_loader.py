"""Validate source fidelity and configuration before any model invocation."""
import csv
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from contracts.models import ScenarioInput
from domains.ground import validate_ground_inputs
from domains.pilot import validate_pilot_inputs

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs/examples/coordination-scenario-v1.json"


class InputError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code, self.detail = code, detail
        super().__init__(detail)


def eligible(raw: dict[str, str]) -> bool:
    try:
        weather, late = (Decimal(raw[k]) for k in ("WEATHER_DELAY", "LATE_AIRCRAFT_DELAY"))
        if not weather.is_finite() or not late.is_finite():
            raise ValueError("Delay must be finite")
        return weather > 15 or late > 20
    except (KeyError, InvalidOperation, ValueError) as exc:
        raise InputError("INPUT_SOURCE_MISMATCH", "Missing/nonfinite delay minutes") from exc


def verify_sources(s: ScenarioInput, root: Path = ROOT) -> None:
    manifest = json.loads((root / "references/source-manifest.json").read_text())
    entries = {x["id"]: x for x in manifest["sources"]}
    # Read bytes once so row verification and hash verification share a snapshot.
    import io
    tables = {}
    for name in ("airlines.csv", "airports.csv", "flights.csv"):
        entry = entries[name]
        content = (root / entry["path"]).read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != entry["sha256"]:
            raise InputError("INPUT_SOURCE_MISMATCH", f"Committed {name} hash mismatch")
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        if reader.fieldnames != entry["columns"]:
            raise InputError("INPUT_SOURCE_MISMATCH", f"{name} column mismatch")
        if name == "flights.csv":
            wanted = {r.csv_row_number for r in s.shared.source_rows}
            rows = {}
            for line, row in enumerate(reader, 2):
                if line in wanted:
                    rows[line] = row
                if len(rows) == len(wanted):
                    break
            for source in s.shared.source_rows:
                if (source.dataset_sha256 != digest or
                        rows.get(source.csv_row_number) != source.raw):
                    raise InputError("INPUT_SOURCE_MISMATCH", "Source envelope differs from committed row")
                if not eligible(source.raw):
                    raise InputError("INPUT_ROW_INELIGIBLE", "Need WEATHER_DELAY > 15 OR LATE_AIRCRAFT_DELAY > 20")
        else:
            tables[name] = {row["IATA_CODE"] for row in reader}
    for source in s.shared.source_rows:
        raw = source.raw
        if (raw["AIRLINE"] not in tables["airlines.csv"] or
                any(raw[k] not in tables["airports.csv"] for k in ("ORIGIN_AIRPORT", "DESTINATION_AIRPORT"))):
            raise InputError("INPUT_SOURCE_MISMATCH", "Source lookup join failed")
    if s.shared.airport_iata not in tables["airports.csv"]:
        raise InputError("INPUT_SCHEMA_INVALID", "Scenario airport is not in airport lookup")


def validate_configuration(s: ScenarioInput) -> None:
    from contracts.models import plan_hash
    problems = []

    def unique(label, values):
        if any(not str(x).strip() for x in values) or len(set(values)) != len(values):
            problems.append(f"{label}: identifiers/options must be nonempty and unique")

    fids = {f.flight_id for f in s.shared.flights}
    sources = {r.source_id for r in s.shared.source_rows}
    unique("flights", [f.flight_id for f in s.shared.flights])
    unique("sources", [r.source_id for r in s.shared.source_rows])
    unique("plans", [p.plan_id for p in s.plans])
    if s.initial_plan_id not in {p.plan_id for p in s.plans}:
        problems.append("initial_plan_id must identify a catalog plan")
    if not any(f.identity_origin == "source_csv" for f in s.shared.flights):
        problems.append("At least one flight identity must reference the source CSV")
    for f in s.shared.flights:
        if ((f.identity_origin == "source_csv" and f.source_id not in sources) or
                (f.identity_origin == "simulated" and f.source_id is not None)):
            problems.append(f"flight {f.flight_id}: inconsistent source identity")
        if f.identity_origin == "source_csv" and f.source_id in sources:
            row = next(r for r in s.shared.source_rows if r.source_id == f.source_id)
            if row.raw.get("DESTINATION_AIRPORT") != s.shared.airport_iata:
                problems.append(f"flight {f.flight_id}: source destination must match this arrival airport")
    if not s.shared.simulated_fields:
        problems.append("simulated_fields must label the operational overlay")
    opts = s.shared.options
    for label, mapping in (("landing options", opts.landing_min_by_flight),
                           ("gate-out options", opts.gate_out_min_by_flight)):
        if set(mapping) != fids or any(not v for v in mapping.values()):
            problems.append(f"{label}: require nonempty options for exactly all flights")
        for v in mapping.values():
            unique(label, v)
    unique("routes", [r.route_id for r in s.atc.routes])
    unique("route options", opts.taxi_route_ids)
    unique("gate options", opts.gate_ids)
    routes = {r.route_id: r.taxi_in_min for r in s.atc.routes}
    if (not opts.taxi_route_ids or not opts.gate_ids or
            not set(opts.taxi_route_ids) <= set(routes) or
            routes != s.shared.taxi_in_min_by_route):
        problems.append("Route options and shared/ATC taxi durations must agree")
    if set(s.atc.wake_class_by_flight) != fids:
        problems.append("Wake classes must cover exactly all flights")
    classes = set(s.atc.wake_class_by_flight.values())
    for leader in classes:
        if not classes <= set(s.atc.separation_min.get(leader, {})):
            problems.append(f"Missing wake matrix entries for {leader}")
    windows = list(s.atc.runway_open_windows)
    windows += [w for r in s.atc.routes for w in r.blocked_windows]
    if any(w.start_min >= w.end_min for w in windows):
        problems.append("ATC intervals must have positive length")
    hashes = []
    for p in s.plans:
        ids = [a.flight_id for a in p.assignments]
        if set(ids) != fids or len(ids) != len(fids):
            problems.append(f"{p.plan_id}: exactly one assignment per flight required")
            continue
        hashes.append(plan_hash(p))
        for a in p.assignments:
            if (a.landing_min not in opts.landing_min_by_flight.get(a.flight_id, []) or
                    a.gate_out_min not in opts.gate_out_min_by_flight.get(a.flight_id, []) or
                    a.taxi_route_id not in opts.taxi_route_ids or a.gate_id not in opts.gate_ids):
                problems.append(f"{p.plan_id}/{a.flight_id}: assignment outside declared options")
    if len(set(hashes)) != len(hashes):
        problems.append("Duplicate plan content is not an alternative")
    problems += validate_pilot_inputs(s.shared, s.pilot)
    problems += validate_ground_inputs(s.shared, s.ground)
    if problems:
        raise InputError("INPUT_SCHEMA_INVALID", "; ".join(problems))


def load_scenario(value, *, root: Path = ROOT) -> ScenarioInput:
    try:
        if isinstance(value, Path):
            value = value.read_bytes()
        if isinstance(value, ScenarioInput):
            value = value.model_dump_json()
        s = (ScenarioInput.model_validate_json(value) if isinstance(value, (bytes, str))
             else ScenarioInput.model_validate(value))
        validate_configuration(s)
        verify_sources(s, root)
        return s
    except InputError:
        raise
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise InputError("INPUT_SCHEMA_INVALID", "Invalid scenario schema or unavailable source files") from exc
