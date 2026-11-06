"""Evidence validation must not disappear under optimized Python execution."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / 'pilots/trace-container-v1'
ARCHIVE = PILOT / 'results/2026-10-23'


class EvidenceVerifier(unittest.TestCase):
    def run_verifier(self, folder, optimized):
        command = [sys.executable]
        if optimized:
            command.append('-O')
        return subprocess.run(command + [str(PILOT / 'verify_results.py'), str(folder)],
                              capture_output=True, text=True, timeout=10)

    def test_original_archive_passes_both_execution_modes(self):
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                result = self.run_verifier(ARCHIVE, optimized)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_hash_mismatch_is_rejected_in_both_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'archive'
            shutil.copytree(ARCHIVE, folder)
            with (folder / 'summary.json').open('a') as output:
                output.write(' ')
            for optimized in (False, True):
                with self.subTest(optimized=optimized):
                    result = self.run_verifier(folder, optimized)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn('PASS:', result.stdout)

    def test_rehashed_failed_summary_is_rejected_in_both_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'archive'
            shutil.copytree(ARCHIVE, folder)
            summary_path = folder / 'summary.json'
            summary = json.loads(summary_path.read_text())
            summary['status'] = 'FAIL'
            summary_path.write_text(json.dumps(summary))
            manifest = folder / 'SHA256SUMS'
            names = [line.split('  ', 1)[1] for line in manifest.read_text().splitlines()]
            manifest.write_text(''.join(
                hashlib.sha256((folder / name).read_bytes()).hexdigest() + '  ' + name + '\n'
                for name in names))
            for optimized in (False, True):
                with self.subTest(optimized=optimized):
                    result = self.run_verifier(folder, optimized)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn('PASS:', result.stdout)


if __name__ == '__main__':
    unittest.main()
