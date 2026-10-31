import { flightLabel, replies, reportFor, ROLES } from './coordination.js';

export const SCENARIOS = [
  { id:'base', label:'Arrival conflict', file:'demo-run.json', description:'Resolve an arrival gap and a shared stand.' },
  { id:'crew', label:'Crew delay', file:'demo-crew.json', description:'Adjust arrivals while a crew is unavailable.' },
];

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
    send(3300,{type:'PROPOSAL',planId:bundle.result.selected_plan_id});
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
    const wake=bad.find((c)=>c.rule_id==='ATC_WAKE');
    if(wake) {
      const gap=wake.observed.match(/gap=(\d+)/)?.[1];
      const required=wake.required.match(/>= (\d+)/)?.[1];
      if(gap&&required)return `I need ${required} min between arrivals. The current gap is ${gap} min.`;
    }
    if(bad.some((c)=>c.rule_id==='ATC_RUNWAY'))return 'I cannot clear an arrival within the runway window.';
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
