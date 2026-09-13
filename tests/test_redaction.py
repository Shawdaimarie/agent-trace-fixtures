import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RedactionChecks(unittest.TestCase):
    def test_marker_is_detected_without_echoing_it(self):
        result = subprocess.run([sys.executable, str(ROOT / 'check_redaction.py'),
                                 str(ROOT / 'fixtures/sensitive-attributes.json')],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn('2 exact synthetic markers remain', result.stdout)
        self.assertNotIn('SYNTHETIC_TOKEN_DO_NOT_USE', result.stdout + result.stderr)

    def test_clean_and_invalid_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output.json'
            for data, expected in [(b'{"redacted": true}', 0), (b'\xff', 2)]:
                output.write_bytes(data)
                result = subprocess.run([sys.executable, str(ROOT / 'check_redaction.py'), str(output)],
                                        capture_output=True, timeout=5)
                self.assertEqual(result.returncode, expected)
