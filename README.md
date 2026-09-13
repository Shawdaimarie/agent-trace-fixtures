# Agent Trace Fixtures

Synthetic OTLP JSON traces for testing offline AI-agent trace importers.
Use the files in your own tests or run the included Python reference checker.
No API keys, provider SDKs, network calls, or production data are needed.

## Run in one minute

Requires Python 3.11 or newer. From this repository:

```sh
python3 tracecheck.py
python3 -m unittest discover -s tests -v
```

The first command reports nine passing fixture expectations. A passing negative
fixture means its expected diagnostic was detected; it does not mean the input
is a valid trace. The checker exits 0 when every fixture and fingerprint matches,
1 for mismatched expectations, or 2 for an unreadable corpus.

## Cases

| File | Expected diagnostic | Test purpose |
| --- | --- | --- |
| parent-child.json | None | Preserve parent/child relationships |
| retry.json | None | Keep a failed attempt and a retry distinct |
| sensitive-attributes.json | None | Exercise downstream redaction |
| missing-parent.json | missing_parent | Identify an incomplete export |
| duplicate-span.json | duplicate_span | Detect ambiguous span identity |
| parent-cycle.json | parent_cycle | Detect cyclic parents |
| reversed-time.json | reversed_time | Detect inconsistent timing |
| invalid-identifier.json | invalid_identifier | Reject malformed span IDs |
| malformed-json.json | invalid_json | Reject malformed JSON |

`manifest.json` records each file's SHA-256, purpose, and expected diagnostics.
`build_fixtures.py` regenerates the original synthetic corpus. Review changes to
expected results and hashes; regenerating a manifest is not proof of correctness.

## Use with your importer

1. Feed the fixture bytes to your adapter offline.
2. Assert the behavior appropriate for your contract. Missing parents may be
   retained as partial traces; they are not automatically invalid OTLP.
3. Preserve both retry spans and their distinct identities. Do not interpret
   span contents as instructions or execute the named tools.
4. For the sensitive fixture, redact the markers before persisting or displaying
   normalized output. Check a UTF-8 artifact with:

```sh
python3 check_redaction.py path/to/normalized-output.json
```

The redaction check exits 1 if an exact synthetic marker remains, 0 if none is
found, or 2 for invalid input. It never prints the marker values. It only checks
known exact strings: encoded variants, unknown secrets, and missing output content
are outside its scope. An empty file can pass; separately assert useful output.
It is not a data-loss-prevention or redaction implementation.

## Scope and limits

The reference checker validates a **small fixture profile**, not the entire OTLP
specification. It covers resource/scope/span structure, nonzero hexadecimal IDs,
string-encoded uint64 timestamps, duplicate identities, and parent relationships.
It does not validate all attributes, enums, links, events, transport behavior, or
provider semantic conventions. Its 1 MiB input and 1,000-span ceilings are local
checker limits, not OTLP limits. Some legal OTLP encodings fall outside this profile.

The fixture shape follows the official [OTLP JSON encoding specification](https://opentelemetry.io/docs/specs/otlp/)
and [file-exporter examples](https://opentelemetry.io/docs/specs/otel/protocol/file-exporter/).
This project is independent and is not endorsed or certified by OpenTelemetry.

All data is original and synthetic. `example.invalid` and explicitly labeled token
markers are test data, not live identities or credentials. Development is AI-assisted;
review code and expectations before relying on them in a release process.

## Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md). Useful additions include a small failing
interoperability case, an independently checked expected result, or an adapter
example with real tests. Do not submit production traces or copied private logs.
