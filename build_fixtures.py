"""Regenerate original synthetic fixtures; review manifest changes before committing."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRACE = 'a' * 32


def span(sid, parent='', name='agent.request'):
    return dict(traceId=TRACE, spanId=sid, parentSpanId=parent, name=name,
                startTimeUnixNano='1000000000', endTimeUnixNano='1100000000',
                kind=1, status={'code': 1})


base = [span('b' * 16), span('c' * 16, 'b' * 16, 'tool.lookup')]
cases = []


def add(name, spans, diagnostics, purpose, remove=None):
    doc = {'resourceSpans': [{'resource': {'attributes': [
        {'key': 'service.name', 'value': {'stringValue': 'synthetic-agent'}}]},
        'scopeSpans': [{'scope': {'name': 'agent-trace-fixtures'}, 'spans': spans}]}]}
    raw = (json.dumps(doc, indent=2, sort_keys=True) + '\n').encode()
    save(name, raw, diagnostics, purpose, remove)


def save(name, raw, diagnostics, purpose, remove=None):
    path = 'fixtures/' + name + '.json'
    (ROOT / path).write_bytes(raw)
    item = dict(id=name, file=path, sha256=hashlib.sha256(raw).hexdigest(),
                diagnostics=diagnostics, purpose=purpose)
    if remove:
        item['sensitive_markers'] = remove
    cases.append(item)


add('parent-child', base, [], 'Preserve parent/child relationships without network access.')
retry = copy.deepcopy(base)
retry[1]['status'] = {'code': 2, 'message': 'synthetic timeout'}
retry.append(span('d' * 16, 'b' * 16, 'tool.lookup.retry'))
add('retry', retry, [], 'Keep the failed attempt and successful retry distinct.')
sensitive = copy.deepcopy(base)
sensitive[0]['attributes'] = [
    {'key': 'http.request.header.authorization', 'value': {'stringValue': 'Bearer SYNTHETIC_TOKEN_DO_NOT_USE'}},
    {'key': 'user.email', 'value': {'stringValue': 'fixture-user@example.invalid'}}]
add('sensitive-attributes', sensitive, [], 'Exercise application redaction without real personal data.',
    ['SYNTHETIC_TOKEN_DO_NOT_USE', 'fixture-user@example.invalid'])
add('missing-parent', [base[1]], ['missing_parent'], 'Detect incomplete exports; not necessarily invalid OTLP.')
add('duplicate-span', base + [base[1]], ['duplicate_span'], 'Reject ambiguous duplicate span identity in this profile.')
cycle = copy.deepcopy(base)
cycle[0]['parentSpanId'] = 'c' * 16
add('parent-cycle', cycle, ['parent_cycle'], 'Detect cyclic parent relationships.')
reversed_time = copy.deepcopy(base)
reversed_time[1]['endTimeUnixNano'] = '999999999'
add('reversed-time', reversed_time, ['reversed_time'], 'Detect an end time before its start time.')
invalid = copy.deepcopy(base)
invalid[1]['spanId'] = 'not-hex'
add('invalid-identifier', invalid, ['invalid_identifier'], 'Reject malformed span identifiers.')
save('malformed-json', b'{not-json\n', ['invalid_json'], 'Reject truncated or malformed JSON cleanly.')
# A valid sibling must not let a malformed empty container disappear during iteration.
malformed_container = {'resourceSpans': [{'scopeSpans': [{'spans': base}, {'spans': {}}]}]}
save('malformed-container', (json.dumps(malformed_container, indent=2, sort_keys=True) + '\n').encode(),
     ['invalid_shape'], 'Reject a non-array spans container even beside valid spans.')
(ROOT / 'manifest.json').write_text(json.dumps(dict(schema_version='agent-trace-fixtures.v1',
    synthetic=True, fixtures=cases), indent=2) + '\n')
