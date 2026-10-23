import copy
import json
import unittest
from pathlib import Path

from tracecheck import MAX_BYTES, inspect_trace

ROOT = Path(__file__).resolve().parents[1]


class TraceChecks(unittest.TestCase):
    def test_corpus_expected_diagnostics_and_hashes(self):
        import hashlib
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        for fixture in manifest['fixtures']:
            with self.subTest(fixture=fixture['id']):
                raw = (ROOT / fixture['file']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), fixture['sha256'])
                self.assertEqual(inspect_trace(raw), fixture['diagnostics'])

    def test_invalid_encoding_and_depth(self):
        for raw in [b'\xff', b'[' * 10000 + b']' * 10000]:
            self.assertEqual(inspect_trace(raw), ['invalid_json'])

    def test_input_limit(self):
        self.assertEqual(inspect_trace(b' ' * (MAX_BYTES + 1)), ['input_too_large'])

    def test_case_insensitive_identifiers(self):
        doc = json.loads((ROOT / 'fixtures/parent-child.json').read_text())
        spans = doc['resourceSpans'][0]['scopeSpans'][0]['spans']
        for span in spans:
            span['traceId'] = span['traceId'].upper()
            span['spanId'] = span['spanId'].upper()
        self.assertEqual(inspect_trace(json.dumps(doc).encode()), [])

    def test_cross_trace_parent_does_not_resolve(self):
        doc = json.loads((ROOT / 'fixtures/parent-child.json').read_text())
        other = copy.deepcopy(doc['resourceSpans'][0]['scopeSpans'][0]['spans'][1])
        other['traceId'] = 'c' * 32
        doc['resourceSpans'][0]['scopeSpans'][0]['spans'].append(other)
        self.assertEqual(inspect_trace(json.dumps(doc).encode()), ['missing_parent'])

    def test_empty_and_bad_shapes(self):
        for raw in [b'null', b'[]', b'{}', b'{"resourceSpans":null}']:
            self.assertEqual(inspect_trace(raw), ['invalid_shape'])

    def test_malformed_containers_are_not_silently_skipped(self):
        for value in [{}, '', None, 0, False]:
            cases = [
                {'resourceSpans': value},
                {'resourceSpans': [{'scopeSpans': value}]},
                {'resourceSpans': [{'scopeSpans': [{'spans': value}]}]},
            ]
            for level, doc in zip(['resourceSpans', 'scopeSpans', 'spans'], cases):
                with self.subTest(level=level, value=value):
                    self.assertEqual(inspect_trace(json.dumps(doc).encode()), ['invalid_shape'])

    def test_valid_spans_do_not_hide_malformed_siblings(self):
        original = json.loads((ROOT / 'fixtures/parent-child.json').read_text())
        for value in [{}, '']:
            for level in ['scopeSpans', 'spans']:
                with self.subTest(level=level, value=value):
                    doc = copy.deepcopy(original)
                    if level == 'scopeSpans':
                        doc['resourceSpans'].append({'scopeSpans': value})
                    else:
                        doc['resourceSpans'][0]['scopeSpans'].append({'spans': value})
                    self.assertEqual(inspect_trace(json.dumps(doc).encode()), ['invalid_shape'])

    def test_empty_arrays_remain_well_shaped(self):
        for doc in [
            {'resourceSpans': []},
            {'resourceSpans': [{'scopeSpans': []}]},
            {'resourceSpans': [{'scopeSpans': [{'spans': []}]}]},
        ]:
            with self.subTest(doc=doc):
                self.assertEqual(inspect_trace(json.dumps(doc).encode()), ['empty_spans'])
        doc = json.loads((ROOT / 'fixtures/parent-child.json').read_text())
        doc['resourceSpans'].append({'scopeSpans': []})
        doc['resourceSpans'][0]['scopeSpans'].append({'spans': []})
        self.assertEqual(inspect_trace(json.dumps(doc).encode()), [])

    def test_container_entries_must_be_objects_with_required_arrays(self):
        for value in [None, False, 0, '', [], {}]:
            for doc in [
                {'resourceSpans': [value]},
                {'resourceSpans': [{'scopeSpans': [value]}]},
            ]:
                with self.subTest(doc=doc):
                    self.assertEqual(inspect_trace(json.dumps(doc).encode()), ['invalid_shape'])

    def test_span_limit_across_scopes(self):
        doc = json.loads((ROOT / 'fixtures/parent-child.json').read_text())
        spans = doc['resourceSpans'][0]['scopeSpans'][0]['spans']
        doc['resourceSpans'][0]['scopeSpans'] = [{'spans': spans * 250}, {'spans': spans * 250}]
        self.assertEqual(inspect_trace(json.dumps(doc).encode()), ['duplicate_span'])
        doc['resourceSpans'][0]['scopeSpans'].append({'spans': [spans[0]]})
        self.assertEqual(inspect_trace(json.dumps(doc).encode()), ['too_many_spans'])


if __name__ == '__main__':
    unittest.main()
