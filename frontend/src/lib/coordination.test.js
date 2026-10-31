import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { alternativeSummary, displayPlan, groupedChecks, latestReply, planMetrics, reportFor, validPlan } from './coordination.js';
import { aircraftPosition, routeFor } from './movement.js';

const data=(name)=>JSON.parse(fs.readFileSync(new URL(`../../public/data/${name}`,import.meta.url)));
const bundle=data('demo-run.json'), layout=data('dfw-layout.json');

test('default review fixture is a real backend-shaped result with explicit scripted provenance',()=>{
  assert.equal(bundle.kind,'recorded-scripted-replay');
  assert.equal(bundle.result.outcome,'CONSENSUS');
  assert.equal(bundle.result.selected_plan_id,'P1');
  assert.equal(bundle.result.agent_invocations,6);
  assert.equal(bundle.result.model_calls_attempted,0);
  assert.equal(Object.keys(bundle.scenario.shared.source_rows[0].raw).length,31);
});
test('initial failure and revised acceptance use actual rule reports',()=>{
  assert.equal(validPlan(bundle,'P0'),false);
  assert.equal(validPlan(bundle,'P1'),true);
  assert.equal(groupedChecks(reportFor(bundle,'P0','atc')).find((r)=>r.rule==='ATC_WAKE').status,'FAIL');
  assert.equal(groupedChecks(reportFor(bundle,'P1','atc')).find((r)=>r.rule==='ATC_WAKE').status,'PASS');
});
test('replay messages retain real backend verdicts across proposal changes',()=>{
  assert.equal(latestReply(bundle,'atc',1).result.decision.verdict,'COUNTER');
  assert.equal(latestReply(bundle,'pilot',1).result.decision.verdict,'ACCEPT');
  assert.equal(latestReply(bundle,'ground',2).result.decision.verdict,'ACCEPT');
  assert.equal(displayPlan(bundle,1).plan_id,'P0');
  assert.equal(displayPlan(bundle,4).plan_id,'P1');
});
test('alternative labels are evidence-based and feasible plans remain feasible',()=>{
  assert.equal(alternativeSummary(bundle,'P0').eligible,false);
  assert.match(alternativeSummary(bundle,'P0').text,/Arrival spacing/);
  assert.equal(alternativeSummary(bundle,'P2').eligible,true);
  assert.equal(alternativeSummary(bundle,'P2').text,'2 missed connections · 12 min more delay');
  assert.equal(planMetrics(bundle,'P1').overtime_min,2);
});
test('geographic overlay uses actual seven runway pairs and attributed map data',()=>{
  assert.equal(new Set(layout.features.filter((f)=>f.type==='runway').map((f)=>f.ref)).size,7);
  assert.ok(layout.features.filter((f)=>f.type==='taxiway').length>200);
  assert.equal(layout.metadata.license,'ODbL-1.0');
  assert.match(layout.metadata.note,/illustrative/);
});
test('aircraft moves during taxi and stays at the assigned simulated stand',()=>{
  const a=bundle.result.selected_plan.assignments[0], shared=bundle.scenario.shared;
  const before=aircraftPosition(layout,a,shared,a.landing_min+.2);
  const after=aircraftPosition(layout,a,shared,a.landing_min+1.2);
  assert.notDeepEqual([before.x,before.y],[after.x,after.y]);
  assert.equal(before.moving,true);
  const parked=aircraftPosition(layout,a,shared,13), later=aircraftPosition(layout,a,shared,17);
  assert.deepEqual([parked.x,parked.y],[later.x,later.y]);
  assert.equal(parked.moving,false);
  assert.deepEqual([parked.x,parked.y],layout.stands[a.gate_id]);
});
test('changed crew revision selects a different route/stand without altering the source row',()=>{
  const changed=data('demo-crew.json');
  assert.equal(changed.result.selected_plan_id,'P2');
  assert.equal(changed.scenario.scenario_version,2);
  assert.deepEqual(changed.scenario.shared.source_rows,bundle.scenario.shared.source_rows);
  assert.notDeepEqual(routeFor(layout,changed.result.selected_plan.assignments[0]),routeFor(layout,bundle.result.selected_plan.assignments[0]));
  assert.equal(validPlan(changed,'P1'),false);
});
test('completed traffic retires before a later flight reuses the same stand',()=>{
  const assignments=bundle.result.selected_plan.assignments;
  const previous=assignments.find((a)=>a.flight_id==='F1');
  const next=assignments.find((a)=>a.flight_id==='F3');
  assert.equal(previous.gate_id,next.gate_id);
  assert.equal(aircraftPosition(layout,previous,bundle.scenario.shared,24).visible,false);
  assert.equal(aircraftPosition(layout,next,bundle.scenario.shared,24).visible,true);
});
test('an impossible scenario has no selected route or fabricated consensus',()=>{
  const closed=data('demo-closed.json');
  assert.equal(closed.result.outcome,'ESCALATED');
  assert.equal(closed.result.selected_plan,null);
  assert.equal(closed.result.acceptances.length,0);
  assert.equal(validPlan(closed,'P1'),false);
});
