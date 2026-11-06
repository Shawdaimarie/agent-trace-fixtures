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
        if not (hashlib.sha256((here / relative).read_bytes()).hexdigest() == criteria['sha256'][relative]):
            raise ValueError('Evidence check failed at original source line 14')
    listed = set()
    for line in (folder / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if not (Path(name).name == name and name not in listed):
            raise ValueError('Evidence check failed at original source line 18')
        listed.add(name)
        if not (hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected):
            raise ValueError(name)
    if not ({'summary.json', 'case-results.jsonl', 'timings.jsonl'} <= listed):
        raise ValueError('Evidence check failed at original source line 21')
    summary = json.loads((folder / 'summary.json').read_text())
    rows = [json.loads(line) for line in (folder / 'case-results.jsonl').read_text().splitlines()]
    timings = [json.loads(line) for line in (folder / 'timings.jsonl').read_text().splitlines()]
    if not (len(cases) == 20 and len(rows) == 40 and len(timings) == 200):
        raise ValueError('Evidence check failed at original source line 25')
    if not (summary['baseline_commit'] == criteria['baseline_commit']):
        raise ValueError('Evidence check failed at original source line 26')
    if not (summary['repetitions_per_implementation'] == criteria['repeats'] == 100):
        raise ValueError('Evidence check failed at original source line 27')
    labels = {c['id']: c for c in cases}
    if not (len({(r['implementation'], r['id']) for r in rows}) == 40):
        raise ValueError('Evidence check failed at original source line 29')
    for row in rows:
        case = labels[row['id']]
        if not (row['cohort'] == case['cohort'] and row['expected'] == case['expected_diagnostics']):
            raise ValueError('Evidence check failed at original source line 32')
        if not (row['match'] == (row['actual'] == row['expected'])):
            raise ValueError('Evidence check failed at original source line 33')
        if not (row['input_sha256'] == hashlib.sha256(case['input_utf8'].encode()).hexdigest()):
            raise ValueError('Evidence check failed at original source line 34')
    for name, expected_matches, false_accepts in [('baseline', 12, 8), ('candidate', 20, 0)]:
        subset = [r for r in rows if r['implementation'] == name]
        samples = [t for t in timings if t['implementation'] == name]
        if not (len(subset) == 20 and len(samples) == 100):
            raise ValueError('Evidence check failed at original source line 38')
        if not ({t['repetition'] for t in samples} == set(range(100))):
            raise ValueError('Evidence check failed at original source line 39')
        if not (all(t['stable'] is True and type(t['batch_nanoseconds']) is int
                   and t['batch_nanoseconds'] >= 0 for t in samples)):
            raise ValueError('Evidence check failed at original source line 40')
        ns = sorted(t['batch_nanoseconds'] for t in samples)
        observed = dict(exact_matches=sum(r['match'] for r in subset), cases=20,
                        false_accepts_malformed_siblings=sum(not r['actual'] for r in subset
                                                            if r['cohort'] == 'malformed-sibling'),
                        valid_control_false_alarms=sum(bool(r['actual']) for r in subset if not r['expected']),
                        median_batch_ms=statistics.median(ns)/1_000_000, p95_batch_ms=ns[94]/1_000_000)
        if not (summary['implementations'][name] == observed):
            raise ValueError('Evidence check failed at original source line 48')
        if not (observed['exact_matches'] == expected_matches):
            raise ValueError('Evidence check failed at original source line 49')
        if not (observed['false_accepts_malformed_siblings'] == false_accepts):
            raise ValueError('Evidence check failed at original source line 50')
        if not (observed['valid_control_false_alarms'] == 0):
            raise ValueError('Evidence check failed at original source line 51')
    if not (summary['observed'] == criteria['acceptance']):
        raise ValueError('Evidence check failed at original source line 52')
    if not (all(v is True for v in summary['checks'].values()) and summary['status'] == 'PASS'):
        raise ValueError('Evidence check failed at original source line 53')
    if not (all(v is None for v in summary['business_outcomes'].values())):
        raise ValueError('Evidence check failed at original source line 54')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    verify(args.folder)
    print('PASS: hashes, labels, counts, diagnostics, timing arithmetic and unmeasured business outcomes')
