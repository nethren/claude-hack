import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ArrowUpRight, Check, ChevronDown, Clock3, Download, Fuel, Hand, Info, Leaf, Plane,
  RadioTower, ShieldCheck, Siren, TriangleAlert, Truck, X } from 'lucide-react';
import AirportMap from './AirportMap.jsx';
import { alternativeSummary, blockingRules, clockLabel, displayPlan, flightIdentity, flightLabel, fuelDeadlines,
  groupedChecks, pendingResult, reportFor, ROLES, runwayClosedUntil } from './lib/coordination.js';
import { FLIGHT_IDENTITIES } from './lib/flight-identities.js';
import { aircraftPosition } from './lib/movement.js';
import { backendHealth, conciseReason, currentAgentVerdict, loadScenario, runEndMinute, runLiveScenario,
  SCENARIOS, startScenario } from './lib/scenario-runner.js';

const ICONS={atc:RadioTower,pilot:Plane,ground:Truck};
const NAMES={atc:'ATC',pilot:'Pilot',ground:'Ground'};
const VERDICT={ACCEPT:'Approved',COUNTER:'Counteroffer',REJECT:'Rejected'};

async function loadJson(url) {
  const response=await fetch(url);
  if(!response.ok)throw new Error('Could not load the airfield map. Reload to try again.');
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
  const summary=conciseReason(bundle,reply);
  return <article className={`agent-message message-${decision.verdict}`}>
    <AgentIcon role={reply.role}/>
    <div className="message-content">
      <div className="message-heading"><strong>{NAMES[reply.role]}</strong><Decision verdict={decision.verdict}/></div>
      <p>{summary}</p>
      {decision.reason!==summary&&<blockquote className="agent-quote">“{decision.reason}”</blockquote>}
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

function EscalationAlert({bundle,acknowledged,onAcknowledge}) {
  const scenario=bundle.scenario;
  const reopens=runwayClosedUntil(scenario);
  const deadlines=fuelDeadlines(scenario);
  const soonest=deadlines[0];
  const rules=blockingRules(bundle);
  const planCount=scenario.plans.length;
  return <section className={`escalation-alert ${acknowledged?'escalation-acknowledged':''}`} role="alert" aria-live="assertive">
    <div className="escalation-head"><Siren size={22}/><div><strong>{acknowledged?'Controller has control':'Controller action required'}</strong><span>Escalated · {(bundle.result.reason_code||'').replaceAll('_',' ').toLowerCase()}</span></div></div>
    <p className="escalation-lead">None of the {planCount} plans passed every hard check. The agents cannot resolve this on their own.</p>
    <ul className="escalation-facts">
      {reopens!==null&&<li><TriangleAlert size={14}/>{reopens===Infinity?'Runway closed with no reopening time':`Runway closed until +${reopens} min`}</li>}
      {soonest&&<li className="fact-critical"><Fuel size={14}/><span><strong>{flightLabel(scenario,soonest.flight_id)}</strong> reaches reserve fuel at <strong>+{soonest.reserve_min} min</strong>{reopens!==null&&reopens!==Infinity&&soonest.reserve_min<reopens?`, ${reopens-soonest.reserve_min} min before the runway reopens`:''}</span></li>}
      {deadlines.slice(1).map((d)=><li key={d.flight_id}><Fuel size={14}/><span>{flightLabel(scenario,d.flight_id)} reaches reserve at +{d.reserve_min} min</span></li>)}
      {rules.map((r)=><li key={r.rule}><X size={14}/><span>{r.label} failed in {r.plans.length===planCount?'every plan':r.plans.join(', ')}</span></li>)}
    </ul>
    <p className="escalation-options">Options outside the catalog: divert to an alternate, reopen another runway, or prioritise the lowest-fuel arrival.</p>
    {acknowledged?<p className="escalation-ack"><Check size={14}/>Acknowledged. The recommendation and evidence are ready for review.</p>
      :<button className="escalation-button" onClick={onAcknowledge}><Hand size={16}/>Take control</button>}
  </section>;
}

function CarbonCard({bundle}) {
  const fuel=bundle.fuel;
  if(!fuel)return null;
  const planId=bundle.result.selected_plan_id;
  const estimate=fuel.panel.plans.find((p)=>p.plan_id===planId);
  const comparison=fuel.panel.comparisons.find((c)=>c.plan_id===planId);
  const baseline=fuel.panel.baseline;
  if(!estimate||!comparison||comparison.status!=='ESTIMATED')return null;
  const saved=comparison.co2_saved_kg;
  return <div className="carbon-card">
    <div className="carbon-title"><Leaf size={14}/><strong>Fuel & CO₂</strong><span>Modelled estimate</span></div>
    <div className="carbon-figures">
      <div><strong>{estimate.co2_kg.toLocaleString()} kg</strong><span>CO₂ from holding</span></div>
      <div><strong>{estimate.fuel_kg.toLocaleString()} kg</strong><span>Holding fuel</span></div>
      <div><strong className={saved<0?'outcome-warning':saved>0?'outcome-good':undefined}>{saved>0?'−':saved<0?'+':''}{Math.abs(saved).toLocaleString()} kg</strong><span>vs scheduled order</span></div>
    </div>
    <p>{saved<0?`Uses more CO₂ than landing in scheduled order (${baseline.co2_kg} kg), which ignores the stand and crew conflicts.`:saved>0?'Saves CO₂ against landing in scheduled order.':'Same CO₂ as landing in scheduled order.'} Holding fuel only; not measured.</p>
  </div>;
}

function exportEvidence(bundle) {
  const blob=new Blob([JSON.stringify({...bundle,display_flights:FLIGHT_IDENTITIES},null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=`groundline-${bundle.result.run_id||bundle.scenario.scenario_id}.json`;link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export default function App() {
  const [layout,setLayout]=useState(null),[bundles,setBundles]=useState({}),[error,setError]=useState(''),[runError,setRunError]=useState('');
  const [health,setHealth]=useState(null);
  const [scenarioId,setScenarioId]=useState(SCENARIOS[0].id),[selected,setSelected]=useState('F1');
  const [phase,setPhase]=useState(0),[round,setRound]=useState(1),[messages,setMessages]=useState([]);
  const [status,setStatus]=useState('idle'),[playing,setPlaying]=useState(false),[acknowledged,setAcknowledged]=useState(false);
  const [waited,setWaited]=useState(0);
  const [clock,setClock]=useState(9.4),clockRef=useRef(9.4);
  const reducedMotion=useRef(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const cancelRun=useRef(()=>{}),feed=useRef(null),runToken=useRef(0);
  const bundle=bundles[scenarioId];

  useEffect(()=>{
    let active=true;
    Promise.all([loadJson('/data/dfw-layout.json'),...SCENARIOS.map((s)=>loadScenario(s.id))])
      .then(([map,...scenarios])=>{
        if(!active)return;
        setLayout(map);
        setBundles(Object.fromEntries(SCENARIOS.map((s,i)=>[s.id,{kind:'scenario-preview',scenario:scenarios[i],result:pendingResult(),events:[],fuel:null}])));
      })
      .catch((e)=>{if(active)setError(e.message);});
    backendHealth().then((h)=>{if(active)setHealth(h);}).catch(()=>{if(active)setHealth({mode:'unreachable'});});
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
    if(status!=='waiting')return;
    const started=Date.now();
    const timer=setInterval(()=>setWaited(Math.floor((Date.now()-started)/1000)),500);
    return ()=>clearInterval(timer);
  },[status]);

  useEffect(()=>{
    if(feed.current)feed.current.scrollTo({top:feed.current.scrollHeight,behavior:reducedMotion.current?'instant':'smooth'});
  },[messages.length,phase,acknowledged]);

  function reset(id=scenarioId) {
    runToken.current++;
    cancelRun.current();setPlaying(false);clockRef.current=9.4;setClock(9.4);setWaited(0);
    setScenarioId(id);setMessages([]);setPhase(0);setRound(1);setStatus('idle');setRunError('');setAcknowledged(false);
  }

  async function run() {
    reset();
    const id=scenarioId,token=runToken.current;
    setStatus('waiting');setPhase(1);
    let live;
    try { live=await runLiveScenario(id,{scenario:bundles[id].scenario}); }
    catch(e) { if(token===runToken.current){setStatus('idle');setPhase(0);setRunError(e.message);} return; }
    if(token!==runToken.current)return;
    setBundles((current)=>({...current,[id]:live}));
    cancelRun.current=startScenario(live,(event)=>{
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
        else {setStatus(event.result.outcome==='ESCALATED'?'escalated':'complete');if(hasPlan){clockRef.current=runEndMinute(live);setClock(clockRef.current);}}
      }
    },{reducedMotion:reducedMotion.current});
  }

  if(!layout||!bundle)return <main className="load-state" aria-busy={!error}>
    <div className="brand-icon"/><h1>{error?'Could not load the scenarios':'Loading DFW'}</h1><p>{error||'Preparing the airfield and flights.'}</p>
    {error&&<button className="run-button" onClick={()=>location.reload()}>Reload</button>}
  </main>;

  const scenario=bundle.scenario,result=bundle.result,currentPlan=displayPlan(bundle,phase);
  const meta=SCENARIOS.find((s)=>s.id===scenarioId);
  const initialId=scenario.initial_plan_id;
  const revisedId=currentPlan.plan_id;
  const focus=currentPlan.assignments.find((a)=>a.flight_id===selected)||currentPlan.assignments[0],identity=flightIdentity(scenario,focus.flight_id);
  const position=aircraftPosition(layout,focus,scenario.shared,clock);
  const active=['waiting','running','moving'].includes(status);
  const done=phase===5;
  const approved=done&&result.outcome==='CONSENSUS';
  const escalated=done&&result.outcome==='ESCALATED';
  const ready=done&&['CONSENSUS','FALLBACK'].includes(result.outcome);
  const totalConnections=scenario.pilot.limits.reduce((n,l)=>n+l.connecting_passengers,0);
  const summary=result.metrics;
  const reopens=runwayClosedUntil(scenario);
  const t2Closed=scenario.atc.routes.find((r)=>r.route_id==='T2')?.blocked_windows.some((w)=>w.start_min<=0&&w.end_min>=scenario.shared.horizon_end_min);
  const live=health?.mode==='live';
  const title=status==='idle'?'Ready to run':status==='waiting'?`Agents reviewing ${initialId}…`:status==='running'?round===1?`Reviewing ${initialId}`:`Reviewing ${revisedId}`:status==='moving'?'Aircraft moving':escalated?'Escalated to controller':'Scenario complete';

  return <div className={`application ${escalated&&!acknowledged?'application-escalated':''}`}>
    <header className="app-header">
      <a className="brand" href="/" aria-label="Groundline dashboard"><span className="brand-icon" aria-hidden="true"><i/><i/><i/></span>groundline<span className="brand-period">.</span></a>
      <div className="airport-title"><strong>DFW</strong><span>Dallas Fort Worth</span></div>
      <span className={`mode-badge mode-${health?.mode||'pending'}`} title={health===null?'Connecting…':health.mode==='unreachable'?'Backend offline':live?'Live Claude agents':'Offline test agents'}>
        <span className="mode-long">{health===null?'Connecting…':health.mode==='unreachable'?'Backend offline':live?'Live Claude agents':'Offline test agents'}</span>
        <span className="mode-short">{health===null?'…':health.mode==='unreachable'?'Offline':live?'Live':'Test'}</span>
      </span>
      <details className="run-details"><summary><Info size={15}/>Details</summary><div className="details-panel">
        <h2>Run details</h2>
        <dl><div><dt>Flights</dt><dd>DOT 2015 callsigns</dd></div><div><dt>Traffic & movement</dt><dd>Simulated</dd></div><div><dt>Agents</dt><dd>{live?'Live Claude calls':'Offline test double'}</dd></div><div><dt>Backend</dt><dd>{health?.mode==='unreachable'?'Not reachable':'Connected'}</dd></div><div><dt>Outcome</dt><dd>{done?result.outcome:'Pending'}</dd></div><div><dt>Model calls</dt><dd>{done?`${result.model_calls_completed} / ${result.model_calls_attempted}`:0}</dd></div></dl>
        <p>Each run sends the scenario to the coordinator, which invokes the ATC, Pilot and Ground agents independently and checks every reply in code.</p>
        <p>Flight labels come from rows 76, 20 and 49. Routes use the DFW map as a visual guide. Fuel and CO₂ are modelled estimates.</p>
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
    {runError&&<div className="run-error" role="alert"><TriangleAlert size={16}/>{runError}</div>}

    <main className="workspace">
      <section className="surface-workspace" aria-labelledby="surface-heading">
        <div className="surface-heading"><h1 id="surface-heading">Airfield</h1>{escalated&&<span className="map-alert"><Siren size={14}/>Escalated · arrivals held</span>}<span>{scenario.shared.flights.length} flights <span className="heading-dot">·</span> T+{clockLabel(clock)}</span></div>
        <div className={`map-frame ${escalated?'map-escalated':''}`}>
          <AirportMap layout={layout} bundle={bundle} plan={currentPlan} selected={focus.flight_id} onSelect={setSelected} clock={clock} clockRef={clockRef} playing={playing} phase={phase} waiting={status==='waiting'}/>
          <div className="selected-flight"><div className="selected-flight-head"><span><Plane size={17}/><strong>{identity.callsign}</strong></span><span>{escalated?'Holding':position.phase}</span></div><div className="flight-route">{identity.origin}<ArrowRight size={14}/>{identity.destination}<span className="flight-stand">{focus.gate_id}</span></div><div className="flight-assignment">Arrival <strong>+{focus.landing_min} min</strong><span>Plan {currentPlan.plan_id}</span></div></div>
          <div className="map-conditions">{reopens===null?<span className="map-condition"><i/>Runway open</span>:<span className="map-condition restriction"><i/>{reopens===Infinity?'Runway closed':`Runway closed to +${reopens}`}</span>}{t2Closed&&<span className="map-condition restriction"><i/>T2 closed</span>}</div>
        </div>
        <div className="traffic-list" aria-label="Flights">{currentPlan.assignments.map((a)=>{
          const name=flightIdentity(scenario,a.flight_id),p=aircraftPosition(layout,a,scenario.shared,clock);
          return <button key={a.flight_id} className={`traffic-flight ${focus.flight_id===a.flight_id?'traffic-selected':''}`} aria-pressed={focus.flight_id===a.flight_id} onClick={()=>setSelected(a.flight_id)}><Plane size={18}/><span><strong>{name.callsign}</strong><small>{name.origin} → DFW</small></span><span className="traffic-flight-state"><small>{escalated?'Holding':p.phase}</small><strong>{a.gate_id}</strong></span></button>;
        })}</div>
      </section>

      <aside className="coordination-panel" aria-labelledby="coordination-heading">
        <div className="coordination-title"><h2 id="coordination-heading">Agent coordination</h2><span>{status==='idle'?'3 agents':`Round ${round} / 2`}</span></div>
        <div className="agent-roster">{ROLES.map((role)=>{
          const verdict=currentAgentVerdict(messages,role,round);
          return <div key={role}><AgentIcon role={role} small/><strong>{NAMES[role]}</strong><span className={`roster-state roster-${verdict||'pending'}`}>{VERDICT[verdict]||(active?'Reviewing':'Ready')}</span></div>;
        })}</div>

        <div className="agent-feed" ref={feed} role="log" aria-label="Agent messages" aria-live="polite" aria-relevant="additions text">
          {status==='idle'?<div className="scenario-brief"><span className="brief-symbol"><RadioTower size={23}/></span><h3>{meta.label}</h3><p>{meta.description}</p><span>Run the scenario to send it to the three agents{live?' (live Claude calls, about 10–40 s)':''}.</span></div>:<>
            <div className="round-label">Initial plan <span>{initialId}</span></div>
            {messages.filter((r)=>r.round_index===1).map((reply)=><AgentMessage key={reply.request_id} bundle={bundle} reply={reply}/>)}
            {messages.length===0&&<div className="reviewing-message"><span className="reviewing-dots"><i/><i/><i/></span>{status==='waiting'?`ATC, Pilot and Ground are reviewing ${initialId}${live?' with live model calls':''}… ${waited}s`:`Agents are checking ${initialId}.`}</div>}
            {phase>=3&&<><div className="proposal-message"><WaypointsIcon/><div><strong>Coordinator proposes {revisedId}</strong><p>Chosen from the agents’ counteroffers by the fixed ranking policy, not by vote.</p></div></div><div className="round-label">Revised plan <span>{revisedId}</span></div></>}
            {messages.filter((r)=>r.round_index===2).map((reply)=><AgentMessage key={reply.request_id} bundle={bundle} reply={reply}/>)}
            {phase>=3&&phase<5&&<div className="reviewing-message"><span className="reviewing-dots"><i/><i/><i/></span>Waiting for fresh approvals.</div>}
            {done&&!escalated&&<div className={`agreement-message ${approved?'agreement-approved':'agreement-other'}`}><ShieldCheck size={19}/><div><strong>{approved?`${result.selected_plan_id} approved`:'Checked fallback'}</strong><p>{approved?`ATC, Pilot and Ground agree${result.rounds_completed===1?' in round 1':' after counteroffers'}.`:`No unanimous agreement (${(result.reason_code||'').replaceAll('_',' ').toLowerCase()}). Code selected the best plan that passes every check.`}</p></div></div>}
            {escalated&&<EscalationAlert bundle={bundle} acknowledged={acknowledged} onAcknowledge={()=>setAcknowledged(true)}/>}
          </>}
        </div>

        <section className="plan-summary" aria-label="Plan result">
          {ready&&summary?<><div className="summary-title"><h3>Plan {result.selected_plan_id}</h3><span><Check size={12}/>{approved?'Approved':'Fallback'}</span></div><div className="plan-outcomes"><div><strong>+{summary.additional_delay_min} min</strong><span>Arrival delay</span></div><div><strong className={summary.missed_connections?'outcome-warning':undefined}>{Math.max(0,totalConnections-summary.missed_connections)}/{totalConnections}</strong><span>Connections kept</span></div><div><strong>{summary.overtime_min} min</strong><span>Crew overtime</span></div></div><CarbonCard bundle={bundle}/><details className="plan-comparison"><summary>Why this plan?<ChevronDown size={13}/></summary><div>{scenario.plans.filter((p)=>p.plan_id!==result.selected_plan_id).map((p)=>{
            const comparison=alternativeSummary(bundle,p.plan_id);
            return <div key={p.plan_id}><strong>{p.plan_id}<span className={comparison.eligible?'':'rejected-alternative'}>{comparison.eligible?'Feasible':'Ruled out'}</span></strong><p>{comparison.text}</p></div>;
          })}</div></details><p className="human-review">Recommendation only. Ready for controller review.</p></>
          :escalated?<div className="summary-escalated"><Siren size={16}/><div><strong>No plan cleared</strong><p>{acknowledged?'Controller has taken control of the arrivals.':'Waiting for a controller decision.'}</p></div></div>
          :<p className="summary-pending">{status==='idle'?'Plan pending':'Waiting for agent agreement.'}</p>}
        </section>
      </aside>
    </main>
    <footer className="app-footer"><span>{meta.description}</span><span>DFW <span>·</span> Airport surface</span></footer>
  </div>;
}

function WaypointsIcon(){return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="5" cy="6" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7 6h6a4 4 0 0 1 0 8h-2a4 4 0 0 0 0 8h6"/></svg>;}
