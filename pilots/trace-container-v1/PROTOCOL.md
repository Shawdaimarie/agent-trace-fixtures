# Pilot: prevent malformed trace exports from passing review

## Problem, user and value

An engineer reviewing an AI-agent trace needs to know whether an export satisfies
this repository's small fixture contract. The existing checker can silently skip
an empty object or string where an array is required. Valid spans elsewhere then
produce a passing result. The bounded improvement rejects the malformed container
and preserves valid empty-array siblings.

The intended business benefit is fewer misleading review results and less
downstream investigation. This run measures **technical defect detection**.
Customer adoption, review effort, avoided incidents and financial benefit have
not been observed. No dollar value or production failure rate is inferred.

## Baseline and approach

- Baseline: `tracecheck.py` at
  `c712de027af0812e927c3b9a5e8b4c669731b80c`, copied byte-for-byte into
  `baseline_tracecheck.py`, under the repository's MIT license.
- Candidate: explicit dictionary/list checks before flattening the spans.
- Same input bytes and exact expected diagnostic lists for both versions.
- Original nine fixture bytes and expectations remain unchanged. Eight additional
  cases vary the known defect across two container levels, empty object/string
  values, and malformed-before-valid/valid-before-malformed ordering. Three
  valid empty-array controls check compatibility. Total: **20 cases**, including
  six expected passes and fourteen expected rejections.
- `cases.jsonl` records every input, cohort and label. `criteria.json` freezes
  their fingerprints and both source fingerprints.

These are purpose-selected regression cases for an already discovered defect.
The candidate repair existed before this protocol. This is neither a blinded
experiment nor a held-out accuracy estimate. Labels come from the documented
local array/object contract, not from candidate output. Case selection emphasizes
one failure mode and cannot establish general importer correctness.

## Acceptance criteria, declared before this pilot run

| Criterion | Required result |
|---|---|
| Candidate exact diagnostic agreement | 20/20 cases |
| Malformed-sibling rejection | 8/8 return exactly `invalid_shape` |
| False alarms on valid controls | 0/6 |
| Original fixture compatibility | 9/9 exact matches |
| Repeatability | All repeated batches return the same diagnostics |

Run the repository unit tests and fixture generator checks as additional release
checks. Maintainer review is required before merge under `CONTRIBUTING.md`.
Independent reproduction and workflow-owner acceptance remain separate statuses.

## Measurement procedure

Development smoke tests precede the freeze. Commit this protocol, cases, runner,
baseline snapshot and candidate before collecting the published 100-batch
measurement. Pass the full protocol commit SHA to `run.py`; it checks local files
against that commit and compares the baseline snapshot with the original commit.
It refuses changed inputs and existing output directories.

Perform one warm-up batch for each implementation, then 100 measured batches per
implementation, alternating order. Each batch checks the same 20 cases. Retain
40 case-result rows and 200 batch timing rows, environment, source provenance,
summary and SHA-256 fingerprints. The repetitions test stable replay; they are
not 2,000 independent examples. Report median and nearest-rank p95 milliseconds
per in-process batch. Timing excludes startup, imports and I/O; shared desktop
load is uncontrolled. There is no speed acceptance threshold and no speedup claim.

On failure, keep the evidence, investigate and version the protocol rather than
changing labels to make results pass. Do not reuse this identifier for changed
inputs. Larger schema validation, provider integrations, production rollout and
real customer traces are outside this pilot.

## Follow-on workflow measurement

Before claiming business savings, a workflow owner must approve permitted data,
the existing review procedure, acceptance labels, costs and publication scope.
Record review/setup/support effort and the reviewer's context separately.

1. Agree at least 12 paired review tasks representing the actual workflow. Freeze
   labels before timing; record how the owner established them. Report the sample
   mix, including failures and clean controls. A synthetic sample stays labeled
   synthetic even when a human reviews it.
2. Use the same reviewer and equivalent tasks under the existing procedure and
   the assisted procedure. Counterbalance order; disclose familiarity and learning
   effects. Capture elapsed active review time, correctness, rework and tool errors.
   Do not treat automated runtime as human labor saved.
3. Proposed acceptance, for the owner to agree before collection: no false accepts
   on labeled malformed cases, all clean controls accepted, at least 25% lower
   median active review time, and reproducible handoff accepted by the owner.
   The 25% threshold is a target, not an achieved result or industry benchmark.
4. Record actual weekly eligible volume, adoption, loaded labor cost and all setup,
   maintenance and runtime costs. Model net capacity value as eligible volume ×
   adopted fraction × observed hours saved per task × documented hourly cost,
   less those costs over the same period. Capacity value differs from cash savings.
5. Obtain a dated owner acceptance, permitted quotation and publication approval.
   Keep confidential records private; publish only approved aggregates and method.

`workflow-observations.csv` is an empty collection template, not completed data.
There is no customer, fee, revenue or economic outcome recorded in this pilot.

## Ownership and learning

Implementation and documentation were developed with AI assistance. Repository
ownership does not establish independent coding fluency or external review.
Before presenting this as personal interview evidence, explain why an empty dict
vanishes in the original comprehension, why an empty list remains allowed, and
how a valid sibling can conceal malformed input. Reproduce the run, then add a
case with a malformed resource before a valid resource without AI assistance.
