# Baseline reconciliation — 8 November 2026

The apparent mismatch was branch history, not conflicting measurements:

| Revision | Role | Status when inspected |
|---|---|---|
| `c712de027af0812e927c3b9a5e8b4c669731b80c` | Original checker and nine fixtures | `main`; historical comparison baseline |
| `e91c1d08ed0c5307931c052164a3c592b53d59c2` | Machine-readable reporting proposal | Separate draft PR #1, not an ancestor of the pilot |
| `906d40859e2e846eac2e892924adaec2459d89f3` | Frozen pilot protocol, 20 cases, container-shape repair | Ancestor of PR #2; candidate's premeasurement revision |
| `748b9e2b61831ebf4b22057b2cf582d06ecd8894` | Published October pilot measurements | Unmerged PR #2, based on main |
| `0d7699f6769531d459d9c207c9745d6b81abba53` | Verifier checks remain active under `python -O` | Unmerged PR #3 stacked on PR #2; this milestone's implementation base |
| `3b2e7cf0716e3940ef5f8af7beb0177408afe333` | Sentinel importer/evaluator | Exact consumer pin for the new integration |

This milestone is stacked on PR #3. It does not merge prior proposals, reset main,
or rewrite frozen pilot inputs or results. PR #1's independent reporting proposal
is not silently folded in. Review/merge ordering remains #2 → #3 → this milestone.
The new integration report belongs to this branch, not to the original main checker.

The historical pilot's full provenance gate now runs from a real Git clone:
it checks frozen files against `906d408...` and baseline code against `c712de0...`.
The new replay reproduced baseline 12/20 and candidate 20/20 exact matches,
with 8 versus 0 malformed-sibling false accepts and no valid-control false alarms.
One hundred batches per implementation are repeated observations of 20 cases,
not 2,000 distinct test examples. See the new evidence archive, separately from
unchanged October evidence. There is no production accuracy or speedup claim.
