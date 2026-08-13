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
| Structured decision factors | prompt `934726736023…`, schema `653eae18e00b…`, dev dataset `06b3f6bbb5aa…` | One-pass gate passed, but frozen three-pass confirmation passed only once. Not releasable. |

The structured candidate keeps one model call, asks for triageability, affected
scope, impact and deadline evidence, and derives priority in Python. Across its
three frozen development passes:

| Pass | Category | Priority | Abstention | Retention | P1 recall | Gate |
|---|---:|---:|---:|---:|---:|---|
| 1 | 17/20 | 17/20 | 10/10 | 18/20 | 3/4 | fail |
| 2 | 18/20 | 19/20 | 10/10 | 19/20 | 4/4 | pass |
| 3 | 17/20 | 16/20 | 10/10 | 18/20 | 3/4 | fail |

It fixed the original abstention behavior on ambiguous tickets, but P1 and P4
interpretation remained unstable. The sealed candidate has never been sent to
the model. No improvement claim is justified until every frozen pass clears the
gate and a human-reviewed sealed set independently confirms it.

## Limitations

- The corpus remains 25 synthetic documents.
- Development labels come from the project author; the sealed candidate still
  requires blind support-domain review.
- Repeated model passes measure output stability, not additional independent
  cases. They are reported separately rather than pooled as 90 observations.
- The current model and pricing are external dependencies checked manually.
