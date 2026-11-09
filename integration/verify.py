"""Verify evidence integrity and replay semantic results with the pinned consumer."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration.run import SOURCE_FILES, SENTINEL_REVISION, digest, load_sentinel, require, run_cases


def verify(folder, sentinel):
    raw = (folder / 'report.json').read_bytes()
    require((folder / 'SHA256SUMS').read_text() == digest(raw) + '  report.json\n', 'report fingerprint mismatch')
    report = json.loads(raw)
    require(report['schema_version'] == 'trace-integration.report.v1', 'unknown report schema')
    require(report['sentinel_revision'] == SENTINEL_REVISION, 'wrong consumer revision')
    require(set(report['source_sha256']) == set(SOURCE_FILES), 'incomplete source inventory')
    require(report['synthetic'] is True and report['semantic_repetitions'] == 10, 'invalid scope metadata')
    for name, expected in report['source_sha256'].items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT) and path.is_file(), 'unsafe source path')
        require(digest(path.read_bytes()) == expected, 'source fingerprint mismatch')
    require(report['sentinel_sha256'] == load_sentinel(sentinel), 'consumer fingerprint mismatch')
    require(report['cases'] == run_cases(), 'semantic replay differs from evidence')
    require(report['passed'] is True and all(row['passed'] is True for row in report['cases']), 'failed contract')
    from tracecheck import inspect_trace
    manifest = json.loads((ROOT / 'manifest.json').read_bytes())
    expected_original = []
    for item in manifest['fixtures']:
        data = (ROOT / item['file']).read_bytes()
        expected_original.append({'id': item['id'], 'passed': digest(data) == item['sha256']
                                  and inspect_trace(data) == item['diagnostics']})
    require(report['original_fixtures'] == expected_original and all(r['passed'] for r in expected_original),
            'fixture evidence mismatch')
    require(report['independent_human_review'] is False and report['business_cost_usd'] is None,
            'unsupported review or cost claim')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--sentinel', required=True, type=Path)
    args = parser.parse_args()
    verify(args.folder.resolve(), args.sentinel.resolve())
    print('PASS: artifact hashes and semantic replay (not independent review)')
