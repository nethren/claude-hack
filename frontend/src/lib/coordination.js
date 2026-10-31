import { FLIGHT_IDENTITIES } from './flight-identities.js';

export const ROLES = ['atc', 'pilot', 'ground'];
export const ROLE_NAMES = { atc: 'ATC agent', pilot: 'Pilot agent', ground: 'Ground agent' };
export const RULE_LABELS = {
  ATC_RUNWAY: 'Runway availability', ATC_WAKE: 'Arrival spacing', ATC_TAXI: 'Taxiway access',
  PILOT_EARLIEST: 'Earliest arrival', PILOT_FUEL: 'Fuel reserves', PILOT_TURBULENCE: 'Turbulence limits',
  PILOT_CONNECTION: 'Passenger connections', GROUND_GATE: 'Stand availability',
  GROUND_TURN: 'Turnaround time', GROUND_CREW: 'Crew availability',
};

export function reportFor(bundle, planId, role) {
  return bundle.result.candidate_reports?.[planId]?.find((r) => r.role === role) || null;
}

export function hardPass(report) {
  const hard = report?.checks.filter((c) => c.severity === 'HARD') || [];
  return hard.length > 0 && hard.every((c) => ['PASS', 'NOT_APPLICABLE'].includes(c.status));
}

export function validPlan(bundle, planId) {
  const reports = bundle.result.candidate_reports?.[planId] || [];
  return reports.length === 3 && reports.every((r) => hardPass(r) && r.checks.every((c) => c.status !== 'UNKNOWN'));
}

export function planMetrics(bundle, planId) {
  return Object.assign({}, ...(bundle.result.candidate_reports?.[planId] || []).map((r) => r.metrics));
}

export function replies(bundle, round) {
  return (bundle.events || []).filter((e) => e.type === 'AGENT_REPLIED' && (!round || e.payload.reply.round_index === round))
    .map((e) => e.payload.reply);
}

export function latestReply(bundle, role, round) {
  return replies(bundle, round).filter((r) => r.role === role).at(-1) || null;
}

export function displayPlan(bundle, phase) {
  const initial = bundle.scenario.plans.find((p) => p.plan_id === bundle.scenario.initial_plan_id);
  return phase < 3 ? initial : bundle.result.selected_plan || initial;
}

export function groupedChecks(report) {
  const groups = new Map();
  for (const check of report?.checks || []) {
    if (!groups.has(check.rule_id)) groups.set(check.rule_id, []);
    groups.get(check.rule_id).push(check);
  }
  return [...groups].map(([rule, checks]) => ({ rule, label: RULE_LABELS[rule] || rule,
    status: checks.some((c) => c.status === 'FAIL') ? 'FAIL' : checks.some((c) => c.status === 'UNKNOWN') ? 'UNKNOWN' : 'PASS',
    checks,
  }));
}

export function alternativeSummary(bundle, planId) {
  const checks = (bundle.result.candidate_reports?.[planId] || []).flatMap((r) => r.checks);
  const failures = [...new Set(checks.filter((c) => c.severity === 'HARD' && c.status === 'FAIL').map((c) => RULE_LABELS[c.rule_id]))];
  if (failures.length) return { eligible: false, text: failures.join(' · '), failures: checks.filter((c) => c.severity === 'HARD' && c.status === 'FAIL') };
  if (!validPlan(bundle, planId)) return { eligible: false, text: 'Some constraints could not be verified', failures: [] };
  const own = planMetrics(bundle, planId);
  const chosen = bundle.result.metrics;
  const details = [];
  if (own.missed_connections) details.push(`${own.missed_connections} missed connections`);
  const extra = chosen ? own.additional_delay_min - chosen.additional_delay_min : null;
  details.push(extra > 0 ? `${extra} min more delay` : `${own.additional_delay_min} min added delay`);
  return { eligible: true, text: details.join(' · '), failures: [] };
}

export function flightLabel(scenario, flightId) {
  const f = scenario.shared.flights.find((f) => f.flight_id === flightId);
  const source = scenario.shared.source_rows.find((r) => r.source_id === f?.source_id);
  return source ? `${source.raw.AIRLINE}${source.raw.FLIGHT_NUMBER}` : FLIGHT_IDENTITIES[flightId]?.callsign || flightId;
}

export function flightIdentity(scenario, flightId) {
  const f = scenario.shared.flights.find((f) => f.flight_id === flightId);
  const source = scenario.shared.source_rows.find((r) => r.source_id === f?.source_id);
  return source ? {callsign:flightLabel(scenario,flightId),origin:source.raw.ORIGIN_AIRPORT,destination:source.raw.DESTINATION_AIRPORT,csv_row_number:source.csv_row_number} : FLIGHT_IDENTITIES[flightId];
}

export function clockLabel(minute) {
  const seconds = Math.floor(Math.max(0, minute) * 60);
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

export function phaseLabel(bundle, phase) {
  if (phase === 0) return 'Initial plan';
  if (phase === 1) return 'Checking constraints';
  if (phase === 2) return 'Counteroffers exchanged';
  if (phase === 3) return 'Revised plan proposed';
  if (phase === 4) return 'Confirming agreement';
  return { CONSENSUS: 'Agreement reached', FALLBACK: 'Checked fallback', ESCALATED: 'Controller review needed', INPUT_ERROR: 'Scenario needs attention' }[bundle.result.outcome];
}

export function revisedScenario(base, kind) {
  const scenario = structuredClone(base);
  if (kind === 'crew') {
    scenario.scenario_version = 2;
    scenario.ground.crews.find((c) => c.crew_id === 'C2').available_windows[0].start_min = 20;
  } else if (kind === 'closed') {
    scenario.scenario_version = 3;
    scenario.atc.runway_open_windows = [];
  }
  return scenario;
}
