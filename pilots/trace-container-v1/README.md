# Trace-review reliability pilot — October 23, 2026

**Measured result:** the candidate stopped eight false accepts in a purpose-selected
synthetic regression set. The existing checker accepted malformed array containers
when a valid sibling supplied spans. Explicit container checks corrected that defect.

| Measure | Existing checker | Candidate |
|---|---:|---:|
| Exact diagnostic agreement | 12/20 | 20/20 |
| False accepts on eight malformed-sibling cases | 8 | 0 |
| False alarms on six valid controls | 0 | 0 |
| Original fixture expectations matched | 9/9 | 9/9 |

All predeclared technical acceptance criteria passed. Each implementation completed
100 measured batches of the same 20 inputs with stable diagnostics. These are
repetitions, not additional distinct examples. The full suite passed 16 unit test
methods; ten fixture expectations matched; original nine fixture bytes were unchanged;
fixture regeneration was deterministic. Output-overwrite and changed-input refusal
checks passed. See [release checks](results/2026-10-23/release-checks.json).

## Baseline, criteria and evidence

- [Protocol and business hypothesis](PROTOCOL.md), [frozen criteria](criteria.json),
  [20 input/label records](cases.jsonl), and [baseline source](baseline_tracecheck.py).
- [Protocol commit](https://github.com/Shawdaimarie/agent-trace-fixtures/commit/906d40859e2e846eac2e892924adaec2459d89f3)
  was published before the recorded 100-batch measurement. Development smoke tests
  preceded the freeze; the defect and candidate were already known.
- [Summary](results/2026-10-23/summary.json), [case-level results](results/2026-10-23/case-results.jsonl),
  [raw timings](results/2026-10-23/timings.jsonl), [hashes](results/2026-10-23/SHA256SUMS),
  and [integrity verifier](verify_results.py).

The local run used Python 3.12.14 on a shared macOS arm64 desktop. Median in-process
20-case batch time was 0.1801455 ms for baseline and 0.136375 ms for candidate;
nearest-rank p95 was 0.188541 ms and 0.141709 ms, respectively. Timings exclude startup,
imports and I/O. No speed threshold was specified; uncontrolled desktop timing
does not substantiate a general speedup, labor saving or production capacity claim.

## Reproduce

Requires Git and Python 3.11+. No third-party Python dependencies, credentials,
network calls during replay, customer data or model-provider charges are needed.

```sh
git clone https://github.com/Shawdaimarie/agent-trace-fixtures.git
cd agent-trace-fixtures
git checkout 906d40859e2e846eac2e892924adaec2459d89f3
python3 -m unittest discover -s tests -v
python3 tracecheck.py
python3 pilots/trace-container-v1/run.py \
  --protocol-commit 906d40859e2e846eac2e892924adaec2459d89f3 \
  --output /tmp/trace-container-v1-new-run
```

Use a new output path. Timing will vary. The checker diagnoses inputs within this
repository's small fixture profile; passing is not complete OTLP certification.
For the published result commit, verify the archive from that checkout with:

```sh
python3 pilots/trace-container-v1/verify_results.py \
  pilots/trace-container-v1/results/2026-10-23
```

## What this adds to a hiring profile

Project-result wording supported now:

> AI-assisted Python trace-validation pilot: improved exact diagnostic agreement
> from 12/20 to 20/20 on a frozen synthetic regression set, eliminating eight
> malformed-container false accepts while preserving all nine original fixture
> expectations; published baseline, acceptance criteria and reproducible raw evidence.

This is a technical result. Before converting it into a personal résumé bullet,
review the code and demonstrate the explanation and independent modification in
[the protocol](PROTOCOL.md#ownership-and-learning). The original résumé and its
timeline are unchanged. Do not add a seniority, client saving or revenue claim
from this experiment.

## What remains unproved

The practical value hypothesis is preventing misleading trace-review results.
Purpose-selected cases cannot estimate production accuracy or avoided incident
cost. No human manual-review baseline, customer acceptance, independent
reproduction, adopted workflow, collected revenue or financial saving is recorded.
AI-assisted local replay and archive reconciliation are not independent review.

The [follow-on measurement procedure](PROTOCOL.md#follow-on-workflow-measurement)
and empty [observation template](workflow-observations.csv) define how to test
review time and net capacity value with a consenting workflow owner. Keep the
existing review procedure available until that owner accepts the assisted process.
