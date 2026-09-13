"""Offline checks for a deliberately small OTLP JSON fixture profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

MAX_BYTES = 1024 * 1024


def inspect_trace(raw: bytes) -> list[str]:
    """Return stable diagnostic codes without echoing source values."""
    if len(raw) > MAX_BYTES:
        return ["input_too_large"]
    try:
        doc = json.loads(raw)
    except (ValueError, RecursionError):
        return ["invalid_json"]
    try:
        spans = [span for resource in doc["resourceSpans"]
                 for scope in resource["scopeSpans"] for span in scope["spans"]]
    except (KeyError, TypeError):
        return ["invalid_shape"]
    if len(spans) > 1000:
        return ["too_many_spans"]
    if not spans:
        return ["empty_spans"]
    issues: set[str] = set()
    parents: dict[tuple[str, str], str] = {}
    for span in spans:
        if not isinstance(span, dict):
            issues.add("invalid_shape")
            continue
        trace, sid, parent = span.get("traceId"), span.get("spanId"), span.get("parentSpanId", "")
        if not isinstance(parent, str):
            issues.add("invalid_identifier")
            continue
        identifiers = [(trace, 32), (sid, 16)] + ([(parent, 16)] if parent else [])
        if any(not isinstance(value, str) or not re.fullmatch(f"[0-9a-fA-F]{{{size}}}", value)
               or int(value, 16) == 0 for value, size in identifiers):
            issues.add("invalid_identifier")
            continue
        key = (trace.lower(), sid.lower())
        if key in parents:
            issues.add("duplicate_span")
        parents[key] = parent.lower()
        try:
            times = [span[name] for name in ("startTimeUnixNano", "endTimeUnixNano")]
            if any(not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value)
                   or int(value) > 2**64 - 1 for value in times):
                raise ValueError
            start, end = map(int, times)
            if end < start:
                issues.add("reversed_time")
        except (KeyError, ValueError):
            issues.add("invalid_timestamp")
    for trace, sid in parents:
        seen: set[str] = set()
        current = sid
        while current:
            if current in seen:
                issues.add("parent_cycle")
                break
            seen.add(current)
            key = (trace, current)
            if key not in parents:
                issues.add("missing_parent")
                break
            current = parents[key]
    return sorted(issues)


def check_corpus(root: Path, json_out: Path | None = None) -> int:
    manifest = json.loads((root / "manifest.json").read_text())
    fixtures = manifest["fixtures"]
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("fixture corpus must not be empty")
    inputs = {(root / item["file"]).resolve() for item in fixtures}
    inputs.add((root / "manifest.json").resolve())
    if json_out is not None and json_out.resolve() in inputs:
        raise ValueError("report cannot overwrite an input")
    results = []
    failures = 0
    for item in fixtures:
        path = (root / item["file"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("fixture path escapes repository")
        with path.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        actual = inspect_trace(raw)
        digest = hashlib.sha256(raw).hexdigest() if len(raw) <= MAX_BYTES else None
        fingerprint_matches = digest == item["sha256"] and digest is not None
        diagnostics_match = actual == item["diagnostics"]
        matches = fingerprint_matches and diagnostics_match
        results.append({
            "id": item["id"], "passed": matches,
            "expected_diagnostics": item["diagnostics"], "actual_diagnostics": actual,
            "diagnostics_match": diagnostics_match,
            "expected_sha256": item["sha256"], "actual_sha256": digest,
            "fingerprint_matches": fingerprint_matches,
        })
        print(f"{'PASS' if matches else 'FAIL'} {item['id']}: {','.join(actual) or 'valid-profile'}")
        failures += not matches
    if json_out is not None:
        report = {
            "schema_version": "agent-trace-fixtures.report.v1",
            "fixture_count": len(results), "failure_count": failures,
            "passed": failures == 0, "results": results,
        }
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json-out", type=Path, help="write machine-readable check results")
    args = parser.parse_args()
    try:
        return check_corpus(args.root, args.json_out)
    except (OSError, ValueError, KeyError, TypeError):
        print("ERROR: invalid or unavailable fixture corpus")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
