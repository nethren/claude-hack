#!/usr/bin/env python3
"""Check documentary/source alignment; does not test an unbuilt application."""
import ast
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
errors = []
manifest = json.loads((ROOT / 'references/source-manifest.json').read_text(encoding='utf-8'))
profile = json.loads((ROOT / 'references/dataset-profile.json').read_text(encoding='utf-8'))
required = [
    'AGENTS.md', 'CLAUDE.md', 'README.md', 'docs/challenge-2-requirements.md',
    'docs/judging-rubric.md', 'docs/datasets.md',
    'docs/multi-agent-design-constraints.md', 'docs/alignment-checklist.md',
    'docs/decision-log.md', 'docs/airbus-track-brief.md', 'docs/source-register.md',
    'docs/data/airlines.md', 'docs/data/airports.md', 'docs/data/flight-scenarios.md',
    'docs/ai-orchestration-architecture.md', 'docs/examples/coordination-scenario-v1.json',
]
for rel in required:
    if not (ROOT / rel).is_file():
        errors.append(f'Missing document: {rel}')

lookups = {}
for entry in manifest['sources']:
    path = ROOT / entry['path']
    if not path.is_file():
        errors.append(f'Missing source: {entry["path"]}')
        continue
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != entry['sha256'] or path.stat().st_size != entry['bytes']:
        errors.append(f'Source changed; refresh docs/profile/manifest: {entry["path"]}')
    if entry['id'] in {'airlines.csv', 'airports.csv'}:
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            if reader.fieldnames != entry['columns'] or len(rows) != entry['rows']:
                errors.append(f'Lookup schema/count mismatch: {entry["id"]}')
        lookups[entry['id']] = {r['IATA_CODE'] for r in rows}
        if len(rows) != len(lookups[entry['id']]):
            errors.append(f'Duplicate lookup keys: {entry["id"]}')
        md = (ROOT / f'docs/data/{path.stem}.md').read_text(encoding='utf-8')
        markdown_rows = [line for line in md.splitlines() if line.startswith('| ')][2:]
        def cell(value):
            return str(value).replace('\\', '\\\\').replace('|', '\\|').replace('\r', '').replace('\n', '<br>')
        expected_rows = ['| ' + ' | '.join(cell(r[c]) for c in entry['columns']) + ' |' for r in rows]
        if markdown_rows != expected_rows:
            errors.append(f'Markdown lookup differs from complete CSV: {entry["id"]}')

f_entry = next(e for e in manifest['sources'] if e['id'] == 'flights.csv')
counts = Counter()
months = Counter()
missing = Counter()
selected_rows = {}
scenario_md = (ROOT / 'docs/data/flight-scenarios.md').read_text(encoding='utf-8')
example_ids = {int(n) for n in re.findall(r'### [^\n]+: CSV row (\d+)', scenario_md)}
architecture_fixture = json.loads((ROOT / 'docs/examples/coordination-scenario-v1.json').read_text(encoding='utf-8'))
architecture_sources = architecture_fixture['shared']['source_rows']
architecture_row_ids = {row['csv_row_number'] for row in architecture_sources}
with (ROOT / f_entry['path']).open(encoding='utf-8-sig', newline='') as stream:
    reader = csv.DictReader(stream)
    if reader.fieldnames != f_entry['columns']:
        errors.append('Flights schema differs from manifest')
    for row_number, row in enumerate(reader, 2):
        counts['rows'] += 1
        months[row['MONTH']] += 1
        missing.update(c for c in reader.fieldnames if not (row.get(c) or '').strip())
        w, l = float(row['WEATHER_DELAY']), float(row['LATE_AIRCRAFT_DELAY'])
        counts['weather_gt_15'] += w > 15
        counts['late_gt_20'] += l > 20
        counts['qualifying_either'] += w > 15 or l > 20
        counts['qualifying_both'] += w > 15 and l > 20
        counts['cancelled'] += row['CANCELLED'] == '1'
        counts['diverted'] += row['DIVERTED'] == '1'
        if row['AIRLINE'] not in lookups.get('airlines.csv', set()):
            counts['unknown_airlines'] += 1
        if row['ORIGIN_AIRPORT'] not in lookups.get('airports.csv', set()):
            counts['unknown_origins'] += 1
        if row['DESTINATION_AIRPORT'] not in lookups.get('airports.csv', set()):
            counts['unknown_destinations'] += 1
        if row_number in example_ids | architecture_row_ids:
            selected_rows[row_number] = row

