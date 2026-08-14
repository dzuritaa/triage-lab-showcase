# Evaluation case study

## Published baseline

The current landing page still cites the accepted phase-1 system and
`evals/live-results.json`: 10/10 category, 6/10 priority, 5/5 correct abstention,
and 10/10 actionable-ticket retention on one 15-case run. Those numbers remain
published because the replacement has not passed its release gate.

## Experiments

| Experiment | Evidence | Outcome |
|---|---|---|
| First live model measurement | commit [`b8549c5`](https://github.com/dzuritaa/triage-lab-showcase/commit/b8549c5) | Exposed a systematic upward priority bias. |
| Deadline prompt fix | commit [`fb90bd2`](https://github.com/dzuritaa/triage-lab-showcase/commit/fb90bd2) | Made category, priority and retention worse; reverted. |
| Narrower abstention bar | commit [`7d6a879`](https://github.com/dzuritaa/triage-lab-showcase/commit/7d6a879) | Improved development retention but did not remove over-abstention. |
| Structured decision factors | `evals/dev-results-structured-3pass.json`, dev dataset `06b3f6bbb5aa…` | One-pass gate passed, but frozen three-pass confirmation passed only once. Not releasable. |
| Abstention flag removed, request rule added | `evals/dev-results-request-fix-3pass.json`, prompt `8aafd1b67c3b…`, commit `8abd395`, clean tree | Two of three frozen passes clear the gate. Priority 20/20 twice, P1 recall 12/12, abstention 30/30, one validation rejection in ninety attempts. Still not releasable: the gate requires three. |

The structured candidate keeps one model call, asks for triageability, affected
scope, impact and deadline evidence, and derives priority in Python. Across its
three frozen development passes:

| Pass | Category | Priority | Abstention | Retention | P1 recall | Rejected | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 17/20 | 17/20 | 10/10 | 18/20 | 3/4 | 1 | fail |
| 2 | 18/20 | 19/20 | 10/10 | 19/20 | 4/4 | 0 | pass |
| 3 | 17/20 | 16/20 | 10/10 | 18/20 | 3/4 | 2 | fail |

**This run is not reproducible, and that is recorded rather than repaired.** The
receipt states `prompt_sha256: 48e38bad…`, and no commit in this repository has
a prompt that hashes to it — the run was made against an uncommitted working
tree. The hashes of the current branch are not a substitute and have not been
written into the file. `evals/live.py` now records the git commit and whether
the tree was dirty, so this cannot recur silently.

### What the receipt actually says

Six of thirty cases account for every failure; the other twenty-four are correct
in all three passes, and abstention is 10/10 in each.

| Case | Passes affected | Cause |
|---|---|---|
| DEV2-010 | all three | Category label disputed. The set said `performance`; the model said `batch-reporting` three times out of three, and on review the model was right. Relabelled. |
| DEV2-016 | all three | A no-malfunction request ("standardise Ltd and LTD when convenient") drives an abstention. Twice it abstains outright; once it names a category *and* marks the ticket untriageable, which the validator rejects. |
| DEV2-017 | 1 and 3 | The same self-contradiction. Category and priority are right whenever the response survives validation. |
| DEV2-003, DEV2-006, DEV2-015 | one each | One impact-label flip apiece: `limited`↔`significant-impairment`, `multiple-users`↔`whole-site-or-department`, `limited`↔`request-or-cosmetic`. |

An earlier version of this section said P1 and P4 interpretation remained
unstable. The receipt does not support it: P4 wobbles once, P1 judgement never
does. Both failing passes lose `p1_recall` to a single ticket whose response was
rejected for contradicting itself, and a rejected attempt is dropped from the
numerator while staying in the denominator, so one contradiction costs a
category point and a retention point as well. Three of the five failing
conditions are that one defect, not a judgement about severity.

### After the two fixes

Removing the `triageable` flag and admitting requests as triageable moved every
metric, and the receipt is `evals/dev-results-request-fix-3pass.json`, recorded
against commit `8abd395` with a clean tree.

| Pass | Category | Priority | Abstention | Retention | P1 recall | Rejected | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 17/20 | 18/20 | 10/10 | 19/20 | 4/4 | 1 | fail |
| 2 | 18/20 | 20/20 | 10/10 | 20/20 | 4/4 | 0 | pass |
| 3 | 18/20 | 20/20 | 10/10 | 20/20 | 4/4 | 0 | pass |

Two of three, so the gate is not met. What moved: priority from a 16–19 spread
to 18–20, retention to 20/20 in two passes, rejections from three to one,
pooled P1 recall to 12/12. DEV2-016 is triaged rather than refused in every
pass, at the correct P4. What did not move: DEV2-010 and DEV2-016 are still
category misses in all three passes, and since the bar is 18/20 with two
permanent misses, every pass clears it with zero margin by construction.

The single rejection is the pre-existing consistency rule — `access-identity`,
`single-user`, `business-stopping` in one response. It is the same shape as the
contradiction removed above: the model disagrees with itself, the response is
thrown away, and one ticket costs a category point, a priority point and a
retention point at once. One occurrence in ninety attempts, and it failed a pass
on its own.

Both remaining category misses are label questions rather than judgement
failures, and both are open — see `docs/REVIEW-THREAD.md`. Neither will be
changed to make the gate pass.

The sealed candidate has never been sent to the model and will not be; see the
limitation below. No improvement claim is justified.

## Limitations

- The corpus remains 25 synthetic documents.
- **No independent reviewer was available, so `evals/golden-v2.json` stays
  unreviewed and unspent.** The development set can show that a candidate is
  worth keeping; it cannot produce a publishable score, because it is the set
  the candidate was tuned against. The structured work therefore stays on its
  branch and the page keeps citing the phase-1 measurement.
- The three-pass run above was produced by a prompt that was never committed.
- Repeated model passes measure output stability, not additional independent
  cases. They are reported separately rather than pooled as 90 observations.
- The current model and pricing are external dependencies checked manually.
