"""Backend CLI. Offline is explicit and does not require credentials."""
import argparse
import asyncio
from pathlib import Path

from agents.atc import ATCAgent
from agents.ground import GroundAgent
from agents.pilot import PilotAgent
from runtime.coordinator import run_negotiation
from runtime.model_gateway import gateway_from_environment
from runtime.scenario_loader import EXAMPLE


def default_agents():
    return {"atc": ATCAgent(), "pilot": PilotAgent(), "ground": GroundAgent()}


def main():
    parser = argparse.ArgumentParser(description="Autonomous SG coordination backend")
    parser.add_argument("--scenario", type=Path, default=EXAMPLE)
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    args = parser.parse_args()
    try:
        gateway = gateway_from_environment(args.mode)
    except ValueError as exc:
        parser.error(str(exc))
    result = asyncio.run(run_negotiation(args.scenario, default_agents(), gateway, log_dir=args.log_dir))
    print(result.model_dump_json(indent=2))
    return 0 if result.outcome in ("CONSENSUS", "FALLBACK") else 2


if __name__ == "__main__":
    raise SystemExit(main())
