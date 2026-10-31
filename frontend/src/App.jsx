import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, ArrowDown, ArrowRight, ArrowUpRight, Check, ChevronDown, ChevronRight,
  CircleCheck, Clock3, CloudDrizzle, Download, Headphones, Pause, Play, Plane, RadioTower,
  RotateCcw, Settings2, ShieldCheck, SlidersHorizontal, Users, Waypoints, X } from 'lucide-react';
import AirportMap from './AirportMap.jsx';
import { alternativeSummary, clockLabel, displayPlan, flightLabel, groupedChecks, latestReply,
  phaseLabel, planMetrics, reportFor, ROLES, ROLE_NAMES, validPlan } from './lib/coordination.js';
import { aircraftPosition } from './lib/movement.js';

const ROLE_ICONS = { atc: RadioTower, pilot: Headphones, ground: Users };
const ROLE_JOBS = { atc: 'Arrival spacing & surface access', pilot: 'Fuel, comfort & connections', ground: 'Stands, crews & turnaround' };
const VERDICTS = { ACCEPT: 'Accepted', COUNTER: 'Counteroffer', REJECT: 'Rejected' };

async function getJson(url, options={}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    if (response.status === 409) throw new Error('Another coordination run is active. Wait for it to finish, then retry.');
    if (response.status === 503) throw new Error('The coordination service is not configured. Ask the backend owner to check its settings.');
    throw new Error('Could not reach the coordination service. Start the backend, then retry.');
  }
  return response.json();
}

function Status({ verdict, children, tone }) {
  const cls = tone || (verdict === 'ACCEPT' ? 'positive' : verdict === 'COUNTER' ? 'warning' : verdict === 'REJECT' ? 'negative' : 'neutral');
  const Icon = cls === 'positive' ? Check : cls === 'negative' ? X : cls === 'warning' ? ArrowUpRight : Clock3;
  return <span className={`status status-${cls}`}><Icon size={12}/>{children || VERDICTS[verdict]}</span>;
}

function AgentRow({ role, bundle, phase, confirms, waiting, currentPlan }) {
  const [open, setOpen] = useState(false);
  const index = ROLES.indexOf(role), Icon = ROLE_ICONS[role];
  let message = null, label = 'Ready', tone = 'neutral';
  if (waiting) label = 'Awaiting result';
  else if (phase === 1) label = 'Checks complete';
  else if (phase === 2 || phase === 3) message = latestReply(bundle, role, 1);
  else if (phase === 4) {
    if (index < confirms) message = latestReply(bundle,role,2) || latestReply(bundle,role);
    else label = 'Reviewing';
  } else if (phase === 5) message = latestReply(bundle, role);
  if (message) label = VERDICTS[message.result.decision.verdict];
  const report = reportFor(bundle, currentPlan.plan_id, role);
  const groups = groupedChecks(report);
  const failures = report?.checks.filter((c) => c.severity === 'HARD' && ['FAIL','UNKNOWN'].includes(c.status)).length || 0;
  const hardCount = report?.checks.filter((c) => c.severity === 'HARD').length || 0;
  const reason = waiting ? 'The three agents are coordinating. Their individual results appear when this run finishes.'
    : message?.result.decision.reason || (phase === 0 ? 'Ready to independently review the proposed plan.'
      : phase === 1 ? `${hardCount} operational checks evaluated${failures ? `; ${failures} need attention` : '.'}`
      : 'Independently reviewing the revised arrival and stand assignments.');
  return <section className={`agent-row ${open ? 'agent-open' : ''}`}>
    <button className="agent-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
      <span className={`agent-avatar agent-avatar-${role}`}><Icon size={17}/></span>
      <span className="agent-heading"><strong>{ROLE_NAMES[role]}</strong><span>{ROLE_JOBS[role]}</span></span>
      <Status verdict={message?.result.decision.verdict} tone={!message ? tone : undefined}>{label}</Status>
      <ChevronDown size={13} className="agent-chevron"/>
    </button>
    <p className="agent-reason">{reason}</p>
    {open && <div className="agent-checks">
      <div className="check-scope">{currentPlan.plan_id} · {waiting ? 'Previous run’s checks' : 'Applied checks'}</div>
      {groups.map((group) => <details key={group.rule} className={`check-group check-${group.status.toLowerCase()}`}>
        <summary>{group.status === 'PASS' ? <Check size={13}/> : <AlertTriangle size={13}/>}<span>{group.label}</span><span>{group.status === 'PASS' ? 'Pass' : group.status === 'FAIL' ? 'Not met' : 'Unknown'}</span><ChevronRight size={12}/></summary>
        <div className="check-detail">{group.checks.map((check) => <div key={check.check_id}>
          <strong>{check.flight_ids.join(' + ') || 'Scenario'}</strong><p>{check.observed}</p><span>{check.required}</span>
        </div>)}</div>
      </details>)}
      <p className="evidence-note">Checked by rules. Explanation is the agent’s stated reason{bundle.kind === 'recorded-scripted-replay' ? ' in this scripted replay' : ''}.</p>
    </div>}
  </section>;
}

