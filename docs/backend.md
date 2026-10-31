# Coordinator backend handoff

Implemented on branch `coordinator`, 2026-10-31. Frontend work remains separate.
This implements the [protocol 1.0 architecture](ai-orchestration-architecture.md)
with unchanged agent wire shapes. Read the requirements, rubric and dataset
contract listed in [AGENTS.md](../AGENTS.md) before changing behavior.

## What is integrated

| Component | Source / ownership |
|---|---|
| Pilot adapter, evaluator and tests | Merged `origin/codex/pilot-agent` at `834f8da`, preserving history |
| Ground adapter, evaluator and tests | Merged `origin/codex/ground-agent` at `690a957`, preserving history |
| Shared agent wire types | Owners' matching `contracts/models.py`, unchanged |
| ATC adapter and evaluator | Compatible integrator reference, authorized by the user; no remote ATC branch was available |
| Coordinator, loader, catalog, gateway, log, CLI and API | Integration implementation on this branch |

Agents still review the current proposal once per round and return ACCEPT,
COUNTER or REJECT. COUNTER proposes existing complete catalog plan IDs; the
coordinator does not merge separate flight/gate fragments or invent schedules.
All agents receive the same candidate assignments and complete historical row,
but only their own state/reports. In round two they receive validated original
round-one messages. The agent interface has not been changed to prefilter away
all globally invalid candidates.

## Install and run

From the repository root with Python 3.11+:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python app.py --mode offline
python -m pytest -q
python3 scripts/check_alignment.py
```

The lock captures the Python 3.12 environment actually tested. Offline mode runs
the real three adapters/evaluators with an explicitly scripted model gateway.
It records six agent invocations and zero actual model calls for a two-round run.
These are integration results, not live LLM reasoning or latency measurements.

The expected default fixture result is CONSENSUS on P1 in two rounds. A live
model is free to produce different valid counteroffers or disagreement. The CLI
prints the complete JSON result and exits 0 for CONSENSUS/FALLBACK, 2 for
ESCALATED/INPUT_ERROR. Use `--scenario path/to/scenario.json` for another complete
protocol scenario. Dataset sources remain the committed originals.

For live mode, export `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` in your shell,
then run:

```sh
python app.py --mode live
```

No model name is silently selected and `.env` files are not automatically read.
Use your team's approved model/budget. No credentials were available during this
implementation, so no real provider generation was tested. The Anthropic REST
adapter is tested with an injected HTTP transport; it follows the official
[Messages API](https://platform.claude.com/docs/en/api/messages/create) and
[API/token-counting interface](https://platform.claude.com/docs/en/api/overview).
Other providers can implement the same `ModelGateway.complete` protocol.

## Run the HTTP backend

```sh
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

The default mode is offline. Set `COORDINATOR_MODE=live` in the server's
environment, plus the two live credentials/model settings, to enable real calls.
Mode is a server configuration, not an option in an untrusted client request.
This is a local development API with one process/worker, no authentication and
no configured cross-origin access. It is not a public deployment configuration.

| Endpoint | Behavior |
|---|---|
| `GET /health` | Protocol version and configured gateway mode |
| `GET /scenarios/example` | Complete labelled scenario, usable as the POST body |
| `POST /runs` | Accepts a ScenarioInput object directly; waits for the bounded run and returns RunResult |
| `GET /runs/{run_id}` | Read persisted terminal result, including reports, acceptances and usage |
| `GET /runs/{run_id}/events` | Ordered original evidence events as a JSON array |
| `GET /runs/{run_id}/evidence` | Download the original JSONL evidence |
| `GET /runs/{run_id}/why/{other_plan_id}` | Actual failed hard checks or first differing policy metric against the selected plan |

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.
For example:

```sh
curl http://127.0.0.1:8000/scenarios/example -o /tmp/sg-scenario.json
curl -X POST http://127.0.0.1:8000/runs \
  -H 'Content-Type: application/json' --data-binary @/tmp/sg-scenario.json
```

The server permits one active run; overlapping submissions return HTTP 409.
Unknown runs/plans return 404; malformed request schemas return FastAPI's 422;
unconfigured live mode returns 503. A well-shaped but semantically invalid
scenario returns RunResult with INPUT_ERROR and no agent calls. Application
outcomes are distinct from HTTP success: a 200 result may be ESCALATED.
Completed JSON results and JSONL evidence survive restarts in ignored `logs/`.

The POST endpoint returns when a run finishes. This version has no streaming
events or background-job polling during a run. The frontend can render the
returned report and original evidence after completion; streaming is separate
future work. Do not fabricate intermediate conversation in the frontend.

## State machine and deterministic policy

1. Strictly validate the scenario and all CSV source hashes/row values. Check
   joins, strict delay eligibility, IDs/options, complete role inputs and maps.
2. Claim the scenario revision in the persisted index. Replaying identical input
   is allowed; changing data under the same scenario ID/version is INPUT_ERROR
   with SCENARIO_VERSION_CONFLICT. Increment the version for a changed environment.
3. Evaluate every catalog plan using all three deterministic domain evaluators.
   An incomplete or wrongly bound report fails closed. Keep failed candidates
   visible for diagnosis; they can never become a final recommendation.
4. Publish the configured `initial_plan_id`. Run the three independent adapters
   concurrently on private JSON copies. Validate each reply independently of
   the adapter: exact identity, source/scenario/proposal/hash/round, own checks,
   counter IDs, citation scope, mutation and one-call budget.
