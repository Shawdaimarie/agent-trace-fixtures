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
    if not isinstance(doc, dict) or not isinstance(doc.get("resourceSpans"), list):
        return ["invalid_shape"]
    spans = []
    for resource in doc["resourceSpans"]:
        if not isinstance(resource, dict) or not isinstance(resource.get("scopeSpans"), list):
            return ["invalid_shape"]
        for scope in resource["scopeSpans"]:
            if not isinstance(scope, dict) or not isinstance(scope.get("spans"), list):
                return ["invalid_shape"]
            spans.extend(scope["spans"])
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


def check_corpus(root: Path) -> int:
    manifest = json.loads((root / "manifest.json").read_text())
    failures = 0
    for item in manifest["fixtures"]:
        path = (root / item["file"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("fixture path escapes repository")
        with path.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        actual = inspect_trace(raw)
        matches = hashlib.sha256(raw).hexdigest() == item["sha256"] and actual == item["diagnostics"]
        print(f"{'PASS' if matches else 'FAIL'} {item['id']}: {','.join(actual) or 'valid-profile'}")
        failures += not matches
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        return check_corpus(args.root)
    except (OSError, ValueError, KeyError, TypeError):
        print("ERROR: invalid or unavailable fixture corpus")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
