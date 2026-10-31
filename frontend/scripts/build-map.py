"""Prepare cached OSM geometry and an explicitly illustrative presentation route.

Inputs are the downloaded public Overpass JSON and OSM terminal-area XML. This
script does not validate operational taxi routes or alter the backend contract.
"""
import hashlib
import heapq
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = Path(sys.argv[1])
terminal_source = Path(sys.argv[2])
raw = json.loads(source.read_text())


def project(point):
    lon, lat = point
    return [round((lon+97.09)*math.cos(math.radians(32.9))*13400, 3), round((32.926-lat)*13400, 3)]


features = []
for element in raw['elements']:
    tags = element.get('tags', {})
    coordinates = [[p['lon'], p['lat']] for p in element.get('geometry', [])]
    if coordinates:
        features.append(dict(id=f"way/{element['id']}", type=tags['aeroway'], ref=tags.get('ref'),
                             name=tags.get('name'), construction=tags.get('building') == 'construction',
                             coordinates=coordinates))

xml = ET.parse(terminal_source).getroot()
nodes = {n.attrib['id']: [float(n.attrib['lon']), float(n.attrib['lat'])] for n in xml.findall('node')}
ways = {w.attrib['id']: w for w in xml.findall('way')}
known = {f['id'] for f in features}


def tags_of(element):
    return {t.attrib['k']: t.attrib['v'] for t in element.findall('tag')}


def way_points(way):
    return [nodes[n.attrib['ref']] for n in way.findall('nd') if n.attrib['ref'] in nodes]


for way in ways.values():
    tags = tags_of(way)
    oid = f"way/{way.attrib['id']}"
    if oid in known:
        continue
    if tags.get('aeroway') == 'terminal' or tags.get('building') == 'terminal':
        points = way_points(way)
        if len(points) > 2:
            features.append(dict(id=oid, type='terminal', ref=tags.get('ref'), name=tags.get('name'),
                                 coordinates=points, construction=False))
    elif tags.get('highway') and 'International' in tags.get('name', ''):
        features.append(dict(id=oid, type='road', ref=None, name=tags['name'], coordinates=way_points(way)))

for relation in xml.findall('relation'):
    tags = tags_of(relation)
    if tags.get('aeroway') != 'terminal' and tags.get('building') != 'terminal':
        continue
    segments = [way_points(ways[m.attrib['ref']]) for m in relation.findall('member')
                if m.attrib['type'] == 'way' and m.attrib.get('role', '') in ('', 'outer') and m.attrib['ref'] in ways]
    segments = [p for p in segments if p]
    while segments:
        polygon = segments.pop(0)
        while polygon[-1] != polygon[0]:
            for index, segment in enumerate(segments):
                if polygon[-1] == segment[0]:
                    polygon += segment[1:]
                    segments.pop(index)
                    break
                if polygon[-1] == segment[-1]:
                    polygon += list(reversed(segment[:-1]))
                    segments.pop(index)
                    break
            else:
                break
        if len(polygon) > 2:
            features.append(dict(id=f"relation/{relation.attrib['id']}/{len(segments)}", type='terminal',
                                 ref=tags.get('ref'), name=tags.get('name'), coordinates=polygon, construction=False))

# Presentation-only shortest path through the mapped taxiway centerlines.
# It is not clearance-aware and is never used by the coordinator's safety checks.
graph, locations = {}, {}
for feature in features:
    if feature['type'] != 'taxiway':
        continue
    points = feature['coordinates']
    for point in points:
        key = tuple(round(n, 6) for n in point)
        locations[key] = project(point)
        graph.setdefault(key, {})
    for a, b in zip(points, points[1:]):
        a, b = tuple(round(n, 6) for n in a), tuple(round(n, 6) for n in b)
        distance = math.dist(locations[a], locations[b])
        graph[a][b] = distance
        graph[b][a] = distance


def nearest(point):
    p = project(point)
    return min(locations, key=lambda k: math.dist(locations[k], p))


def path(start, end):
    queue, costs, previous = [(0, start)], {start: 0}, {}
    while queue:
        cost, node = heapq.heappop(queue)
        if node == end:
            result = [node]
            while node in previous:
                node = previous[node]
                result.append(node)
            return [locations[p] for p in reversed(result)]
        if cost != costs[node]:
            continue
        for other, length in graph[node].items():
            new = cost + length
            if new < costs.get(other, float('inf')):
                costs[other], previous[other] = new, node
                heapq.heappush(queue, (new, other))
    raise ValueError('Mapped taxiway components do not connect these presentation anchors')


threshold = project([-97.02599, 32.915695])
exit_node = nearest([-97.02612, 32.9049])
stands = {'G1': [-97.0347, 32.8973], 'G2': [-97.0360, 32.9005]}
routes = {}
for gate, anchor in stands.items():
    end = nearest(anchor)
    route = path(exit_node, end)
    routes[gate] = {'surface': [threshold, *route, project(anchor)],
                    'approach': [[threshold[0], 14], threshold]}

result = {
    'metadata': {'airport': 'DFW', 'icao': 'KDFW', 'prepared_date': '2026-10-31',
                 'attribution': '© OpenStreetMap contributors', 'license': 'ODbL-1.0',
                 'license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
                 'source_url': 'https://www.openstreetmap.org/#map=14/32.897/-97.041',
                 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                 'terminal_source_sha256': hashlib.sha256(terminal_source.read_bytes()).hexdigest(),
                 'note': 'Real mapped airport features. Stands G1/G2, flight positions and geographic route mappings are illustrative simulation overlays, not an operational taxi-routing model.'},
    'features': features, 'routes': routes,
    'stands': {k: project(v) for k, v in stands.items()},
    'approaches': {'F1': [[threshold[0], 18], threshold],
                   'F2': [[threshold[0]+110, 30], [threshold[0]+75, 90], threshold],
                   'F3': [[threshold[0]+190, 190], [threshold[0]+145, 90], [threshold[0]+65, 40], threshold]},
    'terminals': [{'name': 'A', 'point': project([-97.0385, 32.9054])},
                  {'name': 'B', 'point': project([-97.0446, 32.9048])},
                  {'name': 'C', 'point': project([-97.0379, 32.8975])},
                  {'name': 'D', 'point': project([-97.0443, 32.8977])},
                  {'name': 'E', 'point': project([-97.0378, 32.8903])}],
}
out = ROOT / 'frontend/public/data/dfw-layout.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
print('Prepared', len(features), 'real map features; runway pairs:', sorted({f['ref'] for f in features if f['type']=='runway'}))
print('Terminals:', [(f.get('name'),f.get('ref')) for f in features if f['type']=='terminal' and f.get('name')])
print('Illustrative route vertices:', {gate: len(r['surface']) for gate, r in routes.items()})
