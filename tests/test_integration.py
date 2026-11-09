"""Exercise real consumer calls and hostile evidence changes, never model APIs."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = os.environ.get('SENTINEL_CHECKOUT')


@unittest.skipUnless(SENTINEL, 'set SENTINEL_CHECKOUT for pinned consumer integration')
class IntegrationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name) / 'evidence'
        result = subprocess.run([sys.executable, 'integration/run.py', '--sentinel', SENTINEL,
                                 '--output', str(cls.folder)], cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def verify(self, folder, optimized=False):
        return subprocess.run([sys.executable, *(['-O'] if optimized else []),
                               'integration/verify.py', str(folder), '--sentinel', SENTINEL],
                              cwd=ROOT, capture_output=True)

    def test_semantic_replay_in_both_modes(self):
        for optimized in (False, True):
            self.assertEqual(self.verify(self.folder, optimized).returncode, 0)

    def test_corruption_then_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'copy'
            shutil.copytree(self.folder, folder)
            report = folder / 'report.json'
            original = report.read_bytes()
            report.write_bytes(original + b' ')
            for optimized in (False, True):
                self.assertNotEqual(self.verify(folder, optimized).returncode, 0)
            report.write_bytes(original)
            self.assertEqual(self.verify(folder).returncode, 0)

    def test_rehashed_false_pass_and_missing_case_rejected(self):
        for mutation in ('gate', 'missing-case', 'empty-normalized'):
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / 'copy'
                shutil.copytree(self.folder, folder)
                report = json.loads((folder / 'report.json').read_bytes())
                if mutation == 'gate':
                    report['cases'][2]['evaluation']['gate_passed'] = True
                elif mutation == 'missing-case':
                    report['cases'].pop()
                else:
                    report['cases'][1]['normalized'] = {}
                raw = json.dumps(report).encode()
                (folder / 'report.json').write_bytes(raw)
                (folder / 'SHA256SUMS').write_text(hashlib.sha256(raw).hexdigest() + '  report.json\n')
                for optimized in (False, True):
                    self.assertNotEqual(self.verify(folder, optimized).returncode, 0)

    def test_refuse_overwrite(self):
        before = (self.folder / 'report.json').read_bytes()
        result = subprocess.run([sys.executable, 'integration/run.py', '--sentinel', SENTINEL,
                                 '--output', str(self.folder)], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.folder / 'report.json').read_bytes(), before)

    def test_reject_modified_consumer_before_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / 'sentinel'
            subprocess.run(['git', 'clone', '--quiet', '--shared', SENTINEL, str(clone)], check=True)
            module = clone / 'Sentinel/src/sentinel/trace_import.py'
            module.write_bytes(module.read_bytes() + b'\n# altered\n')
            result = subprocess.run([sys.executable, 'integration/run.py', '--sentinel', str(clone),
                                     '--output', str(Path(tmp) / 'results')], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(tmp) / 'results').exists())


class IntegrationCorpus(unittest.TestCase):
    def test_generation_matches_committed_cases(self):
        from integration.build_cases import generate
        self.assertEqual(generate(), json.loads((ROOT / 'integration/cases.json').read_bytes()))

    def test_resource_limit_prevents_consumer_import(self):
        from integration.adapter import adapt
        from tracecheck import MAX_BYTES
        self.assertEqual(adapt(b' ' * (MAX_BYTES + 1), 'oversized'), (['input_too_large'], None))
