import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ArrowUpRight, Check, ChevronDown, ChevronRight, CircleCheck,
  Clock3, Download, Info, Plane, RadioTower, ShieldCheck, Truck, X } from 'lucide-react';
import AirportMap from './AirportMap.jsx';
import { alternativeSummary, clockLabel, displayPlan, flightIdentity, flightLabel,
  groupedChecks, reportFor, ROLES } from './lib/coordination.js';
import { FLIGHT_IDENTITIES } from './lib/flight-identities.js';
import { aircraftPosition } from './lib/movement.js';
import { conciseReason, currentAgentVerdict, runEndMinute, SCENARIOS, startScenario } from './lib/scenario-runner.js';

const ICONS={atc:RadioTower,pilot:Plane,ground:Truck};
const NAMES={atc:'ATC',pilot:'Pilot',ground:'Ground'};
const JOBS={atc:'Runway & spacing',pilot:'Fuel & connections',ground:'Stands & crews'};
const VERDICT={ACCEPT:'Approved',COUNTER:'Counteroffer',REJECT:'Rejected'};

async function loadJson(url) {
  const response=await fetch(url);
  if(!response.ok)throw new Error('Could not load the scenario. Reload to try again.');
  return response.json();
}

function AgentIcon({role,small=false}) {
  const Icon=ICONS[role];
  return <span className={`agent-avatar avatar-${role} ${small?'avatar-small':''}`}><Icon size={small?18:21}/></span>;
}

function Decision({verdict,pending=false}) {
  const Icon=verdict==='ACCEPT'?Check:verdict==='REJECT'?X:verdict==='COUNTER'?ArrowUpRight:Clock3;
  return <span className={`decision decision-${verdict||'pending'}`}><Icon size={13}/>{VERDICT[verdict]||(pending?'Reviewing':'Ready')}</span>;
}

function AgentMessage({bundle,reply}) {
  const [open,setOpen]=useState(false);
  const report=reportFor(bundle,reply.current_plan_id,reply.role);
  const checks=groupedChecks(report);
  const failures=checks.filter((c)=>c.status!=='PASS');
  const decision=reply.result.decision;
  return <article className={`agent-message message-${decision.verdict}`}>
    <AgentIcon role={reply.role}/>
    <div className="message-content">
      <div className="message-heading"><strong>{NAMES[reply.role]}</strong><Decision verdict={decision.verdict}/></div>
      <p>{conciseReason(bundle,reply)}</p>
      {decision.verdict==='COUNTER'&&<div className="counter-options">Proposes <strong>{decision.ranked_alternative_ids.join(' or ')}</strong></div>}
      <button className={`check-toggle ${failures.length?'has-failures':''}`} aria-expanded={open} onClick={()=>setOpen(!open)}>
        {failures.length?<X size={12}/>:<Check size={12}/>} {failures.length?`${failures.length} ${failures.length===1?'issue':'issues'}`:`${checks.length} checks passed`}<ChevronDown size={12}/>
      </button>
      {open&&<div className="message-checks">{checks.map((group)=><details key={group.rule} className={`check-group check-${group.status.toLowerCase()}`}>
        <summary>{group.status==='PASS'?<Check size={12}/>:<X size={12}/>}<span>{group.label}</span><strong>{group.status==='PASS'?'Pass':group.status==='FAIL'?'Fail':'Unknown'}</strong></summary>
        <div>{group.checks.map((check)=><p key={check.check_id}><b>{check.flight_ids.map((id)=>flightLabel(bundle.scenario,id)).join(' + ')}</b><span>{check.observed}</span><small>{check.required}</small></p>)}</div>
      </details>)}</div>}
    </div>
  </article>;
}

