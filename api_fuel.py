"""Backend API plus the fuel & CO2 panel (MODELLED ESTIMATE, not measured fuel).

Run instead of api:app when the panel is wanted:
    uvicorn api_fuel:app --host 127.0.0.1

Additive: builds the unchanged api.create_app() and only adds read-only routes.
"""
from pathlib import Path

from fastapi import HTTPException

from analysis.fuel_co2 import (FuelCO2Panel, RunNotFound, build_panel,
                               hard_check_results, panel_for_run)
from api import create_app
from contracts.models import ScenarioInput
from runtime.scenario_loader import EXAMPLE


def create_fuel_app(*, model=None, agents=None, log_dir=Path("logs")):
    server = create_app(model=model, agents=agents, log_dir=log_dir)

    @server.get("/scenarios/example/fuel-co2", response_model=FuelCO2Panel)
    async def example_fuel():
        s = ScenarioInput.model_validate_json(EXAMPLE.read_bytes())
        return build_panel(s, hard_pass=hard_check_results(s))

    @server.get("/runs/{run_id}/fuel-co2")
    async def run_fuel(run_id: str):
        try:
            panel, selected = panel_for_run(Path(log_dir), run_id)
        except RunNotFound:
            raise HTTPException(404, "Unknown or unfinished run")
        selected_cmp = next((c for c in panel.comparisons if c.plan_id == selected), None)
        return {"selected_plan_id": selected,
                "headline": selected_cmp.headline if selected_cmp else
                f"Run selected no plan; nothing to compare. ({panel.label}.)",
                "panel": panel.model_dump(mode="json")}

    return server


app = create_fuel_app()
