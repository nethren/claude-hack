import { memo, useEffect, useRef, useState } from 'react';
import { Crosshair, Eye, EyeOff, Minus, Plus } from 'lucide-react';
import { aircraftPosition, HEIGHT, pathString, project, routeFor, WIDTH } from './lib/movement.js';
import { clockLabel, flightLabel } from './lib/coordination.js';

const Geometry = memo(function Geometry({ layout }) {
  return <g className="airport-geometry">
    {['apron', 'road', 'taxiway', 'runway', 'terminal'].map((type) => <g key={type} className={`geometry-${type}`}>
      {layout.features.filter((f) => f.type === type).map((f) => {
        const points = f.coordinates.map(project);
        return <g key={f.id} className={f.construction ? 'under-construction' : ''}>
          {type === 'runway' && <path className="runway-shoulder" d={pathString(points)} />}
          <path d={pathString(points, type === 'apron' || type === 'terminal')} />
          {type === 'runway' && <path className="runway-center" d={pathString(points)} />}
        </g>;
      })}
    </g>)}
    {layout.features.filter((f) => f.type === 'runway' && f.coordinates.length > 5).map((f) => {
      const ends = [f.coordinates[0], f.coordinates.at(-1)].sort((a,b) => b[1]-a[1]);
      return ends.map((p,i) => { const [x,y] = project(p); return <text key={`${f.id}-${i}`} className="runway-label" x={x} y={y+(i ? 24 : -16)}>{f.ref.split('/')[i]}</text>; });
    })}
    {layout.terminals.map((terminal) => <g key={terminal.name} transform={`translate(${terminal.point[0]},${terminal.point[1]})`}>
      <circle className="terminal-disc" r="11" /><text className="terminal-letter" y="3.5">{terminal.name}</text>
    </g>)}
    <text className="parkway-label" x="545" y="438" transform="rotate(-90 545 438)">INTERNATIONAL PARKWAY</text>
  </g>;
});

function PlaneShape() {
  return <path d="M0-13.5 2-10 2-3 11 3.7 11 6 2 3.4 2 9 5.2 12 5.2 13.5 0 11.7-5.2 13.5-5.2 12-2 9-2 3.4-11 6-11 3.7-2-3-2-10Z" />;
}

