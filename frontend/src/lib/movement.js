export const WIDTH = 1000;
export const HEIGHT = 760;
export function project([lon, lat]) {
  return [(lon + 97.09) * Math.cos(32.9 * Math.PI / 180) * 13400, (32.926 - lat) * 13400];
}

export function pointOnPath(points, progress) {
  const lengths = points.slice(1).map((point, i) => Math.hypot(point[0] - points[i][0], point[1] - points[i][1]));
  const total = lengths.reduce((sum, n) => sum + n, 0);
  let left = Math.max(0, Math.min(1, progress)) * total;
  for (let i = 0; i < lengths.length; i++) {
    if (left <= lengths[i] || i === lengths.length - 1) {
      const a = points[i], b = points[i + 1];
      const t = lengths[i] ? Math.min(1, left / lengths[i]) : 0;
      return { x: a[0] + (b[0]-a[0])*t, y: a[1] + (b[1]-a[1])*t,
        heading: Math.atan2(b[1]-a[1], b[0]-a[0]) * 180/Math.PI + 90 };
    }
    left -= lengths[i];
  }
  return { x: points[0][0], y: points[0][1], heading: 0 };
}

export function routeFor(layout, assignment) {
  return layout.routes[assignment.gate_id] || layout.routes.G1;
}

export function aircraftPosition(layout, assignment, shared, now) {
  const route = routeFor(layout, assignment);
  const taxi = shared.taxi_in_min_by_route[assignment.taxi_route_id];
  const gateIn = assignment.landing_min + taxi;
  if (now < assignment.landing_min) {
    // Illustrative approach, not an observed track or an ATC flight-path contract.
    const inbound = layout.approaches?.[assignment.flight_id] || route.approach;
    const moving = now >= assignment.landing_min - 8;
    return { ...pointOnPath(inbound, (now-(assignment.landing_min-8))/8), phase: moving ? 'On approach' : 'Inbound queue', moving, visible: true };
  }
  if (now < gateIn) return { ...pointOnPath(route.surface, (now-assignment.landing_min)/taxi), phase: 'Taxiing to stand', moving: true, visible: true };
  // No outbound trajectory exists in the API. Retire the track when occupancy
  // ends, rather than leave a completed aircraft blocking a later assignment.
  return { ...pointOnPath(route.surface, 1), phase: now < assignment.gate_out_min ? 'At stand' : 'Turn complete', moving: false, visible: now < assignment.gate_out_min };
}

export function pathString(points, close=false) {
  return points.map((p,i)=>`${i ? 'L' : 'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' ') + (close ? ' Z' : '');
}
