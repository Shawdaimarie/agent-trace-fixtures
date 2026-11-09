"""Run the pinned synthetic trace-to-Sentinel contract; no network during execution."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration.adapter import adapt
from tracecheck import inspect_trace

SENTINEL_REVISION = '3b2e7cf0716e3940ef5f8af7beb0177408afe333'
SENTINEL_FILES = ('Sentinel/src/sentinel/__init__.py', 'Sentinel/src/sentinel/evaluation.py',
                  'Sentinel/src/sentinel/trace_import.py')
SOURCE_FILES = ('tracecheck.py', 'manifest.json', 'integration/adapter.py',
                'integration/run.py', 'integration/cases.json', 'integration/requirements.lock',
                'integration/build_cases.py', 'integration/verify.py')
MARKERS = ('SYNTHETIC_TOKEN_DO_NOT_USE', 'fixture-user@example.invalid')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_sentinel(path):
    """Check the files we execute against their pinned Git objects before importing."""
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path).decode().strip()
            == SENTINEL_REVISION, 'Sentinel revision differs from pin')
    for line in (ROOT / 'integration/requirements.lock').read_text().splitlines():
        name, version = line.split('==')
        require(importlib.metadata.version(name) == version, f'dependency differs from lock: {name}')
    hashes = {}
    for name in SENTINEL_FILES:
        raw = (path / name).read_bytes()
        expected = subprocess.check_output(['git', 'show', f'{SENTINEL_REVISION}:{name}'], cwd=path)
        require(raw == expected, f'Sentinel source modified: {name}')
        hashes[name] = digest(raw)
    sys.path.insert(0, str(path / 'Sentinel/src'))
    return hashes


def run_cases():
    from sentinel.evaluation import EvalCase, evaluate_suite
    corpus = json.loads((ROOT / 'integration/cases.json').read_bytes())
    require(corpus['schema_version'] == 'trace-integration.cases.v1', 'unknown corpus version')
    require(len(corpus['cases']) == 10, 'incomplete integration corpus')
    require(len({c['id'] for c in corpus['cases']}) == 10, 'duplicate case identity')
    rows = []
    for case in corpus['cases']:
        raw = case['input_utf8'].encode()
        require(digest(raw) == case['sha256'], 'case fingerprint mismatch')
        diagnostics, imported = adapt(raw, case['id'])
        checks = {'diagnostics_match': diagnostics == case['diagnostics'],
                  'import_disposition': (imported is not None) == (case['evaluation_gate'] is not None)}
        row = {'id': case['id'], 'input_sha256': digest(raw), 'diagnostics': diagnostics,
               'checks': checks, 'normalized': None, 'evaluation': None}
        if imported is not None:
            normalized = imported.model_dump(mode='json')
            # Preserve exact timestamps for JSON consumers with IEEE-754 numbers.
            for trace in normalized['manifest']['traces']:
                for action in trace['actions']:
                    if action['start_ns'] is not None:
                        action['start_ns'] = str(action['start_ns'])
            text = json.dumps(normalized, sort_keys=True)
            checks['markers_removed'] = not any(marker in text for marker in MARKERS)
            traces = imported.manifest.traces
            actions = [a for t in traces for a in t.actions]
            checks['useful_content'] = (len(imported.runs) > 0 and len(actions) == case['action_count']
                                        and any(r.output == 'synthetic completed' for r in imported.runs))
            checks['partial_count'] = imported.manifest.partial_runs == case['partial_runs']
            checks['source_identity'] = imported.manifest.source_sha256 == digest(raw)
            if case['id'] == 'sensitive':
                checks['redaction_count'] = imported.manifest.redacted_attribute_count >= 2
            if case['id'] == 'retry-preserved':
                checks['retry_identity'] = (len({a.span_id for a in actions}) == 2
                                           and {a.status for a in actions} == {'failed', 'executed'})
            if case['id'] == 'uint64-boundary':
                checks['timestamp_exact'] = actions[0].start_ns == 2**64 - 2
            suite = evaluate_suite([EvalCase(id=case['id'], task='Synthetic trace contract',
                                            expected_output_contains=['synthetic completed'],
                                            required_actions=['lookup'])], imported.runs)
            evaluation = suite.model_dump(mode='json')
            evaluation.pop('generated_at')  # Wall time is not a semantic result.
            # Sentinel defaults absent cost to zero. Explicitly mark it unmeasured here.
            checks['evaluation_gate'] = suite.gate_passed == case['evaluation_gate']
            row.update(normalized=normalized, evaluation=evaluation)
        row['passed'] = all(checks.values())
        rows.append(row)
    return rows


def execute(sentinel, output):
    require(not output.exists(), 'refusing to overwrite evidence directory')
    sentinel_hashes = load_sentinel(sentinel)
    rows = run_cases()
    # Semantic stability, not independent examples or an independent reviewer.
    for _ in range(9):
        require(run_cases() == rows, 'semantic results changed across repeated runs')
    manifest = json.loads((ROOT / 'manifest.json').read_bytes())
    original = []
    for item in manifest['fixtures']:
        raw = (ROOT / item['file']).read_bytes()
        original.append({'id': item['id'], 'passed': digest(raw) == item['sha256']
                         and inspect_trace(raw) == item['diagnostics']})
    report = dict(schema_version='trace-integration.report.v1', synthetic=True,
                  source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                  source_worktree_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
                  source_sha256={p: digest((ROOT / p).read_bytes()) for p in SOURCE_FILES},
                  sentinel_revision=SENTINEL_REVISION, sentinel_sha256=sentinel_hashes,
                  environment={'python': platform.python_version(), 'system': platform.system(),
                               'machine': platform.machine(), 'packages': {
                                   name: importlib.metadata.version(name) for name in
                                   ('pydantic', 'pydantic-core', 'annotated-types', 'typing-extensions', 'typing-inspection')}},
                  semantic_repetitions=10, original_fixtures=original, cases=rows,
                  business_cost_usd=None, independent_human_review=False,
                  passed=all(r['passed'] for r in rows + original))
    output.mkdir(parents=True, exist_ok=False)
    raw = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode()
    (output / 'report.json').write_bytes(raw)
    (output / 'SHA256SUMS').write_text(digest(raw) + '  report.json\n')
    return report['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sentinel', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        passed = execute(args.sentinel.resolve(), args.output.resolve())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(2)
    print('PASS: trace-to-evaluation contract' if passed else 'FAIL: contract mismatch')
    raise SystemExit(0 if passed else 1)
