"""Local development backend API; run with uvicorn api:app --host 127.0.0.1.

Synchronous request/async work: POST waits for the bounded run to finish. Results
and JSONL evidence persist across server restarts. No frontend or operational
execution. Mode is server-side configuration, never a client-controlled API key.
"""
import asyncio
import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app import default_agents
from contracts.models import ScenarioInput
from runtime.catalog import explain_comparison
from runtime.coordinator import run_negotiation
from runtime.model_gateway import gateway_from_environment
from runtime.models import RunResult
from runtime.scenario_loader import EXAMPLE


def create_app(*, model=None, agents=None, log_dir=Path("logs")):
    server = FastAPI(title="Autonomous SG coordinator", version="1.0")
    directory = Path(log_dir)
    # Serialize runs on this demo server to avoid multiplying the provider budget.
    run_lock = asyncio.Lock()

    def result_path(run_id):
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise HTTPException(404, "Unknown run")
        path = directory / f"{run_id}.result.json"
        if not path.is_file():
            raise HTTPException(404, "Unknown or unfinished run")
        return path

    def read_result(run_id):
        return RunResult.model_validate_json(result_path(run_id).read_text(encoding="utf-8"))

    @server.get("/health")
    async def health():
        return {"status": "ok", "protocol_version": "1.0",
                "mode": getattr(model, "mode", os.environ.get("COORDINATOR_MODE", "offline"))}

    @server.get("/scenarios/example", response_model=ScenarioInput)
    async def example():
        return ScenarioInput.model_validate_json(EXAMPLE.read_bytes())

    @server.post("/runs", response_model=RunResult)
    async def run(scenario: ScenarioInput):
        try:
            gateway = model or gateway_from_environment(os.environ.get("COORDINATOR_MODE", "offline"))
        except ValueError:
            raise HTTPException(503, "Live gateway is not configured")
        if run_lock.locked():
            raise HTTPException(409, "Another run is active; retry after it finishes")
        async with run_lock:
            return await run_negotiation(scenario, agents or default_agents(), gateway, log_dir=directory)

    @server.get("/runs/{run_id}", response_model=RunResult)
    async def get_run(run_id: str):
        return read_result(run_id)

    @server.get("/runs/{run_id}/events")
    async def get_events(run_id: str):
        result_path(run_id)
        return [json.loads(line) for line in (directory / f"{run_id}.jsonl").read_text(encoding="utf-8").splitlines()]

    @server.get("/runs/{run_id}/evidence")
    async def get_evidence(run_id: str):
        result_path(run_id)
        return FileResponse(directory / f"{run_id}.jsonl", media_type="application/x-ndjson", filename=f"{run_id}.jsonl")

    @server.get("/runs/{run_id}/why/{other_plan_id}")
    async def why(run_id: str, other_plan_id: str):
        result = read_result(run_id)
        if result.selected_plan is None:
            raise HTTPException(409, "Run has no selected plan")
        events = [json.loads(line) for line in (directory / f"{run_id}.jsonl").read_text(encoding="utf-8").splitlines()]
        original = next(e["payload"]["scenario"] for e in events if e["type"] == "INPUT_VALIDATED")
        scenario = ScenarioInput.model_validate(original)
        other = next((p for p in scenario.plans if p.plan_id == other_plan_id), None)
        if other is None:
            raise HTTPException(404, "Plan not in the run's catalog")
        if other.plan_id == result.selected_plan_id:
            return {"reason": "SELECTED_PLAN", "plan_id": other.plan_id}
        return explain_comparison(result.selected_plan, other, result.candidate_reports)

    return server


app = create_app()
