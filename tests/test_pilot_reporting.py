"""Protect the pilot's release decision from misleading summary totals."""
import importlib.util
import json
import unittest
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / 'pilots/trace-container-v1'
spec = importlib.util.spec_from_file_location('pilot', PILOT / 'run.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class PilotReporting(unittest.TestCase):
    def setUp(self):
        self.criteria = json.loads((PILOT / 'criteria.json').read_text())
        self.cases = [json.loads(line) for line in (PILOT / 'cases.jsonl').read_text().splitlines()]
        # One batch is enough for decision tests; published measurement uses frozen 100.
        self.criteria['repeats'] = 1
        self.rows, self.timings = pilot.replay(self.criteria, self.cases)

    def test_a_false_accept_fails_the_decision(self):
        row = next(r for r in self.rows if r['implementation'] == 'candidate'
                   and r['cohort'] == 'malformed-sibling')
        row['actual'], row['match'] = [], False
        result = pilot.summarize(self.criteria, self.rows, self.timings)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['implementations']['candidate']['false_accepts_malformed_siblings'], 1)

    def test_an_unstable_repeat_fails_the_decision(self):
        self.timings[0]['stable'] = False
        self.assertEqual(pilot.summarize(self.criteria, self.rows, self.timings)['status'], 'FAIL')

    def test_technical_pass_does_not_populate_business_outcomes(self):
        result = pilot.summarize(self.criteria, self.rows, self.timings)
        self.assertEqual(result['status'], 'PASS')
        self.assertTrue(all(value is None for value in result['business_outcomes'].values()))


if __name__ == '__main__':
    unittest.main()
