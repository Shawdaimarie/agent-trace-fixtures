# Trace-to-evaluation contract v1

This integration runs the real Sentinel importer and evaluator at
`3b2e7cf0716e3940ef5f8af7beb0177408afe333`. It does not mock them, contact a
model provider, or execute tools named in a trace. Installation requires network
access; replay is offline. Python 3.11 or 3.12 and Git are required.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r integration/requirements.lock
git clone https://github.com/Shawdaimarie/sentinel.git /tmp/sentinel-integration
git -C /tmp/sentinel-integration checkout --detach 3b2e7cf0716e3940ef5f8af7beb0177408afe333
.venv/bin/python integration/run.py --sentinel /tmp/sentinel-integration --output /tmp/trace-integration-new
.venv/bin/python integration/verify.py /tmp/trace-integration-new --sentinel /tmp/sentinel-integration
SENTINEL_CHECKOUT=/tmp/sentinel-integration .venv/bin/python -m unittest discover -s tests -v
```

Use unused paths. The runner refuses to overwrite evidence. Exit status is 0 for
matched expectations, 1 for a contract mismatch, and 2 for a setup/input error.
The verifier returns nonzero on an error, including under optimized Python.
Without `SENTINEL_CHECKOUT`, five integration test methods are explicitly skipped;
the standalone corpus checks still run. CI supplies the variable.

## Input and diagnostic contract

`cases.json` is synthetic and versioned as `trace-integration.cases.v1`.
Each case has a unique ID, exact UTF-8 input and SHA-256, expected sorted diagnostics,
expected evaluation disposition, partial-run count and action count. Expectations
are authored from the stated behaviors, not inferred from checker output.
Regenerate with `python integration/build_cases.py`; review any expectation change.
The existing ten fixtures and the historical 20-case pilot remain separate.

The adapter applies the reference checker's limited profile **before** Sentinel.
Rejected inputs return diagnostics and are never passed to the consumer. An empty
diagnostic set or only `missing_parent` permits import. These diagnostics are the
wrapper's preflight result, not a claim of equivalent native Sentinel diagnostics.
This deliberately narrows the consumer's accepted inputs without modifying Sentinel.
An importer exception is a failed run, not an expected diagnostic match.

Missing-parent input can be a valid partial export. The importer preserves partial
state and the evaluation gate must fail for incomplete runs. The complete synthetic
cases must retain `synthetic completed` and a `lookup` action. Retry testing requires
two distinct span identities and both failed/executed status. Cross-trace parents
must not resolve to an unrelated trace. The uint64 test retains exact action start
time, while the overflow case is rejected by preflight.

## Output and evidence contract

`trace-integration.report.v1` records each input digest, diagnostics, normalized
consumer output, actual evaluation report, expectation checks, dependency versions,
source hashes and the pinned consumer revision. `passed` means every declared
expectation matched, including expected negative evaluation gates. It is not an
assertion that every input was valid or that every evaluated run passed.

The adapter envelope serializes normalized action `start_ns` values as decimal
strings for exact JSON interchange; Sentinel internally uses Python integers.
The normalized section is therefore an envelope representation, not an unchanged
native Sentinel manifest. Consumer `generated_at` is omitted from semantic
comparison. Ten repeated runs must produce identical semantic records; these are
not ten independent datasets.

Sentinel's native schema defaults absent cost to zero. No cost threshold is used
here, and the envelope records `business_cost_usd: null`: no measured business cost,
provider usage, timing benchmark, or savings claim is made. Root/trace topology and
useful output are asserted in addition to absence of the two exact synthetic markers.
This tests known marker removal, not general secret detection or DLP.

The verifier requires the complete source inventory, checks hashes, replays the real
consumer and compares semantic rows and original-fixture outcomes. It rejects changed
hashes, rehashed fabricated gates, omitted cases and empty normalized content. Hashes
are not signatures: someone able to replace code and all evidence can replace claims.
Execute only a trusted checkout. Source content hashes identify working-tree code;
`source_revision` is the containing base/commit and `source_worktree_dirty` discloses
whether uncommitted content existed when measuring.

## Recovery and independent review

The tests copy the saved artifact, corrupt it, verify rejection in normal and optimized
Python, restore original bytes, and verify successful replay. This is an artifact
recovery drill, not a production disaster-recovery or database restore exercise.
Changed consumer source is rejected before execution. Existing evidence is preserved.

A second person should use a fresh clone, install the lock, pin Sentinel, run the
commands, compare all semantic rows and record their identity, revisions and outcome.
AI-assisted local execution and CI are not independent human review. That review
remains outstanding; use [verification notes](../docs/MILESTONE-1-RESULTS.md) for
what was actually executed and [baseline reconciliation](../docs/BASELINES.md) for
branch ancestry. Maintainer review is required before merge.
