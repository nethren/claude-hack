import asyncio
from types import SimpleNamespace

from app import default_agents
from runtime.coordinator import run_negotiation
from runtime.model_gateway import OfflineGateway
from runtime.models import Budgets
from runtime.scenario_loader import EXAMPLE, load_scenario


def test_final_validation_recomputes_instead_of_trusting_cached_passes(tmp_path, monkeypatch):
    import domains.atc
    original = domains.atc.evaluate_atc
    calls = 0
    def change_after_preflight(plan, *args, **kwargs):
        nonlocal calls
        calls += 1
        r = original(plan, *args, **kwargs)
        if calls > 3 and plan.plan_id == "P1":
            r.checks[0].status = "FAIL"
        return r
    monkeypatch.setattr(domains.atc, "evaluate_atc", change_after_preflight)
    scenario = load_scenario(EXAMPLE)
    scenario.initial_plan_id = "P1"
    r = asyncio.run(run_negotiation(scenario, default_agents(), OfflineGateway(), log_dir=tmp_path))
    assert r.outcome == "FALLBACK" and r.trigger_code == "FINAL_VALIDATION_FAILED"
    assert r.selected_plan_id == "P2" and r.acceptances == []
    assert calls >= 8


def test_unknown_check_is_not_consensus_or_false_infeasibility(tmp_path, monkeypatch):
    import domains.atc
    original = domains.atc.evaluate_atc
    def unknown(*args, **kwargs):
        r = original(*args, **kwargs)
        r.checks[0].status = "UNKNOWN"
        return r
    monkeypatch.setattr(domains.atc, "evaluate_atc", unknown)
    r = asyncio.run(run_negotiation(EXAMPLE, default_agents(), OfflineGateway(), log_dir=tmp_path))
    assert r.outcome == "ESCALATED" and r.reason_code == "CHECK_UNKNOWN"
    assert r.selected_plan is None


def test_reserved_deadline_never_returns_an_unfinished_validation(tmp_path, monkeypatch):
    import runtime.coordinator as coordinator
    clock = SimpleNamespace(value=0)
    monkeypatch.setattr(coordinator, "time", SimpleNamespace(monotonic=lambda: clock.value))
    original = coordinator.evaluate
    calls = 0
    def expire_final(*args, **kwargs):
        nonlocal calls
        calls += 1
        r = original(*args, **kwargs)
        if calls >= 4:
            clock.value = Budgets().whole_run_s + 1  # just past the run deadline
        return r
    monkeypatch.setattr(coordinator, "evaluate", expire_final)
    r = asyncio.run(run_negotiation(EXAMPLE, default_agents(), OfflineGateway(), log_dir=tmp_path))
    assert r.outcome == "ESCALATED" and r.reason_code == "FALLBACK_BUDGET_EXHAUSTED"
    assert r.selected_plan is None and r.acceptances == []


def test_caller_cancellation_closes_run_and_discards_votes(tmp_path):
    class Slow(OfflineGateway):
        async def complete(self, **kwargs):
            await asyncio.sleep(10)
            return await super().complete(**kwargs)
    async def exercise():
        task = asyncio.create_task(run_negotiation(EXAMPLE, default_agents(), Slow(), log_dir=tmp_path))
        await asyncio.sleep(.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await asyncio.sleep(0)
    asyncio.run(exercise())
    logs = list(tmp_path.glob("*.jsonl"))
    assert len(logs) == 1
    assert '"type":"RUN_CANCELLED"' in logs[0].read_text()
    assert not list(tmp_path.glob("*.result.json"))


def test_reusing_version_with_changed_data_fails_before_model_calls(tmp_path):
    scenario = load_scenario(EXAMPLE)
    a = asyncio.run(run_negotiation(scenario, default_agents(), OfflineGateway(), log_dir=tmp_path))
    scenario.ground.crews[1].available_windows[0].start_min = 20
    conflict = asyncio.run(run_negotiation(scenario, default_agents(), OfflineGateway(), log_dir=tmp_path))
    assert a.outcome == "CONSENSUS" and conflict.outcome == "INPUT_ERROR"
    assert conflict.reason_code == "SCENARIO_VERSION_CONFLICT" and conflict.agent_invocations == 0
    scenario.scenario_version += 1
    b = asyncio.run(run_negotiation(scenario, default_agents(), OfflineGateway(), log_dir=tmp_path))
    assert b.outcome == "CONSENSUS" and b.selected_plan_id == "P2"


def test_first_failure_is_not_hidden_by_cancelling_slow_peers(tmp_path):
    from contracts.models import AgentProtocolError
    class Gateway(OfflineGateway):
        async def complete(self, **kwargs):
            if kwargs["role"] == "ground":
                raise AgentProtocolError("MODEL_UNAVAILABLE", "ground", "test", "unavailable")
            await asyncio.sleep(1)
            return await super().complete(**kwargs)
    r = asyncio.run(run_negotiation(EXAMPLE, default_agents(), Gateway(), log_dir=tmp_path))
    assert r.outcome == "FALLBACK" and r.reason_code == "MODEL_UNAVAILABLE"