export default function AirportMap({ layout, bundle, plan, selected, onSelect, clock, clockRef, playing, phase, waiting }) {
  const root = useRef(null), aircraft = useRef({}), icons = useRef({});
  const [camera, setCamera] = useState({ zoom: 1, x: 0, y: 0 });
  const [routes, setRoutes] = useState(true), [hovered, setHovered] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 900, height: 650 });
  const drag = useRef(null);
  const assignment = plan.assignments.find((a) => a.flight_id === selected) || plan.assignments[0];
  const route = routeFor(layout, assignment);
  const proposed = bundle.result.selected_plan && phase >= 3;
  const noPlan = ['ESCALATED', 'INPUT_ERROR'].includes(bundle.result.outcome) && phase >= 5;

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setDimensions(entry.contentRect));
    observer.observe(root.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let frame;
    function paint() {
      for (const a of plan.assignments) {
        const p = aircraftPosition(layout, a, bundle.scenario.shared, clockRef.current);
        aircraft.current[a.flight_id]?.setAttribute('transform', `translate(${p.x} ${p.y})`);
        aircraft.current[a.flight_id]?.setAttribute('visibility', p.visible ? 'visible' : 'hidden');
        icons.current[a.flight_id]?.setAttribute('transform', `rotate(${p.heading})`);
      }
      if (playing) frame = requestAnimationFrame(paint);
    }
    paint();
    return () => cancelAnimationFrame(frame);
  }, [plan, layout, bundle.scenario.shared, clockRef, playing, clock]);

  function zoom(delta) { setCamera((c) => ({ ...c, zoom: Math.max(.85, Math.min(2.4, c.zoom+delta)) })); }
  function pointerDown(event) {
    if (event.target.closest('[role="button"]') || event.button !== 0) return;
    drag.current = { x: event.clientX, y: event.clientY, initial: camera };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function pointerMove(event) {
    if (!drag.current) return;
    const scale = Math.min(dimensions.width/WIDTH, dimensions.height/HEIGHT);
    const dx = (event.clientX-drag.current.x)/scale, dy = (event.clientY-drag.current.y)/scale;
    setCamera({ ...drag.current.initial, x: Math.max(-300, Math.min(300, drag.current.initial.x+dx)), y: Math.max(-260, Math.min(260, drag.current.initial.y+dy)) });
  }
  const hoverAssignment = plan.assignments.find((a) => a.flight_id === hovered);
  const hoverPosition = hoverAssignment && aircraftPosition(layout, hoverAssignment, bundle.scenario.shared, clock);
  const scale = Math.min(dimensions.width/WIDTH, dimensions.height/HEIGHT);
  const hoverX = hoverPosition ? (WIDTH/2+(hoverPosition.x-WIDTH/2)*camera.zoom+camera.x)*scale+(dimensions.width-WIDTH*scale)/2 : 0;
  const hoverY = hoverPosition ? (HEIGHT/2+(hoverPosition.y-HEIGHT/2)*camera.zoom+camera.y)*scale+(dimensions.height-HEIGHT*scale)/2 : 0;

  return <div className="map-canvas" ref={root}>
    <div className="map-ident"><span className="map-status-dot" /> Surface movement <span className="map-sim-label">SIMULATED</span></div>
    <div className="north-marker"><span>N</span><svg viewBox="0 0 24 30" width="20" height="28" aria-hidden="true"><path d="M12 2 19 24 12 19 5 24Z" fill="none" stroke="currentColor" strokeWidth="1.2" /></svg></div>
    <svg className="surface-map" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} aria-label="Real Dallas Fort Worth runway and taxiway layout with simulated aircraft" onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
      <defs>
        <pattern id="map-grid" width="65" height="65" patternUnits="userSpaceOnUse"><path d="M65 0H0V65" fill="none" stroke="var(--map-grid)" strokeWidth=".6" /></pattern>
        <filter id="route-light" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" /></filter>
      </defs>
      <rect width={WIDTH} height={HEIGHT} fill="url(#map-grid)" />
      <g className="world" transform={`translate(${WIDTH/2+camera.x} ${HEIGHT/2+camera.y}) scale(${camera.zoom}) translate(${-WIDTH/2} ${-HEIGHT/2})`}>
        <g className="range-rings"><circle cx="550" cy="390" r="210" /><circle cx="550" cy="390" r="370" /><path d="M538 390h24m-12-12v24" /></g>
        <Geometry layout={layout} />
        <g className="scenario-restriction" transform="translate(674 470)">
          <path d="M-10-10 10 10m0-20-20 20" /><path className="restriction-zone" d="M-17-19h34v38h-34Z" />
          <text x="23" y="-2">T2 UNAVAILABLE</text><text className="restriction-sub" x="23" y="13">Scenario restriction</text>
        </g>
        {routes && !noPlan && <g className={`guidance ${proposed ? 'guidance-proposed' : 'guidance-initial'} ${waiting ? 'guidance-waiting' : ''}`}>
          {proposed && <path className="route-glow" d={pathString(route.surface)} filter="url(#route-light)" />}
          <path className="route-approach" d={pathString(layout.approaches[selected] || route.approach)} />
          <path className="route-line" d={pathString(route.surface)} />
          {route.surface.filter((_,i)=>i === 0 || i === Math.floor(route.surface.length/2)).map((p,i) => <circle className="route-waypoint" key={i} cx={p[0]} cy={p[1]} r="4" />)}
        </g>}
        {Object.entries(layout.stands).map(([id,p]) => <g key={id} className={`simulation-stand ${id === assignment.gate_id && !noPlan ? 'stand-selected' : ''}`} transform={`translate(${p[0]} ${p[1]})`}>
          <rect x="-8" y="-8" width="16" height="16" rx="2" /><path d="M-3 0h6m-3-3v6" />
          <text x="-13" y="-17" textAnchor="end">{id}</text>
        </g>)}
        {plan.assignments.map((a) => <g key={a.flight_id} ref={(node) => { aircraft.current[a.flight_id] = node; }}
          className={`aircraft ${a.flight_id === selected ? 'aircraft-selected' : ''}`} role="button" tabIndex="0"
          aria-label={`${flightLabel(bundle.scenario,a.flight_id)}, ${a.flight_id === selected ? 'selected flight' : 'inspect flight'}`}
          onClick={() => onSelect(a.flight_id)} onKeyDown={(e) => { if (['Enter',' '].includes(e.key)) { e.preventDefault(); onSelect(a.flight_id); } }}
          onMouseEnter={() => setHovered(a.flight_id)} onMouseLeave={() => setHovered(null)} onFocus={() => setHovered(a.flight_id)} onBlur={() => setHovered(null)}>
          <g transform={`scale(${1/(scale*camera.zoom)})`}>
          <circle className="aircraft-hit-area" r="23" />
          {a.flight_id === selected && <><circle className="aircraft-selection-ring" r="22" /><circle className="aircraft-selection-dot" cx="-20" cy="-10" r="2.3" /></>}
          <g className="aircraft-icon" ref={(node) => { icons.current[a.flight_id] = node; }}><PlaneShape /></g>
          <text className="aircraft-callsign" x="22" y="-7">{flightLabel(bundle.scenario,a.flight_id)}</text>
          <text className="aircraft-stand" x="22" y="7">{a.flight_id === selected ? `TO ${a.gate_id}` : 'SIM TRAFFIC'}</text>
          </g>
        </g>)}
      </g>
    </svg>
    {hovered && hoverPosition?.visible && <div className="aircraft-tooltip" role="tooltip" style={{ left: Math.max(12,Math.min(dimensions.width-248,hoverX+20)), top: Math.max(55,Math.min(dimensions.height-115,hoverY+22)) }}>
      <div><strong>{flightLabel(bundle.scenario, hovered)}</strong><span>{hovered === 'F1' ? 'Historical flight' : 'Simulated traffic'}</span></div>
      <p>{hoverPosition.phase}</p><dl><div><dt>Landing</dt><dd>T+{clockLabel(hoverAssignment.landing_min)}</dd></div><div><dt>Stand</dt><dd>{hoverAssignment.gate_id} <small>simulation</small></dd></div></dl>
    </div>}
    <div className="map-controls" aria-label="Map controls">
      <button aria-label="Zoom in" onClick={() => zoom(.2)} disabled={camera.zoom >= 2.4}><Plus size={17}/></button>
      <button aria-label="Zoom out" onClick={() => zoom(-.2)} disabled={camera.zoom <= .85}><Minus size={17}/></button>
      <span />
      <button aria-label="Reset map view" onClick={() => setCamera({ zoom:1,x:0,y:0 })}><Crosshair size={17}/></button>
      <button aria-label={routes ? 'Hide proposed route' : 'Show proposed route'} aria-pressed={routes} onClick={() => setRoutes(!routes)}>{routes ? <Eye size={17}/> : <EyeOff size={17}/>}</button>
    </div>
    <div className="map-legend"><span><i className="legend-plane"/>Selected aircraft</span><span><i className="legend-route"/>Proposed route</span></div>
    <div className="map-credit"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL</a><span>Real layout · illustrative routes & motion</span></div>
    <div className="map-scale"><span style={{width:500*13400/111320*scale*camera.zoom}}/>≈500 m</div>
  </div>;
}
