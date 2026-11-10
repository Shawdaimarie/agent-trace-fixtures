"""Replay a frozen baseline and candidate offline; no third-party dependencies."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_checker(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inspect_trace


def frozen_inputs(protocol_commit: str) -> tuple[dict, list[dict]]:
    """Require exact committed inputs, not just a caller-supplied revision label."""
    if not re.fullmatch(r"[0-9a-f]{40}", protocol_commit):
        raise ValueError("protocol commit must be a full lowercase SHA")
    criteria = json.loads((HERE / "criteria.json").read_bytes())
    paths = ["criteria.json", "run.py", "PROTOCOL.md", *criteria["sha256"]]
    for relative in paths:
        path = (HERE / relative).resolve()
        data = path.read_bytes()
        committed = subprocess.check_output(
            ["git", "show", f"{protocol_commit}:{path.relative_to(ROOT)}"], cwd=ROOT
        )
        if data != committed:
            raise ValueError(f"input differs from protocol commit: {relative}")
        expected = criteria["sha256"].get(relative)
        if expected and sha256(data) != expected:
            raise ValueError(f"input fingerprint mismatch: {relative}")
    baseline = subprocess.check_output(
        ["git", "show", f"{criteria['baseline_commit']}:{criteria['baseline_path']}"], cwd=ROOT
    )
    if baseline != (HERE / "baseline_tracecheck.py").read_bytes():
        raise ValueError("baseline snapshot differs from baseline commit")
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines()]
    if len(cases) != criteria["case_count"] or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("case count or identity mismatch")
    return criteria, cases


def replay(criteria: dict, cases: list[dict]) -> tuple[list[dict], list[dict]]:
    checks = {
        "baseline": load_checker(HERE / "baseline_tracecheck.py", "pilot_baseline"),
        "candidate": load_checker(ROOT / "tracecheck.py", "pilot_candidate"),
    }
    rows = []
    for case in cases:
        raw = case["input_utf8"].encode()
        for name, check in checks.items():
            actual = check(raw)
            rows.append({"id": case["id"], "cohort": case["cohort"], "implementation": name,
                         "input_sha256": sha256(raw), "expected": case["expected_diagnostics"],
                         "actual": actual, "match": actual == case["expected_diagnostics"]})
    # Warm up both implementations. Alternate execution order to reduce order bias.
    for check in checks.values():
        for case in cases:
            check(case["input_utf8"].encode())
    timings = []
    inputs = [c["input_utf8"].encode() for c in cases]
    expected = {name: [r["actual"] for r in rows if r["implementation"] == name]
                for name in checks}
    for repetition in range(criteria["repeats"]):
        order = list(checks) if repetition % 2 == 0 else list(reversed(checks))
        for name in order:
            start = time.perf_counter_ns()
            actual = [checks[name](raw) for raw in inputs]
            elapsed = time.perf_counter_ns() - start
            timings.append({"repetition": repetition, "implementation": name,
                            "batch_nanoseconds": elapsed, "stable": actual == expected[name]})
    return rows, timings


def summarize(criteria: dict, rows: list[dict], timings: list[dict]) -> dict:
    candidate = [r for r in rows if r["implementation"] == "candidate"]
    observed = {
        "candidate_exact_matches": sum(r["match"] for r in candidate),
        "malformed_sibling_rejections": sum(r["actual"] == ["invalid_shape"] for r in candidate
                                             if r["cohort"] == "malformed-sibling"),
        "valid_control_false_alarms": sum(bool(r["actual"]) for r in candidate if not r["expected"]),
        "original_fixture_matches": sum(r["match"] for r in candidate if r["cohort"] == "original"),
    }
    results = {}
    for name in ("baseline", "candidate"):
        subset = [r for r in rows if r["implementation"] == name]
        ns = sorted(r["batch_nanoseconds"] for r in timings if r["implementation"] == name)
        results[name] = {
            "exact_matches": sum(r["match"] for r in subset),
            "cases": len(subset),
            "false_accepts_malformed_siblings": sum(not r["actual"] for r in subset
                                                      if r["cohort"] == "malformed-sibling"),
            "valid_control_false_alarms": sum(bool(r["actual"]) for r in subset if not r["expected"]),
            "median_batch_ms": statistics.median(ns) / 1_000_000,
            "p95_batch_ms": ns[(95 * len(ns) + 99) // 100 - 1] / 1_000_000,
        }
    checks = {key: observed[key] == value for key, value in criteria["acceptance"].items()}
    checks["repeat_diagnostics_stable"] = all(r["stable"] for r in timings)
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "observed": observed, "implementations": results,
            "business_outcomes": {"review_time_saved": None, "customer_acceptance": None,
                                  "financial_savings": None, "production_adoption": None}}


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-commit", required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory; never overwritten")
    args = parser.parse_args()
    try:
        if sys.version_info < (3, 11):
            raise ValueError("Python 3.11 or newer is required")
        criteria, cases = frozen_inputs(args.protocol_commit)
        # Refuse overwrite before doing measurement work.
        if args.output.exists():
            raise ValueError("output already exists; choose a new directory")
        rows, timings = replay(criteria, cases)
        summary = summarize(criteria, rows, timings)
        summary.update({"pilot_id": criteria["pilot_id"], "protocol_commit": args.protocol_commit,
                        "baseline_commit": criteria["baseline_commit"],
                        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
                        "environment": {"python": platform.python_version(),
                                        "platform": platform.platform(), "machine": platform.machine(),
                                        "conditions": "shared local desktop; uncontrolled competing load"},
                        "timing_scope": "In-process 20-case batches; excludes startup, imports and I/O. Informational, not a speed or savings claim.",
                        "provenance": criteria["provenance"],
                        "repetitions_per_implementation": criteria["repeats"]})
        args.output.mkdir(parents=True, exist_ok=False)
        artifacts = {"summary.json": json_bytes(summary),
                     "case-results.jsonl": b"".join(json.dumps(r, sort_keys=True).encode()+b"\n" for r in rows),
                     "timings.jsonl": b"".join(json.dumps(r, sort_keys=True).encode()+b"\n" for r in timings)}
        for name, data in artifacts.items():
            (args.output / name).write_bytes(data)
        (args.output / "SHA256SUMS").write_text("".join(f"{sha256(data)}  {name}\n" for name, data in artifacts.items()))
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"pilot: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": summary["status"], "results": summary["implementations"]}, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
