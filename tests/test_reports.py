import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReportChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / 'corpus'
        self.root.mkdir()
        shutil.copy(ROOT / 'manifest.json', self.root / 'manifest.json')
        shutil.copytree(ROOT / 'fixtures', self.root / 'fixtures')
        self.output = Path(self.directory.name) / 'reports/results.json'

    def run_checker(self, output=None):
        return subprocess.run([
            sys.executable, str(ROOT / 'tracecheck.py'), '--root', str(self.root),
            '--json-out', str(output or self.output),
        ], capture_output=True, text=True, timeout=5)

    def test_report_preserves_negative_expectations_without_payload(self):
        self.assertEqual(self.run_checker().returncode, 0)
        raw = self.output.read_text()
        report = json.loads(raw)
        self.assertEqual(report['fixture_count'], 9)
        self.assertEqual(report['failure_count'], 0)
        self.assertTrue(report['passed'])
        negative = next(item for item in report['results'] if item['id'] == 'parent-cycle')
        self.assertTrue(negative['passed'])
        self.assertEqual(negative['actual_diagnostics'], ['parent_cycle'])
        self.assertNotIn('SYNTHETIC_TOKEN_DO_NOT_USE', raw)
        self.assertNotIn('resourceSpans', raw)
        self.assertEqual(self.run_checker().returncode, 0)
        self.assertEqual(self.output.read_text(), raw)

    def test_byte_change_fails_even_when_structure_is_valid(self):
        source = self.root / 'fixtures/parent-child.json'
        source.write_bytes(source.read_bytes() + b' ')
        self.assertEqual(self.run_checker().returncode, 1)
        report = json.loads(self.output.read_text())
        changed = report['results'][0]
        self.assertTrue(changed['diagnostics_match'])
        self.assertFalse(changed['fingerprint_matches'])
        self.assertEqual(report['failure_count'], 1)

    def test_output_cannot_overwrite_inputs(self):
        for source in [self.root / 'manifest.json', self.root / 'fixtures/parent-child.json']:
            before = source.read_bytes()
            self.assertEqual(self.run_checker(source).returncode, 2)
            self.assertEqual(source.read_bytes(), before)

    def test_empty_corpus_does_not_pass(self):
        (self.root / 'manifest.json').write_text('{"fixtures": []}')
        self.assertEqual(self.run_checker().returncode, 2)
        self.assertFalse(self.output.exists())

    def test_oversize_input_has_no_misleading_full_file_digest(self):
        source = self.root / 'fixtures/parent-child.json'
        source.write_bytes(b' ' * (1024 * 1024 + 100))
        self.assertEqual(self.run_checker().returncode, 1)
        changed = json.loads(self.output.read_text())['results'][0]
        self.assertIsNone(changed['actual_sha256'])
        self.assertEqual(changed['actual_diagnostics'], ['input_too_large'])
