"""Reconcile archived evidence; this is integrity checking, not independent replay."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path


def verify(folder: Path) -> None:
    here = Path(__file__).resolve().parent
    criteria = json.loads((here / 'criteria.json').read_text())
    cases = [json.loads(line) for line in (here / 'cases.jsonl').read_text().splitlines()]
    for relative in ('cases.jsonl', 'baseline_tracecheck.py'):
        assert hashlib.sha256((here / relative).read_bytes()).hexdigest() == criteria['sha256'][relative]
    listed = set()
    for line in (folder / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert Path(name).name == name and name not in listed
        listed.add(name)
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected, name
    assert {'summary.json', 'case-results.jsonl', 'timings.jsonl'} <= listed
    summary = json.loads((folder / 'summary.json').read_text())
    rows = [json.loads(line) for line in (folder / 'case-results.jsonl').read_text().splitlines()]
    timings = [json.loads(line) for line in (folder / 'timings.jsonl').read_text().splitlines()]
    assert len(cases) == 20 and len(rows) == 40 and len(timings) == 200
    assert summary['baseline_commit'] == criteria['baseline_commit']
    assert summary['repetitions_per_implementation'] == criteria['repeats'] == 100
    labels = {c['id']: c for c in cases}
    assert len({(r['implementation'], r['id']) for r in rows}) == 40
    for row in rows:
        case = labels[row['id']]
        assert row['cohort'] == case['cohort'] and row['expected'] == case['expected_diagnostics']
        assert row['match'] == (row['actual'] == row['expected'])
        assert row['input_sha256'] == hashlib.sha256(case['input_utf8'].encode()).hexdigest()
    for name, expected_matches, false_accepts in [('baseline', 12, 8), ('candidate', 20, 0)]:
        subset = [r for r in rows if r['implementation'] == name]
        samples = [t for t in timings if t['implementation'] == name]
        assert len(subset) == 20 and len(samples) == 100
        assert {t['repetition'] for t in samples} == set(range(100))
        assert all(t['stable'] is True and type(t['batch_nanoseconds']) is int
                   and t['batch_nanoseconds'] >= 0 for t in samples)
        ns = sorted(t['batch_nanoseconds'] for t in samples)
        observed = dict(exact_matches=sum(r['match'] for r in subset), cases=20,
                        false_accepts_malformed_siblings=sum(not r['actual'] for r in subset
                                                            if r['cohort'] == 'malformed-sibling'),
                        valid_control_false_alarms=sum(bool(r['actual']) for r in subset if not r['expected']),
                        median_batch_ms=statistics.median(ns)/1_000_000, p95_batch_ms=ns[94]/1_000_000)
        assert summary['implementations'][name] == observed
        assert observed['exact_matches'] == expected_matches
        assert observed['false_accepts_malformed_siblings'] == false_accepts
        assert observed['valid_control_false_alarms'] == 0
    assert summary['observed'] == criteria['acceptance']
    assert all(v is True for v in summary['checks'].values()) and summary['status'] == 'PASS'
    assert all(v is None for v in summary['business_outcomes'].values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    verify(args.folder)
    print('PASS: hashes, labels, counts, diagnostics, timing arithmetic and unmeasured business outcomes')