function exportEvidence(bundle) {
  const blob=new Blob([JSON.stringify({...bundle,display_flights:FLIGHT_IDENTITIES},null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=`groundline-${bundle.result.run_id}.json`;link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export default function App() {
  const [layout,setLayout]=useState(null),[bundles,setBundles]=useState(null),[error,setError]=useState('');
  const [scenarioId,setScenarioId]=useState('base'),[selected,setSelected]=useState('F1');
  const [phase,setPhase]=useState(0),[round,setRound]=useState(1),[messages,setMessages]=useState([]);
  const [status,setStatus]=useState('idle'),[playing,setPlaying]=useState(false);
  const [clock,setClock]=useState(9.4),clockRef=useRef(9.4);
  const reducedMotion=useRef(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const cancelRun=useRef(()=>{}),feed=useRef(null);
  const bundle=bundles?.[scenarioId];

  useEffect(()=>{
    let active=true;
    Promise.all([loadJson('/data/dfw-layout.json'),loadJson('/data/demo-run.json'),loadJson('/data/demo-crew.json')])
      .then(([map,base,crew])=>{if(active){setLayout(map);setBundles({base,crew});}})
      .catch((e)=>{if(active)setError(e.message);});
    return ()=>{active=false;cancelRun.current();};
  },[]);

  useEffect(()=>{
    if(!playing||!bundle)return;
    let frame,previous,lastLabel=0;
    const end=runEndMinute(bundle);
    function tick(now) {
      if(previous!==undefined)clockRef.current=Math.min(end,clockRef.current+Math.min((now-previous)/1000,.1)*50/60);
      previous=now;
      if(now-lastLabel>120){setClock(clockRef.current);lastLabel=now;}
      if(clockRef.current>=end){setClock(end);setPlaying(false);setStatus('complete');}
      else frame=requestAnimationFrame(tick);
    }
    frame=requestAnimationFrame(tick);
    return ()=>cancelAnimationFrame(frame);
  },[playing,bundle]);

  useEffect(()=>{
    if(feed.current)feed.current.scrollTo({top:feed.current.scrollHeight,behavior:reducedMotion.current?'instant':'smooth'});
  },[messages.length,phase]);

  function reset(id=scenarioId) {
    cancelRun.current();setPlaying(false);clockRef.current=9.4;setClock(9.4);
    setScenarioId(id);setMessages([]);setPhase(0);setRound(1);setStatus('idle');setError('');
  }

  function run() {
    reset();
    cancelRun.current=startScenario(bundle,(event)=>{
      if(event.type==='START'){setStatus('running');setPhase(1);}
      if(event.type==='ROUND')setRound(event.round);
      if(event.type==='MESSAGE'){
        setMessages((current)=>[...current,event.reply]);
        setPhase(event.reply.round_index===1?2:4);
      }
      if(event.type==='PROPOSAL'){setRound(2);setPhase(3);}
      if(event.type==='RESULT'){
        setPhase(5);
        const hasPlan=['CONSENSUS','FALLBACK'].includes(event.result.outcome);
        if(hasPlan&&!event.reducedMotion){setStatus('moving');setPlaying(true);}
        else {setStatus('complete');if(hasPlan){clockRef.current=runEndMinute(bundle);setClock(clockRef.current);}}
      }
    },{reducedMotion:reducedMotion.current});
  }

  if(!layout||!bundle)return <main className="load-state" aria-busy={!error}>
    <div className="brand-icon"/><h1>{error?'Could not load the scenario':'Loading DFW'}</h1><p>{error||'Preparing the airfield and flights.'}</p>
    {error&&<button className="run-button" onClick={()=>location.reload()}>Reload</button>}
  </main>;

  const scenario=bundle.scenario,result=bundle.result,currentPlan=displayPlan(bundle,phase);
  const focus=currentPlan.assignments.find((a)=>a.flight_id===selected),identity=flightIdentity(scenario,selected);
  const position=aircraftPosition(layout,focus,scenario.shared,clock);
  const active=status==='running'||status==='moving';
  const approved=phase===5&&result.outcome==='CONSENSUS';
  const ready=phase===5&&['CONSENSUS','FALLBACK'].includes(result.outcome);
  const totalConnections=scenario.pilot.limits.reduce((n,l)=>n+l.connecting_passengers,0);
  const summary=result.metrics;
  const title=status==='idle'?'Ready to run':status==='running'?round===1?'Reviewing P0':`Reviewing ${result.selected_plan_id}`:status==='moving'?'Aircraft moving':'Scenario complete';

  return <div className="application">
    <header className="app-header">
      <a className="brand" href="/" aria-label="Groundline dashboard"><span className="brand-icon" aria-hidden="true"><i/><i/><i/></span>groundline<span className="brand-period">.</span></a>
      <div className="airport-title"><strong>DFW</strong><span>Dallas Fort Worth</span></div>
      <details className="run-details"><summary><Info size={15}/>Details</summary><div className="details-panel">
        <h2>Run details</h2>
        <dl><div><dt>Flights</dt><dd>DOT 2015 callsigns</dd></div><div><dt>Traffic & movement</dt><dd>Demo data</dd></div><div><dt>Agents</dt><dd>Prepared responses</dd></div><div><dt>Backend</dt><dd>Connect after UI review</dd></div><div><dt>Outcome</dt><dd>{phase===5?result.outcome:'Pending'}</dd></div><div><dt>Model calls</dt><dd>{phase===5?result.model_calls_attempted:0}</dd></div></dl>
        <p>Flight labels come from rows 76, 20 and 49. Routes use the DFW map as a visual guide.</p>
        <p>Summaries use saved checks. The export includes the original agent messages and source fields.</p>
        <button className="text-button" onClick={()=>exportEvidence(bundle)}><Download size={14}/>Export evidence</button>
      </div></details>
    </header>

    <section className="scenario-bar" aria-label="Scenario controls">
      <div className="scenario-tabs" role="tablist" aria-label="Choose scenario">{SCENARIOS.map((item,index)=><button role="tab" aria-selected={scenarioId===item.id} tabIndex={scenarioId===item.id?0:-1} key={item.id} onClick={()=>reset(item.id)} onKeyDown={(event)=>{
        if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
        event.preventDefault();
        const next=event.key==='Home'?0:event.key==='End'?SCENARIOS.length-1:(index+(event.key==='ArrowRight'?1:-1)+SCENARIOS.length)%SCENARIOS.length;
        reset(SCENARIOS[next].id);event.currentTarget.parentElement.querySelectorAll('[role="tab"]')[next].focus();
      }}><span>{String(index+1).padStart(2,'0')}</span>{item.label}</button>)}</div>
      <div className="scenario-state"><span className={`state-dot ${status}`}/>{title}</div>
      <button className="run-button" onClick={run} disabled={active}>{active?<Clock3 size={16}/>:<ArrowRight size={16}/>} {active?'Running…':'Run scenario'}</button>
    </section>

    <main className="workspace">
      <section className="surface-workspace" aria-labelledby="surface-heading">
        <div className="surface-heading"><h1 id="surface-heading">Airfield</h1><span>{scenario.shared.flights.length} flights <span className="heading-dot">·</span> T+{clockLabel(clock)}</span></div>
        <div className="map-frame">
          <AirportMap layout={layout} bundle={bundle} plan={currentPlan} selected={selected} onSelect={setSelected} clock={clock} clockRef={clockRef} playing={playing} phase={phase} waiting={false}/>
          <div className="selected-flight"><div className="selected-flight-head"><span><Plane size={17}/><strong>{identity.callsign}</strong></span><span>{position.phase}</span></div><div className="flight-route">{identity.origin}<ArrowRight size={14}/>{identity.destination}<span className="flight-stand">{focus.gate_id}</span></div><div className="flight-assignment">Arrival <strong>+{focus.landing_min} min</strong><span>Plan {currentPlan.plan_id}</span></div></div>
          <div className="map-conditions"><span className="map-condition"><i/>Runway open</span><span className="map-condition restriction"><i/>T2 closed</span>{scenarioId==='crew'&&<span className="map-condition crew-condition">Crew C2 · +20 min</span>}</div>
        </div>
        <div className="traffic-list" aria-label="Flights">{currentPlan.assignments.map((a)=>{
          const name=flightIdentity(scenario,a.flight_id),p=aircraftPosition(layout,a,scenario.shared,clock);
          return <button key={a.flight_id} className={`traffic-flight ${selected===a.flight_id?'traffic-selected':''}`} aria-pressed={selected===a.flight_id} onClick={()=>setSelected(a.flight_id)}><Plane size={18}/><span><strong>{name.callsign}</strong><small>{name.origin} → DFW</small></span><span className="traffic-flight-state"><small>{p.phase}</small><strong>{a.gate_id}</strong></span></button>;
        })}</div>
      </section>

      <aside className="coordination-panel" aria-labelledby="coordination-heading">
        <div className="coordination-title"><h2 id="coordination-heading">Agent coordination</h2><span>{status==='idle'?'3 agents':`Round ${round} / 2`}</span></div>
        <div className="agent-roster">{ROLES.map((role)=>{
          const verdict=currentAgentVerdict(messages,role,round);
          return <div key={role}><AgentIcon role={role} small/><strong>{NAMES[role]}</strong><span className={`roster-state roster-${verdict||'pending'}`}>{VERDICT[verdict]||(active?'Reviewing':'Ready')}</span></div>;
        })}</div>

        <div className="agent-feed" ref={feed} role="log" aria-label="Agent messages" aria-live="polite" aria-relevant="additions text">
          {status==='idle'?<div className="scenario-brief"><span className="brief-symbol"><RadioTower size={23}/></span><h3>{SCENARIOS.find((s)=>s.id===scenarioId).label}</h3><p>{scenarioId==='base'?`${flightLabel(scenario,'F1')} and ${flightLabel(scenario,'F2')} share G1. Their arrivals are 2 min apart.`:'Crew C2 starts at +20 min. Adjust the arrivals to fit the available crew.'}</p><span>Run the scenario to hear from each agent.</span></div>:<>
            <div className="round-label">Initial plan <span>P0</span></div>
            {messages.filter((r)=>r.round_index===1).map((reply)=><AgentMessage key={reply.request_id} bundle={bundle} reply={reply}/>)}
            {messages.length===0&&<div className="reviewing-message"><span className="reviewing-dots"><i/><i/><i/></span>Agents are checking P0.</div>}
            {phase>=3&&<><div className="proposal-message"><WaypointsIcon/><div><strong>Coordinator proposes {result.selected_plan_id}</strong><p>Review the revised arrivals and stands.</p></div></div><div className="round-label">Revised plan <span>{result.selected_plan_id}</span></div></>}
            {messages.filter((r)=>r.round_index===2).map((reply)=><AgentMessage key={reply.request_id} bundle={bundle} reply={reply}/>)}
            {phase>=3&&phase<5&&<div className="reviewing-message"><span className="reviewing-dots"><i/><i/><i/></span>Waiting for fresh approvals.</div>}
            {phase===5&&<div className={`agreement-message ${approved?'agreement-approved':'agreement-other'}`}><ShieldCheck size={19}/><div><strong>{approved?`${result.selected_plan_id} approved`:result.outcome==='FALLBACK'?'Checked fallback':'Needs controller review'}</strong><p>{approved?'ATC, Pilot and Ground agree.':result.outcome==='FALLBACK'?'The coordinator found a valid plan without agreement.':'No plan passed the required checks.'}</p></div></div>}
          </>}
        </div>

        <section className="plan-summary" aria-label="Plan result">
          {ready&&summary?<><div className="summary-title"><h3>Plan {result.selected_plan_id}</h3><span><Check size={12}/>{approved?'Approved':'Fallback'}</span></div><div className="plan-outcomes"><div><strong>+{summary.additional_delay_min} min</strong><span>Arrival delay</span></div><div><strong className={summary.missed_connections?'outcome-warning':undefined}>{Math.max(0,totalConnections-summary.missed_connections)}/{totalConnections}</strong><span>Connections kept</span></div><div><strong>{summary.overtime_min} min</strong><span>Crew overtime</span></div></div><details className="plan-comparison"><summary>Why this plan?<ChevronDown size={13}/></summary><div>{scenario.plans.filter((p)=>p.plan_id!==result.selected_plan_id).map((p)=>{
            const comparison=alternativeSummary(bundle,p.plan_id);
            return <div key={p.plan_id}><strong>{p.plan_id}<span className={comparison.eligible?'':'rejected-alternative'}>{comparison.eligible?'Feasible':'Ruled out'}</span></strong><p>{comparison.text}</p></div>;
          })}</div></details><p className="human-review">Ready for controller review.</p></>:<p className="summary-pending">{status==='idle'?'Plan pending':'Waiting for agent agreement.'}</p>}
        </section>
      </aside>
    </main>
    <footer className="app-footer"><span>{scenarioId==='base'?'Weather delay +35 min · Stand conflict':'Crew C2 unavailable before +20 min'}</span><span>DFW <span>·</span> Airport surface</span></footer>
  </div>;
}

function WaypointsIcon(){return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="5" cy="6" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7 6h6a4 4 0 0 1 0 8h-2a4 4 0 0 0 0 8h6"/></svg>;}