for key in ['weather_gt_15','late_gt_20','qualifying_either','qualifying_both','cancelled','diverted']:
    if counts[key] != profile['flights.csv']['counts'][key]:
        errors.append(f'Flight profile count mismatch: {key}')
if counts['rows'] != f_entry['rows'] or dict(months) != profile['flights.csv']['months']:
    errors.append('Flight row count/month coverage mismatch')
if {c: missing[c] for c in f_entry['columns']} != profile['flights.csv']['missing']:
    errors.append('Flight missing-cell profile mismatch')
for key in ['unknown_airlines','unknown_origins','unknown_destinations']:
    if counts[key]:
        errors.append(f'Flight lookup join failed: {key}={counts[key]}')
for row_number in example_ids:
    if row_number not in selected_rows:
        errors.append(f'Example source row missing: {row_number}')
    else:
        row = selected_rows[row_number]
        for c in f_entry['columns']:
            expected = f'| {c} | {row[c]} |'
            section = scenario_md.split(f': CSV row {row_number}\n',1)[1].split('\n### ',1)[0]
            if expected not in section:
                errors.append(f'Example row {row_number} field mismatch: {c}')

for row in architecture_sources:
    if row['dataset_sha256'] != f_entry['sha256'] or selected_rows.get(row['csv_row_number']) != row['raw']:
        errors.append(f'Architecture fixture source differs from real CSV row {row["csv_row_number"]}')
architecture = (ROOT / 'docs/ai-orchestration-architecture.md').read_text(encoding='utf-8')
for block in re.findall(r'```python\n(.*?)\n```', architecture, re.S):
    try:
        ast.parse(block)
    except SyntaxError as error:
        errors.append(f'Architecture Python contract syntax: {error}')

# Check relative file links without following network URLs or interpreting source prose.
md_files = sorted(ROOT.rglob('*.md'))
for path in md_files:
    body = path.read_text(encoding='utf-8')
    if body.count('```') % 2:
        errors.append(f'Unclosed code fence: {path.relative_to(ROOT)}')
    for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', body):
        target = target.strip().strip('<>')
        if not target or target.startswith(('#','https://','http://','mailto:')):
            continue
        local = unquote(target.split('#', 1)[0])
        if local and not (path.parent / local).resolve().is_file():
            errors.append(f'Broken local link in {path.relative_to(ROOT)}: {target}')

requirements = (ROOT / 'docs/challenge-2-requirements.md').read_text(encoding='utf-8')
matrix = (ROOT / 'docs/alignment-checklist.md').read_text(encoding='utf-8')
defined = set(re.findall(r'^\| (C2-\d{2}) \|', requirements, flags=re.M))
expected = {f'C2-{i:02d}' for i in range(1,27)}
if defined != expected:
    errors.append('Challenge requirement IDs missing or unexpected')
for rid in expected:
    if rid not in matrix:
        errors.append(f'Requirement absent from alignment matrix: {rid}')
rubric = (ROOT / 'docs/judging-rubric.md').read_text(encoding='utf-8')
weights = [int(x) for x in re.findall(r'^\| JR-\d{2} \| [^|]+ \| (\d+)%',rubric,flags=re.M)]
if weights != [20,25,20,20,10,5] or sum(weights) != 100:
    errors.append('Official rubric weights differ from source transcription')
for i in range(1,7):
    if f'JR-{i:02d}' not in matrix:
        errors.append(f'Rubric criterion absent from matrix: JR-{i:02d}')

secret = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{25,}|sk-[A-Za-z0-9]{25,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
for path in md_files:
    if secret.search(path.read_text(encoding='utf-8')):
        errors.append(f'Potential credential in {path.relative_to(ROOT)}')
for nested in ROOT.rglob('.git'):
    if nested != ROOT / '.git':
        errors.append(f'Nested Git directory: {nested}')

if errors:
    for error in errors:
        print('FAIL:', error)
    sys.exit(1)
print(f'PASS: {len(md_files)} Markdown documents; 5 source hashes; all CSV schemas/counts;')
print(f'{counts["rows"]:,} qualifying flight rows; lookup joins; complete lookup tables; source-row examples;')
print('26 requirement IDs; 6 rubric weights totaling 100%; relative links and file hygiene.')
print('Architecture Python syntax and integration-fixture source provenance checked.')
print('Application status remains not implemented / not tested.')
