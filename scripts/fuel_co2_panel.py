"""Print the fuel & CO2 panel (MODELLED ESTIMATE, not measured fuel).

  .venv/Scripts/python scripts/fuel_co2_panel.py                 # example scenario catalog
  .venv/Scripts/python scripts/fuel_co2_panel.py --plan P1       # highlight one plan
  .venv/Scripts/python scripts/fuel_co2_panel.py --run-id <id>   # a finished coordinator run
  ... --json                                                     # machine-readable panel

Read-only: it never runs a negotiation or changes scenarios, logs or results.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.fuel_co2 import (RunNotFound, build_panel, hard_check_results,  # noqa: E402
                               panel_for_run, render_text)
from contracts.models import ScenarioInput  # noqa: E402
from runtime.scenario_loader import EXAMPLE  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario", type=Path, default=EXAMPLE)
    parser.add_argument("--run-id", help="finished coordinator run in --log-dir")
    parser.add_argument("--log-dir", type=Path, default=ROOT / "logs")
    parser.add_argument("--plan", help="plan to highlight (default: the run's selected plan)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.run_id:
        try:
            panel, selected = panel_for_run(args.log_dir, args.run_id)
        except RunNotFound as exc:
            parser.error(str(exc))
        highlight = args.plan or selected
    else:
        s = ScenarioInput.model_validate_json(args.scenario.read_bytes())
        panel, highlight = build_panel(s, hard_pass=hard_check_results(s)), args.plan

    print(panel.model_dump_json(indent=2) if args.json else render_text(panel, highlight=highlight))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