function downloadBundle(bundle) {
  const blob = new Blob([JSON.stringify(bundle,null,2)], {type:'application/json'});
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = `groundline-${bundle.result.run_id}.json`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function App() {
  const [layout,setLayout] = useState(null), [bundle,setBundle] = useState(null), [loadError,setLoadError] = useState('');
  const [selected,setSelected] = useState('F1'), [phase,setPhase] = useState(5), [confirms,setConfirms] = useState(3);
  const [clock,setClock] = useState(9.4), clockRef = useRef(9.4);
  const reduceMotion = useRef(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [playing,setPlaying] = useState(!reduceMotion.current), [speed,setSpeed] = useState(20);
  const [mode,setMode] = useState('replay'), [scenarioKind,setScenarioKind] = useState('base');
  const [replaying,setReplaying] = useState(false), [waiting,setWaiting] = useState(false), [error,setError] = useState('');
  const [connection,setConnection] = useState(null), [reviewed,setReviewed] = useState(false), [recordOpen,setRecordOpen] = useState(false);
  const [inspectedPlan,setInspectedPlan] = useState(null);
  const timers = useRef([]), planPanel = useRef(null), controller = useRef(null);

  useEffect(() => {
    Promise.all([getJson('/data/dfw-layout.json'),getJson('/data/demo-run.json')]).then(([map,run])=>{setLayout(map);setBundle(run);})
      .catch(()=>setLoadError('The draft could not load its airport map or recorded scenario. Reload to try again.'));
    return () => { timers.current.forEach(clearTimeout); controller.current?.abort(); };
  },[]);

  useEffect(() => {
    if (!playing || !bundle || waiting) return;
    let frame, previous, lastText = 0;
    function tick(timestamp) {
      if (previous !== undefined) clockRef.current = Math.min(40,clockRef.current+Math.min((timestamp-previous)/1000,.1)*speed/60);
      previous = timestamp;
      if (timestamp-lastText > 120) { setClock(clockRef.current); lastText=timestamp; }
      if (clockRef.current >= 40) { setPlaying(false); setClock(40); }
      else frame = requestAnimationFrame(tick);
    }
    frame=requestAnimationFrame(tick);
    return ()=>cancelAnimationFrame(frame);
  },[playing,speed,bundle,waiting]);

  function seek(minute) { clockRef.current=minute; setClock(minute); }
  function resetTimers() { timers.current.forEach(clearTimeout); timers.current=[]; }
  function toggleRecord() {
    setRecordOpen(!recordOpen);
    setTimeout(()=>document.querySelector('.decision-record')?.scrollIntoView({behavior:reduceMotion.current?'instant':'smooth',block:'nearest'}),0);
  }
  function replay() {
    resetTimers(); setReviewed(false); setInspectedPlan(null); setReplaying(true); setPlaying(false); seek(9.4);setPhase(0);setConfirms(0);
    [[600,1],[2000,2],[3800,3],[5100,4],[7700,5]].forEach(([delay,p])=>timers.current.push(setTimeout(()=>{
      setPhase(p);if(p===5){setReplaying(false);setConfirms(3);setPlaying(!reduceMotion.current && bundle.result.outcome!=='ESCALATED');}
    },delay)));
    [5650,6350,7000].forEach((delay,i)=>timers.current.push(setTimeout(()=>setConfirms(i+1),delay)));
  }

  async function changeScenario(kind) {
    const previousKind=scenarioKind;
    resetTimers();setReplaying(false);setError('');setReviewed(false);setInspectedPlan(null);setScenarioKind(kind);setPlaying(false);seek(9.4);
    try {
      const path = kind === 'crew' ? 'demo-crew.json' : kind === 'closed' ? 'demo-closed.json' : 'demo-run.json';
      const data=await getJson(`/data/${path}`);setBundle(data);setPhase(5);setConfirms(3);
      setPlaying(!reduceMotion.current && data.result.outcome==='CONSENSUS');
    } catch { setScenarioKind(previousKind);setError('This recorded drill could not load. Choose the original scenario to try again.'); }
  }

  async function connect(value) {
    setMode(value);setError('');
    if(value==='backend') {
      setConnection('connecting');
      try {const health=await getJson('/api/health');setConnection(health.mode || 'connected');}
      catch(err){setConnection('unavailable');setError(err.message);}
    }
  }

  async function runBackend() {
    resetTimers();setReplaying(false);setWaiting(true);setError('');setReviewed(false);setPlaying(false);
    controller.current=new AbortController();const timeout=setTimeout(()=>controller.current.abort(),45000);
    try {
      const result=await getJson('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(bundle.scenario),signal:controller.current.signal});
      const events=await getJson(`/api/runs/${result.run_id}/events`);
      setBundle({kind:'backend-result',scenario:bundle.scenario,result,events});setPhase(5);setConfirms(3);setInspectedPlan(null);
      if(result.outcome==='INPUT_ERROR')setError('The scenario could not be validated. Open the decision record for details; the input needs review.');
    } catch(err){setError(err.name==='AbortError'?'The run did not return in time. Check the backend before retrying.':err.message);}
    finally {clearTimeout(timeout);setWaiting(false);}
  }

  if(loadError)return <main className="load-state" role="alert"><AlertTriangle size={24}/><h1>Unable to load the draft</h1><p>{loadError}</p><button className="primary-button" onClick={()=>location.reload()}>Reload draft</button></main>;
  if(!layout || !bundle)return <main className="load-state" aria-busy="true"><div className="brand-icon"/><h1>Loading DFW surface</h1><p>Preparing the airport map and recorded coordination.</p></main>;

  const scenario=bundle.scenario, result=bundle.result, currentPlan=displayPlan(bundle,phase);
  const source=scenario.shared.source_rows[0].raw;
  const focus=currentPlan.assignments.find((a)=>a.flight_id===selected);
  const limits=scenario.pilot.limits.find((l)=>l.flight_id===selected);
  const atTerminal=aircraftPosition(layout,focus,scenario.shared,clock);
  const terminalOutcome=phase===5 && !waiting;
  const consensus=terminalOutcome && result.outcome==='CONSENSUS';
  const fallback=terminalOutcome && result.outcome==='FALLBACK';
  const escalated=terminalOutcome && ['ESCALATED','INPUT_ERROR'].includes(result.outcome);
  const anyCrewDelay=scenario.ground.crews.some((c)=>c.available_windows[0]?.start_min>0);
  const totalConnections=scenario.pilot.limits.reduce((n,l)=>n+l.connecting_passengers,0);
  const preserved=Math.max(0,totalConnections-(result.metrics?.missed_connections || 0));
  const alternatives=scenario.plans.filter((p)=>p.plan_id!==result.selected_plan_id);
  const title=waiting ? 'Coordination in progress' : phaseLabel(bundle,phase);
  const reviewLabel = reviewed ? 'Reviewed in this draft' : 'Mark recommendation reviewed';

  return <div className="application">
    <header className="app-header">
      <a className="brand" href="/" aria-label="Groundline dashboard"><span className="brand-icon" aria-hidden="true"><i/><i/><i/></span>groundline<span className="brand-period">.</span></a>
      <span className="header-divider"/>
      <div className="airport-title"><strong>DFW</strong><span>Dallas Fort Worth<span className="airport-title-extra"> International</span></span></div>
      <span className="header-surface">Surface coordination</span>
      <div className="header-right"><span className="session-badge"><span/>{mode==='replay'?'Recorded demo':connection==='live'?'Backend · live models':connection==='offline'?'Backend · scripted':'Backend mode'}</span>
        <button className={`text-button record-button ${recordOpen?'active':''}`} onClick={toggleRecord}><Clock3 size={15}/>Decision record</button>
        <details className="connection-control"><summary aria-label="Connection settings"><Settings2 size={18}/></summary><div className="connection-panel"><strong>Coordination source</strong><p>Review the recorded demo or run your local backend.</p><select aria-label="Coordination source" value={mode} onChange={(e)=>connect(e.target.value)}><option value="replay">Recorded demo</option><option value="backend">Connected backend</option></select>{mode==='backend'&&<span className={`connection-note ${connection==='unavailable'?'negative':''}`}>{connection==='unavailable'?'Start the local Python backend and retry.':connection==='connecting'?'Connecting…':`Connected · ${connection==='live'?'live models':'scripted responses'}`}</span>}</div></details>
      </div>
    </header>

    <section className="conditions-bar" aria-label="Airport scenario conditions">
      <div className="condition condition-disruption"><CloudDrizzle size={19}/><span><span className="condition-label">Historical disruption</span><strong>Weather delay <span className="condition-value">+{source.WEATHER_DELAY} min</span></strong></span></div>
      <div className="condition"><Waypoints size={18}/><span><span className="condition-label">Surface restriction</span><strong className="amber">Route T2 unavailable</strong></span></div>
      <div className="condition"><RadioTower size={18}/><span><span className="condition-label">Runway window</span><strong>{scenario.atc.runway_open_windows.length?'Open for arrivals':'No open window'}<span className={`inline-dot ${scenario.atc.runway_open_windows.length?'mint':'rose'}`}/></strong></span></div>
      <div className="condition"><Users size={18}/><span><span className="condition-label">Ground resources</span><strong>{scenario.ground.gates.length} stands <span className="condition-separator">/</span> {anyCrewDelay?'Crew C2 delayed':`${scenario.ground.crews.length} crews available`}</strong></span></div>
      <span className="conditions-note">Scenario conditions<br/><span>Not live telemetry</span></span>
    </section>

    {error&&<div className="error-banner" role="alert"><AlertTriangle size={16}/><span>{error}</span><button aria-label="Dismiss message" onClick={()=>setError('')}><X size={16}/></button></div>}

    <main className="workspace">
      <section className="surface-workspace" aria-labelledby="surface-heading">
        <div className="surface-heading"><div><h1 id="surface-heading">Airport surface</h1><span>Selected flight and proposed recovery route</span></div><div className="map-mode-label"><span/>Airport layout</div></div>
        <div className="map-frame">
          <AirportMap layout={layout} bundle={bundle} plan={currentPlan} selected={selected} onSelect={setSelected} clock={clock} clockRef={clockRef} playing={playing} phase={phase} waiting={waiting}/>
          <div className="selected-flight">
            <div className="selected-flight-head"><span><Plane size={15}/><strong>{flightLabel(scenario,selected)}</strong></span><span className="selected-flight-label">Selected flight</span></div>
            <div className="flight-route"><span>{selected==='F1'?source.ORIGIN_AIRPORT:'SIM'}</span><ArrowRight size={15}/><span>DFW</span><span className="flight-route-state">{atTerminal.phase}</span></div>
            <div className="flight-assignment"><span>Arrival <strong>T+{clockLabel(focus.landing_min)}</strong></span><span>Stand <strong>{focus.gate_id}</strong></span><span>{selected==='F1'?'Source row 76':'Simulated traffic'}</span></div>
          </div>
          <div className={`map-plan-pill ${escalated?'map-plan-pill-warning':''}`}><span className="tiny-route-line"/>{waiting?'Previous recommendation':escalated?'No validated route':phase<3?'Initial plan':'Proposed plan'} <strong>{escalated?'—':currentPlan.plan_id}</strong></div>
        </div>

        <section className="playback-bar" aria-label="Simulation playback">
          <button className="playback-button" aria-label={playing?'Pause aircraft motion':'Play aircraft motion'} aria-pressed={playing} onClick={()=>{if(clockRef.current>=40)seek(0);setPlaying(!playing);}} disabled={replaying || waiting || escalated}>{playing?<Pause size={15} fill="currentColor"/>:<Play size={15} fill="currentColor"/>}</button>
          <span className="playback-time">T+{clockLabel(clock)}</span>
          <input aria-label="Simulation time in minutes" type="range" min="0" max="40" step=".05" value={clock} onChange={(e)=>seek(+e.target.value)} disabled={replaying || waiting || escalated}/>
          <span className="playback-end">40:00</span>
          <select value={speed} aria-label="Aircraft playback speed" onChange={(e)=>setSpeed(+e.target.value)}><option value="10">10×</option><option value="20">20×</option><option value="40">40×</option></select>
          <span className="playback-caption">Motion simulation</span>
        </section>

        <section className="traffic" aria-label="Scenario aircraft">
          <div className="traffic-heading"><span>Scenario traffic</span><span>{scenario.shared.flights.length} aircraft</span></div>
          <div className="traffic-list">{currentPlan.assignments.map((a)=>{
            const position=aircraftPosition(layout,a,scenario.shared,clock);
            return <button key={a.flight_id} className={`traffic-flight ${a.flight_id===selected?'traffic-selected':''}`} aria-pressed={a.flight_id===selected} onClick={()=>setSelected(a.flight_id)}>
              <span className="traffic-plane"><Plane size={19}/></span><span className="traffic-identity"><strong>{flightLabel(scenario,a.flight_id)}</strong><span>{a.flight_id==='F1'?`${source.ORIGIN_AIRPORT} → ${source.DESTINATION_AIRPORT}`:'Simulated traffic'}</span></span><span className="traffic-flight-state"><span>{position.phase}</span><strong>{a.gate_id}<ChevronRight size={12}/></strong></span>
            </button>;
          })}</div>
        </section>
      </section>

      <aside className="coordination-panel" ref={planPanel} aria-labelledby="coordination-heading">
        <div className="coordination-scroll">
        <div className="coordination-title"><h2 id="coordination-heading">Recovery coordination</h2><span className="ai-label"><Waypoints size={12}/>3 AI agents</span></div>
        <div className={`coordination-stage ${escalated?'stage-escalated':''}`} aria-live="polite">
          <div className="stage-symbol">{consensus?<ShieldCheck size={21}/>:escalated?<AlertTriangle size={21}/>:fallback?<Waypoints size={21}/>:<RadioTower size={21}/>}</div>
          <div><h3>{title}</h3><p>{waiting?'Waiting for the completed run':consensus?'All three agents accepted the same plan':fallback?'A checked plan is available without consensus':escalated?'No plan is ready for operational review':phase<3?'Reviewing the initial arrival and stand plan':'Reviewing the revised arrival and stand plan'}</p></div>
        </div>
        <div className="round-tracker"><span className={phase>=0?'round-done':''}>Initial plan</span><span className={`tracker-line ${phase>=3?'tracker-line-done':''}`}/><span className={phase>=3?'round-done':''}>Revised plan</span><span className={`tracker-line ${phase===5?'tracker-line-done':''}`}/><span className={phase===5?'round-done':''}>{fallback?'Fallback':escalated?'Escalation':'Agreement'}</span></div>

        <div className="agents-section"><div className="section-label"><h3>Independent agent review</h3><span>{mode==='replay'?'Recorded replay':waiting?'Running':bundle.kind==='backend-result'?'Run results':'Recorded replay'}</span></div>
          {ROLES.map((role)=><AgentRow key={`${role}-${result.run_id}`} role={role} bundle={bundle} phase={phase} confirms={confirms} waiting={waiting} currentPlan={currentPlan}/>)}
        </div>

        <section className="why-section" aria-labelledby="why-heading">
          <div className="section-label"><h3 id="why-heading">Why this plan?</h3><span className="plan-id">{result.selected_plan_id || 'No selection'}</span></div>
          {!escalated&&result.metrics&&phase>=3&&!waiting ? <><p className="why-headline">{anyCrewDelay?'The available crew can support this plan.':preserved===totalConnections?'Both connections stay on time.':'Meets the limits, with connection trade-offs.'}</p>
            <div className="plan-outcomes"><div><Clock3 size={14}/><strong>+{result.metrics.additional_delay_min} min</strong><span>Total arrival shift</span></div><div><Users size={14}/><strong>{preserved}/{totalConnections}</strong><span>Connections kept</span></div><div><Users size={14}/><strong>{result.metrics.overtime_min} min</strong><span>Crew overtime</span></div></div>
          </> : <p className={escalated?'escalation-explanation':'pending-explanation'}>{waiting?'The previous recommendation stays visible on the map until a new run is complete.':phase<3?'A revised recommendation follows the independent agent reviews.':result.outcome==='INPUT_ERROR'?'The scenario needs correction before the agents can review it.':'No candidate passed every operational constraint. Review the runway window or provide another plan.'}</p>}
          <div className="alternatives">{alternatives.map((p)=>{
            const summary=alternativeSummary(bundle,p.plan_id);
            return <button key={p.plan_id} className={`alternative ${inspectedPlan===p.plan_id?'alternative-open':''}`} aria-expanded={inspectedPlan===p.plan_id} onClick={()=>setInspectedPlan(inspectedPlan===p.plan_id?null:p.plan_id)}><span className="alternative-id">{p.plan_id}</span><span className="alternative-copy"><strong>{p.plan_id===scenario.initial_plan_id?'Initial plan':summary.eligible?'Other feasible plan':'Alternative plan'}</strong><span>{summary.text}</span></span><span className={`alternative-status ${summary.eligible?'':'alternative-rejected'}`}>{summary.eligible?'Feasible':'Ruled out'}</span><ChevronRight size={13}/></button>;
          })}</div>
          {inspectedPlan&&<div className="alternative-evidence"><strong>{inspectedPlan} · Decision evidence</strong>{alternativeSummary(bundle,inspectedPlan).failures.length?alternativeSummary(bundle,inspectedPlan).failures.slice(0,3).map((c)=><p key={c.check_id}><span>{c.observed}</span><small>Required: {c.required}</small></p>):<p>This plan passes the declared hard checks. The coordinator compares throughput, connections and delay before the other preferences. Its preference order is fixed.</p>}</div>}
        </section>

        {recordOpen&&<section className="decision-record"><div className="section-label"><h3>Decision record</h3><button aria-label="Close decision record" onClick={()=>setRecordOpen(false)}><X size={14}/></button></div><dl><div><dt>Source</dt><dd>AA 1344 · CSV row 76 · 2015</dd></div><div><dt>Outcome</dt><dd>{result.outcome}</dd></div><div><dt>Reason</dt><dd>{result.reason_code.replaceAll('_',' ').toLowerCase()}</dd></div><div><dt>Scope</dt><dd>Simulated operating conditions</dd></div><div><dt>Model calls</dt><dd>{result.model_calls_attempted} attempted · {result.retries} retries</dd></div></dl><button className="text-button" onClick={()=>downloadBundle(bundle)}><Download size={14}/>Export original decision evidence</button></section>}

        </div>
        <div className="panel-footer"><span>{result.rounds_completed} rounds<span>·</span>{result.agent_invocations} agent reviews<span>·</span>{result.model_calls_attempted} model calls</span><button className={`text-button mobile-record-button ${recordOpen?'active':''}`} onClick={toggleRecord}><Clock3 size={14}/>Decision record<ChevronRight size={13}/></button><button className={`review-button ${reviewed?'reviewed':''}`} onClick={()=>setReviewed(true)} disabled={!terminalOutcome || escalated || reviewed}>{reviewed?<Check size={15}/>:<ShieldCheck size={15}/>} {reviewLabel}</button><p>{reviewed?'Local review recorded in this draft.':'Recommendation for qualified human review.'} No airport instructions are sent.</p></div>
      </aside>
    </main>

    <footer className="scenario-toolbar"><div className="scenario-description"><span className="scenario-status"/><span><strong>{scenarioKind==='crew'?'Crew availability disruption':scenarioKind==='closed'?'No runway availability':'Weather & surface disruption'}</strong><span>{scenarioKind==='base'?'AA1344 · DEN → DFW':'Simulation drill'}<span className="footer-dot">·</span>{scenario.shared.flights.length} planned arrivals</span></span></div>
      <div className="scenario-actions"><label className="scenario-select"><SlidersHorizontal size={14}/><select value={scenarioKind} aria-label="Select disruption scenario" onChange={(e)=>changeScenario(e.target.value)} disabled={waiting || replaying}><option value="base">Original scenario</option><option value="crew">Crew delay drill</option><option value="closed">No runway drill</option></select></label><button className="primary-button" onClick={mode==='replay'?replay:runBackend} disabled={waiting || replaying}>{replaying?<RadioTower size={15}/>:mode==='replay'?<RotateCcw size={15}/>:<Waypoints size={15}/>} {waiting?'Coordinating…':replaying?'Replaying coordination…':mode==='replay'?'Replay coordination':'Run coordination'}<ArrowRight size={15}/></button></div>
    </footer>
    <div className="draft-disclosure"><span>INTERACTIVE REVIEW DRAFT</span><span>{bundle.kind==='recorded-scripted-replay'?'Scripted decisions through the real backend · Recorded events, not live agent progress':'Connected run · Original backend decisions and check evidence'}</span><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">Map data & attribution<ArrowUpRight size={11}/></a></div>
  </div>;
}
