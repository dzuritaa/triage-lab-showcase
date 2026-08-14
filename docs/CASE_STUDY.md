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
| DEV2-010 | all three | Category label disputed. The set said `performance`; the model said `batch-reporting` three times out of three. It was relabelled on that basis and the relabel was **reversed the next day** — see "The label that moved twice". |
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

### The label that moved twice

DEV2-010 — *"the annual compliance report times out whenever the full period is
selected"* — was labelled `performance`, relabelled `batch-reporting` because
the model had said so three times running, and then reverted to `performance`
the following day. The reversal is worth more than the label.

| Prompt | What the model answered |
|---|---|
| `48e38bad…` (three passes) | `batch-reporting` ×3 |
| `8eb73c0f…` (one pass) | `performance` |
| `8aafd1b6…` (three passes) | `performance` ×3 |

The model did not have a stable opinion. It answered one way under one prompt
and the other way under the next, so the three answers that justified the
relabel were not independent evidence about the ticket — they were three samples
of one prompt. The ticket sits on a boundary the taxonomy does not resolve:
"times out" is `performance` by the enum's own wording, and a report failing to
produce is `batch-reporting` by its own wording. Both readings are defensible,
which is what made the model's answer look like a verdict.

It was reverted to `performance` on the merits: the discriminating fact is that
a smaller range completes, which is a cost problem rather than a job that did
not run. `evals/dev.json` is now byte-identical to its pre-session state, hash
`06b3f6bbb5aa…`, which is the same dataset the older frozen receipt cites.

**The label change did not alter any verdict, and that is the point.**
Re-scoring the post-fix receipt against the reverted label gives category
18/19/19 instead of 17/18/18 — better, and still fail/pass/pass, because run 1
fails on a validation rejection either way. A relabel that improves the number
without changing the outcome is one that can be made honestly.

### What was left alone

The prompt is exactly as measured. The example sentence added for requests —
*"rename a field, tidy a display value or reschedule a job"* — mixes three
categories in one list and is the leading suspect for DEV2-016 now answering
`batch-reporting` where it previously abstained. The fix is known and small:
move the examples next to the categories they belong to. It has deliberately not
been applied, because applying it would leave the branch carrying a prompt that
no receipt in the repository measured, and shipping a claim whose evidence
describes different code is the defect this project has already corrected twice.

Both remaining category misses are label questions rather than judgement
failures. Neither was changed to make the gate pass.

The sealed candidate has never been sent to the model and will not be; see the
limitation below. No improvement claim is justified.

## Limitations

- The corpus remains 25 synthetic documents.
- **There is no holdout.** `evals/golden-v2.json` was built to be one and is
  not: it agrees with the development set on the expected priority and category
  of all thirty cases, position for position, so it re-asks the development
  questions in different words. It is retired as sealed evidence and never ran.
  ADR-004 carries the figures; `python -m evals.validate_data` reproduces them.
- **No independent reviewer was available either**, which blocked the review
  first and would not have fixed the dataset. The development set can show that
  a candidate is worth keeping; it cannot produce a publishable score, because
  it is the set the candidate was tuned against. The structured work therefore
  stays on its branch and the page keeps citing the phase-1 measurement.
- The three-pass run above was produced by a prompt that was never committed.
- Repeated model passes measure output stability, not additional independent
  cases. They are reported separately rather than pooled as 90 observations.
- The current model and pricing are external dependencies checked manually.
