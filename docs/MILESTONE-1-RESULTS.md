# Milestone 1 verification — 8 November 2026

Implementation: versioned synthetic corpus, bounded preflight adapter, actual pinned
Sentinel import/evaluation, semantic replay, evidence integrity checks, recovery tests
and reproducible CI. See [the contract](../integration/README.md) and
[baseline reconciliation](BASELINES.md).

Independent human reproduction and maintainer review remain outstanding. This is
AI-assisted implementation and verification, not a completed independent assessment.

## Verified results

Frozen implementation: [`05f2428d4002b1a70069a7653a214206aff0bbef`](https://github.com/Shawdaimarie/agent-trace-fixtures/commit/05f2428d4002b1a70069a7653a214206aff0bbef).
Measured from a clean checkout using Python 3.12.16 on macOS arm64. Dependency
versions and executable source fingerprints are recorded in the report.

| Check | Observed result |
|---|---|
| Unit tests with real consumer configured | 26 passed; none skipped |
| Existing fixture expectations | 10/10 matched, including the pilot's added malformed-container case |
| New integration cases | 10/10 expectations matched |
| Real consumer calls | Six importable cases; four complete cases pass evaluation and two partial cases fail evaluation as expected |
| Preflight rejection | Four malformed/out-of-profile cases rejected before consumer execution |
| Stability | Ten semantic repetitions identical; not independent examples |
| Original historical pilot | Baseline 12/20, candidate 20/20; false accepts 8 → 0; 100 batches each |
| Frozen Git provenance | Passed checks against the protocol and baseline commits |
| Redaction | Both known markers absent; useful output/actions retained; at least two attribute redactions |
| Recovery and integrity | Corrupt artifact rejected; restored original passes; rehashed fabricated gate, removed case and empty output rejected |
| Optimized Python | Semantic verifier and negative integrity checks remain effective under `-O` |
| Fresh environment | Fresh clone and separate virtual environment produced a byte-identical integration report on the same host |
| Regeneration | Fixture/manifest bytes unchanged; integration corpus regeneration identical |

The `retry-preserved` and `uint64-boundary` cases preserve distinct attempt identities,
failed/executed status and exact timestamps. The cross-trace parent remains unresolved.
No provider credentials, customer traces, live model calls or paid compute were used.

[Raw command results](../integration/results/2026-11-08/checks.json),
[test output](../integration/results/2026-11-08/unit-tests.txt),
[integration report](../integration/results/2026-11-08/integration/report.json),
[fresh-checkout report](../integration/results/2026-11-08/fresh-checkout/report.json),
[historical replay](../integration/results/2026-11-08/baseline/summary.json), and
[archive fingerprints](../integration/results/2026-11-08/ARCHIVE-SHA256SUMS).

The original October archive is unchanged. This run's timing data is retained for
transparency and does not substantiate a general performance improvement.
`main` remains the original baseline pending the existing review sequence.

## Scope of completion

The implementation, automated checks, same-operator fresh-environment reproduction,
and artifact recovery drill are complete. The blueprint's **second-person review**
criterion is not complete: no independent reviewer has signed off on the cases,
implementation or reproduction. CI is additional automated evidence, not that review.
No operational/business performance, production deployment or universal OTLP
conformance is claimed. The learned-model phases remain future work.

GitHub Actions also passed for the exact implementation commit on Python 3.11
and 3.12: [implementation CI run](https://github.com/Shawdaimarie/agent-trace-fixtures/actions/runs/42556133221).
