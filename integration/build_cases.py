"""Generate a separate synthetic integration corpus; leave the frozen pilot untouched."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent


def generate():
    base = json.loads((ROOT / 'fixtures/parent-child.json').read_bytes())
    spans = base['resourceSpans'][0]['scopeSpans'][0]['spans']
    spans[0]['attributes'] = [{'key': 'output.value', 'value': {'stringValue': 'synthetic completed'}}]
    cases = []

    def add(name, doc, diagnostics, gate=None, partial=0, actions=1):
        raw = json.dumps(doc, sort_keys=True, separators=(',', ':')) + '\n'
        cases.append(dict(id=name, input_utf8=raw, sha256=hashlib.sha256(raw.encode()).hexdigest(),
                          diagnostics=diagnostics, evaluation_gate=gate, partial_runs=partial,
                          action_count=actions))

    add('complete', base, [], True)
    sensitive = copy.deepcopy(base)
    sensitive['resourceSpans'][0]['scopeSpans'][0]['spans'][0]['attributes'] += [
        {'key': 'user.email', 'value': {'stringValue': 'fixture-user@example.invalid'}},
        {'key': 'http.request.header.authorization', 'value': {'stringValue': 'Bearer SYNTHETIC_TOKEN_DO_NOT_USE'}}]
    add('sensitive', sensitive, [], True)
    missing = copy.deepcopy(base)
    missing['resourceSpans'][0]['scopeSpans'][0]['spans'][0]['parentSpanId'] = 'e' * 16
    add('partial-parent', missing, ['missing_parent'], False, 1)
    retry = copy.deepcopy(base)
    retry_spans = retry['resourceSpans'][0]['scopeSpans'][0]['spans']
    retry_spans[1]['status']['code'] = 2
    success = copy.deepcopy(retry_spans[1])
    success['spanId'] = 'd' * 16
    success['status']['code'] = 1
    retry_spans.append(success)
    add('retry-preserved', retry, [], True, actions=2)
    boundary = copy.deepcopy(base)
    for span in boundary['resourceSpans'][0]['scopeSpans'][0]['spans']:
        span['startTimeUnixNano'] = str(2**64 - 2)
        span['endTimeUnixNano'] = str(2**64 - 1)
    add('uint64-boundary', boundary, [], True)
    overflow = copy.deepcopy(boundary)
    overflow['resourceSpans'][0]['scopeSpans'][0]['spans'][0]['endTimeUnixNano'] = str(2**64)
    add('uint64-overflow', overflow, ['invalid_timestamp'])
    cross = copy.deepcopy(base)
    cross['resourceSpans'][0]['scopeSpans'][0]['spans'][1]['traceId'] = 'f' * 32
    # Each trace becomes a separate run; the child-only trace is partial and has no output.
    add('cross-trace-parent', cross, ['missing_parent'], False, 1)
    malformed = copy.deepcopy(base)
    malformed['resourceSpans'].append({'scopeSpans': {}})
    add('malformed-sibling', malformed, ['invalid_shape'])
    duplicate = copy.deepcopy(base)
    duplicate['resourceSpans'][0]['scopeSpans'][0]['spans'].append(copy.deepcopy(spans[1]))
    add('duplicate', duplicate, ['duplicate_span'])
    limit = copy.deepcopy(base)
    limit['resourceSpans'][0]['scopeSpans'][0]['spans'] = [{} for _ in range(1001)]
    add('span-limit', limit, ['too_many_spans'])
    return dict(schema_version='trace-integration.cases.v1', synthetic=True, cases=cases)


if __name__ == '__main__':
    (HERE / 'cases.json').write_text(json.dumps(generate(), indent=2) + '\n')
