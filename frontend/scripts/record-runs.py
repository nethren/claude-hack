"""Record one coordinator run per demo scenario for the hosted static build.

Start the backend first (python -m dev.serve, or --live for Claude agents), then
from the repository root run:

    python frontend/scripts/record-runs.py [--backend http://127.0.0.1:8000]

Each file in frontend/public/data/runs/ holds the scenario, the coordinator's
result, its event log and the fuel/CO2 panel exactly as the API returned them,
plus the backend mode and the time recorded. The hosted site replays these
files; it never calls an agent or holds an API key.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

SCENARIOS = ("clear", "counter", "escalate")
OUT = Path(__file__).resolve().parents[1] / "public" / "data" / "runs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=args.backend, timeout=600) as client:
        mode = client.get("/health").raise_for_status().json()["mode"]
        for sid in SCENARIOS:
            scenario = client.get(f"/scenarios/demo/{sid}").raise_for_status().json()
            result = client.post("/runs", json=scenario).raise_for_status().json()
            run_id = result["run_id"]
            events = client.get(f"/runs/{run_id}/events").raise_for_status().json()
            fuel_response = client.get(f"/runs/{run_id}/fuel-co2")
            fuel = fuel_response.json() if fuel_response.is_success else None
            bundle = {
                "kind": "recorded-run",
                "recorded": {"mode": mode, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                "scenario": scenario, "result": result, "events": events, "fuel": fuel,
            }
            (OUT / f"{sid}.json").write_text(json.dumps(bundle, indent=1) + "\n", encoding="utf-8")
            print(f"{sid}: {result['outcome']} in {result.get('rounds_completed', '?')} rounds, "
                  f"{result.get('model_calls_completed')} model calls ({mode})")


if __name__ == "__main__":
    main()
