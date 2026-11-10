# Debugging silently skipped trace containers

The reference checker must reject a malformed container even when another
container supplies valid spans. Previously, an empty object or string at an
array position contributed no items to a nested comprehension. Valid spans
elsewhere could then produce an empty diagnostic list.

This walkthrough is for importer maintainers and engineers reviewing this
bounded bug fix. It requires Python 3.11 or newer and no external packages.

## Reproduce the failure

From the repository root, run:

```sh
python3 - <<'PY'
import json
from pathlib import Path
from tracecheck import inspect_trace

doc = json.loads(Path('fixtures/parent-child.json').read_text())
doc['resourceSpans'][0]['scopeSpans'].append({'spans': {}})
print(inspect_trace(json.dumps(doc).encode()))
PY
```

At base revision `c712de027af0812e927c3b9a5e8b4c669731b80c`, this prints `[]`.
With this fix, it prints `['invalid_shape']`. The document contains valid
parent/child spans, but the additional `spans` value is an object, not an array.
An empty dictionary is iterable and yields no keys; it does not raise the
`TypeError` the old code relied on for shape validation.

## Contract and acceptance criteria

| Input or behavior | Required result |
| --- | --- |
| Document is not an object | `invalid_shape` |
| `resourceSpans`, `scopeSpans`, or `spans` is missing or is not an array | `invalid_shape` |
| Resource or scope entry is not an object | `invalid_shape` |
| Valid spans coexist with a malformed container | `invalid_shape` |
| Well-shaped arrays contain no spans anywhere | `empty_spans` |
| Valid spans coexist with empty arrays | Existing span diagnostics; empty arrays add none |
| More than 1,000 spans across scopes | `too_many_spans` after container validation |
| Original nine fixtures | Existing diagnostics and SHA-256 values stay the same |
| Diagnostic output | Stable codes; no source values echoed |

An `invalid_shape` container error takes precedence over checks of individual
spans. The existing handling of non-object span entries remains unchanged.
The new synthetic `malformed-container.json` fixture deliberately combines a
valid span list with an empty object at another `spans` position. Its expected
result follows the contract above; it was not selected to fit the implementation.

## Approach and tradeoffs

Explicit `dict` and `list` checks precede each container traversal. Using Python's
generic iterable contract would be too permissive: JSON strings and objects are
iterable too. Missing keys and JSON `null` both fail the required-array check.
The loops preserve all spans for the existing identifier, timestamp, duplicate,
and topology checks. No schema library or runtime dependency is added.

Container collection remains linear in the number of resource entries, scope
entries, and spans, with a list proportional to span count. JSON parsing still
materializes the bounded input. The existing topology walk can be quadratic in
span count; this change makes no performance claim and does not alter that walk.

This is a local fixture-profile contract. It is not full OTLP validation.
The [OTLP JSON specification](https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding)
uses protobuf JSON encoding with specific deviations. This checker additionally
requires the container fields described here; it does not implement every
legal omission, encoding, attribute type, or transport behavior.

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 tracecheck.py
python3 build_fixtures.py
git diff --check
```

The expanded unit suite includes malformed values at each container level,
malformed siblings beside valid spans, empty-array compatibility, invalid
resource/scope entries, and the 1,000/1,001-span boundary across scopes. Ten
regression subcases failed against the base checker before the fix. In the
completed local check on Python 3.12.14, all 13 unit test methods and all ten
fixture expectations passed. Repeated generation preserved the new corpus
byte for byte. This is local evidence; a new GitHub CI run is separate.

The first nine fixture bytes and fingerprints were preserved. The tenth
fixture, generator, manifest, README, tests, and checker belong in the same
reviewed change. Returning `invalid_shape` instead of accepting malformed
containers is the intended compatibility change.

## Explain it independently

Before presenting this as your debugging work, explain:

1. Why `for x in {}` and `for x in ''` execute zero iterations.
2. Why a broad exception handler did not catch this bug.
3. Why the valid-sibling test is stronger than testing only an empty input.
4. Why `[]` should remain well shaped while `{}` is rejected here.
5. What the byte and span limits bound, and what they do not prove.

Then, without AI, add a test that inserts a malformed scope before the valid
scope instead of after it. Predict the result, run it, and explain whether input
ordering changes the contract. Keep the added test focused on observable behavior.

Development and this repair were AI-assisted. Passing automated tests proves
the covered behavior, not independent understanding, production adoption, or
standards certification.