5. All three ACCEPT plus fresh global checks gives CONSENSUS. Otherwise take the
   current plan and valid counteroffer IDs, discard globally invalid candidates,
   and choose the smallest fixed ranking tuple. Repetition exits to fallback.
6. Publish a new proposal and discard old votes. Round two uses fresh calls plus
   exact validated previous messages. There is no third round or model repair.
7. Any protocol/model/budget failure or continued disagreement invokes a checked
   deterministic fallback over the entire bounded catalog. A valid plan gives
   FALLBACK with no fabricated acceptances; no validated plan gives ESCALATED.

The ranking tuple is:

```text
(-throughput_count, missed_connections, additional_delay_min,
 turbulence_units, overtime_min, turnaround_delay_min, -gate_busy_min, plan_hash)
```

The policy is an engineering choice, not an aviation standard or a proof of the
most suitable plan under every preference. Rank positions/LLM confidence are not
votes in this formula. The proposed counteroffers define the negotiation pool;
fallback checks the full catalog. Complete plans contain all scenario flights.
There is no claim the catalog covers every possible disruption.

## Budgets and evidence

Two rounds; at most six generation attempts; no retries or repair calls;
25 seconds per role invocation; 60-second negotiation budget; 70-second whole-run
budget (raised from 15/35/40 after live timeouts; DEC-21). The shared output cap is 1,600 tokens, matching the merged adapters and
resolving the earlier 800-token documentation mismatch. Time defaults remain
unbenchmarked against live models.

Each live request counts the complete prompt through the provider before
generation, within the invocation timeout. More than 16,000 input tokens or an
unavailable count invokes fallback without dropping constraints. A separate
64,000-byte UTF-8 context ceiling also applies. (Both were raised from
8,000 tokens / 32,000 bytes after measured live prompts exceeded them; DEC-19.) Token-count requests are HTTP
requests, not model generations; evidence records them separately. A two-round
live run may use six count requests plus six model requests. Usage is preserved
for received malformed model responses; unknown usage remains null. Provider
timeouts may still incur unreported cost after client cancellation.

Every run has a fresh ID. Evidence includes source/overlay snapshot, prompt/rule
versions, budgets, reports, proposals, original parsed decisions and raw response
text, usage, protocol errors and final outcome. No chain-of-thought is requested
or stored. Provider error messages/authorization headers are not persisted; the
live gateway removes its known key from returned text before recording it.
Keep logs local and out of Git. Qualified human review follows the recommendation;
the backend performs no real airport execution.

## Verified results and remaining work

The test suite covers real integrated adapters/evaluators and mocked provider
HTTP, not only coordinator stubs. Verified examples:

Validation snapshot: **136 tests passed**, followed by the complete reference
alignment check. A temporary Uvicorn listener was also exercised over actual
localhost HTTP: the initial scenario returned P1 consensus, the incremented
crew-delay revision returned P2 consensus, and a new revision with no open runway
returned ESCALATED / NO_VALID_PLAN_IN_CATALOG. All used the offline gateway;
the listener was stopped after verification. Measured run times in that local
smoke check were 49 ms and 40 ms for the first two runs, excluding network/client
startup and any real model latency. These are not live-model timing claims.

| Case | Observed outcome |
|---|---|
| Default fixture | Two-round consensus on P1 with scripted gateway |
| P1 initially proposed | One-round consensus with scripted gateway |
| Different counteroffer sets/ranking orders | Fixed policy selects among the proposed pool |
| Round-two disagreement or malformed/stale/unknown reply | Checked fallback, distinct from consensus |
| Entire catalog fails runway checks | ESCALATED / NO_VALID_PLAN_IN_CATALOG |
| Missing report checks / UNKNOWN | No final unsafe recommendation |
| Final check changes after initial validation | Cached pass cannot establish consensus; fresh fallback checks apply |
| Changed crew C2 availability starts at minute 20 | New version: P1 fails GROUND_CREW; P2 reaches scripted consensus |
| Changed data without version increment | INPUT_ERROR before agent calls |
| Timeout, extra model call, request mutation, caller cancellation | Bounded failure/closed request; no stale vote reused |
| Mocked live HTTP | Six counted generations across three roles/two rounds, no retries; invalid JSON preserves available usage |
| API request, persisted result, evidence export, comparison | Verified with an in-process HTTP test client |

For P1 the modelled metrics match hand calculations: throughput 3, additional
delay 2 minutes, missed connecting passengers 0, turbulence 3 ordinal units,
overtime 2 minutes, turnaround delay 0 minutes, gate occupancy 24 gate-minutes.
The deterministic fallback chooses the same P1 under the same initial scenario;
this does not show a multi-agent advantage over that baseline. No single-agent
baseline, real-world benefit or live model success rate is claimed.

All operational values are simulated; the actual historical seed is row 76
(AA 1344 DEN–DFW, weather delay 35 and late-aircraft delay 40 minutes). Arrival,
fuel, wake classes, routes, gates, crews, turbulence and passenger connection
inputs remain separate labelled overlays. Raw HHMM clocks are not converted
into simulation slots. See [dataset limitations](datasets.md).

Remaining work: live provider/model integration and timing, review of the
reference ATC implementation by its owner, broader scenario/catalog coverage,
live evaluation against comparable baselines, frontend and human review UX,
and the organizer's clarification of “under 3 turns.” The persisted revision
index and evidence files assume the documented single-process local runtime;
multiple workers/distributed deployment require a shared transactional store.
