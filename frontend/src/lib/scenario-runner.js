import { flightLabel, proposedPlan, replies, reportFor, ROLES, runwayClosedUntil } from './coordination.js';

// Backend demo scenarios (runtime/demo_scenarios.py), one per outcome.
export const SCENARIOS = [
  { id:'clear', label:'All clear', expected:'CONSENSUS',
    description:'The airline’s proposed plan already fits runway spacing, fuel and stands.' },
  { id:'counter', label:'Counteroffer', expected:'CONSENSUS or FALLBACK',
    description:'Arrivals are 2 min apart and two aircraft share G1. Agents counter and the best plan is chosen.' },
  { id:'escalate', label:'Runway closed', expected:'ESCALATED',
    description:'The runway is closed until +45 min. No plan can land safely, so a controller must decide.' },
];

export class BackendError extends Error {
  constructor(message, status=null) { super(message); this.status=status; }
}

function friendly(status, detail) {
  if(status===409)return 'Another run is still finishing on the server. Try again in a few seconds.';
  if(status===429)return detail||'Too many runs right now. Wait a minute and try again.';
  if(status===503)return 'The backend is in live mode but has no model or API key configured.';
  if(status===422)return `The backend rejected the scenario: ${detail||'invalid input'}.`;
  return `The backend returned HTTP ${status}${detail?`: ${detail}`:''}.`;
}

async function call(fetchImpl, path, init) {
  let response;
  try { response=await fetchImpl(`/api${path}`, init); }
  catch { throw new BackendError('Cannot reach the backend. Start it with: uvicorn api_fuel:app --port 8000'); }
  if(!response.ok) {
    let detail='';
    try { const body=await response.json(); detail=typeof body.detail==='string'?body.detail:''; } catch { /* non-JSON error body */ }
    throw new BackendError(friendly(response.status, detail), response.status);
  }
  return response.json();
}

// Hosted static build (vite build --mode static): no backend exists, so each
// scenario replays a run recorded by frontend/scripts/record-runs.py. The
// files are unaltered API output; the app never holds an API key.
export const STATIC_DEMO=import.meta.env?.VITE_STATIC_DEMO==='1';

async function recordedRun(fetchImpl, id) {
  const response=await fetchImpl(`/data/runs/${id}.json`);
  if(!response.ok)throw new BackendError(`Recorded run for "${id}" is missing (HTTP ${response.status}).`, response.status);
  return response.json();
}

export async function backendHealth({fetchImpl=fetch}={}) {
  if(STATIC_DEMO) {
    const run=await recordedRun(fetchImpl, SCENARIOS[0].id);
    return { status:'ok', mode:'recorded', recorded:run.recorded };
  }
  return call(fetchImpl, '/health');
}
export async function loadScenario(id, {fetchImpl=fetch}={}) {
  if(STATIC_DEMO)return (await recordedRun(fetchImpl, id)).scenario;
  return call(fetchImpl, `/scenarios/demo/${id}`);
}

// Runs the real coordinator: the three agents are invoked server-side (live
// Claude or the offline test double, per the server's COORDINATOR_MODE). The
// returned bundle has the same shape as the recorded fixtures.
export async function runLiveScenario(id, {fetchImpl=fetch, scenario=null}={}) {
  if(STATIC_DEMO) {
    const run=await recordedRun(fetchImpl, id);
    return { kind:'recorded-run', recorded:run.recorded, scenario:run.scenario, result:run.result, events:run.events, fuel:run.fuel };
  }
  const input=scenario||await loadScenario(id,{fetchImpl});
  const result=await call(fetchImpl, '/runs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(input)});
  const [events, fuel]=await Promise.all([
    call(fetchImpl, `/runs/${result.run_id}/events`),
    call(fetchImpl, `/runs/${result.run_id}/fuel-co2`).catch(()=>null),
  ]);
  return { kind:'live-backend-run', scenario:input, result, events, fuel };
}

// Frontend-only event presentation. A future backend adapter can implement this
// boundary without changing the view or protocol 1.0 agent messages.
export function startScenario(bundle, emit, { reducedMotion=false, schedule=setTimeout, cancel=clearTimeout }={}) {
  const timers=[];
  const send=(at,event)=>timers.push(schedule(()=>emit(event),at));
  emit({type:'START'});
  send(350,{type:'ROUND',round:1});
  const first=replies(bundle,1);
  const second=replies(bundle,2);
  first.forEach((reply,index)=>send(850+index*750,{type:'MESSAGE',reply}));
  if(second.length) {
    send(3300,{type:'PROPOSAL',planId:proposedPlan(bundle,2)?.plan_id||second[0].current_plan_id});
    second.forEach((reply,index)=>send(4100+index*750,{type:'MESSAGE',reply}));
  }
  send(second.length?6350:3400,{type:'RESULT',result:bundle.result,reducedMotion});
  return ()=>timers.forEach(cancel);
}

export function currentAgentVerdict(messages, role, round) {
  return messages.filter((reply)=>reply.role===role&&reply.round_index===round).at(-1)?.result.decision.verdict || null;
}

export function conciseReason(bundle, reply) {
  const report=reportFor(bundle,reply.current_plan_id,reply.role);
  const decision=reply.result.decision;
  const bad=(report?.checks||[]).filter((c)=>c.severity==='HARD'&&['FAIL','UNKNOWN'].includes(c.status));
  if(reply.role==='atc') {
    if(bad.some((c)=>c.rule_id==='ATC_RUNWAY')) {
      const reopens=runwayClosedUntil(bundle.scenario);
      if(reopens===Infinity)return 'The runway is closed. I cannot clear any arrival.';
      if(reopens!==null)return `The runway is closed until +${reopens} min. Every plan lands before it reopens.`;
      return 'I cannot clear an arrival within the runway window.';
    }
    const wake=bad.find((c)=>c.rule_id==='ATC_WAKE');
    if(wake) {
      // "gap=2" (reference evaluator) or "F1->F2 gap 2 min" (ATC agent).
      const gap=wake.observed.match(/gap[= ](\d+)/)?.[1];
      const required=wake.required.match(/>= (\d+)/)?.[1];
      if(gap&&required)return `I need ${required} min between arrivals. The current gap is ${gap} min.`;
    }
    if(decision.verdict==='ACCEPT')return 'Runway, spacing and taxiway checks pass.';
  }
  if(reply.role==='pilot'&&decision.verdict==='ACCEPT') {
    const missed=report?.metrics.missed_connections||0;
    return missed ? `Fuel and turbulence limits pass. ${missed} passengers miss their connection.` : 'Fuel and turbulence limits pass. Both connections stay on time.';
  }
  if(reply.role==='ground') {
    if(bad.some((c)=>c.rule_id==='GROUND_CREW')) {
      const start=bundle.scenario.ground.crews.find((c)=>c.crew_id==='C2')?.available_windows[0]?.start_min;
      return `Crew C2 starts at +${start} min. Delay ${flightLabel(bundle.scenario,'F2')} to fit.`;
    }
    if(bad.some((c)=>c.rule_id==='GROUND_GATE'))return 'Separate the stands. Two aircraft need G1.';
    if(decision.verdict==='ACCEPT')return 'Stand, crew and turnaround checks pass.';
  }
  return decision.reason;
}

export function runEndMinute(bundle) {
  return Math.max(...(bundle.result.selected_plan?.assignments||bundle.scenario.plans[0].assignments).map((a)=>a.gate_out_min));
}
