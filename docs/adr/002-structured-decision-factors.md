# ADR-002: Structured decision factors and deterministic priority

- **Status:** proposed; blocked by evaluation
- **Date:** 2026-08-13

## Context

The first paid measurement scored priority 6/10, below a 7/10 nearest-neighbour
baseline, with every miss escalating by one level. Prompt-only corrections
regressed other behavior.

## Proposed decision

Keep one model call, but ask the model for ticket-grounded evidence: affected
people, business impact, and a dated deadline. Python maps those factors
deterministically to priority and SLA. Retrieval appears after the ticket and
cannot supply missing decision facts.

The public response remains backward-compatible and adds `decision_factors`.
Model-supplied `priority` or `sla_hours` is rejected.

**Abstention is carried by the category alone.** An earlier version of this
decision also asked the model for a `triageable` boolean, which said exactly
what `category == "insufficient-information"` already said. The model
contradicted itself on three of ninety recorded attempts — a named category with
`triageable` false — and each contradiction was rejected outright, costing a
category point and a retention point as well as the answer. The field is gone
and derived back in Python for the response, so the contradiction is now
unrepresentable rather than merely detected. The cost is a real signal lost:
a response that disagreed with itself was worth knowing about.

## Evidence and status

One development pass cleared the gate. A frozen three-pass confirmation then
passed only once; the receipt is `evals/dev-results-structured-3pass.json` and
the reading of it is in `docs/CASE_STUDY.md`. That run is not reproducible — its
prompt was never committed.

**The sealed set will not be queried.** No independent support-domain reviewer
is available, so `evals/golden-v2.json` stays unreviewed and unspent; see
ADR-006. A development set is the set a candidate is tuned against, so clearing
the gate on it justifies keeping this design, never publishing a number from it.
This decision is therefore implemented experimentally on its branch and is not
accepted for publication or merge.

## Acceptance condition

Development set only. All three passes must **independently** reach 18/20
category, 16/20 priority, 9/10 abstention, 19/20 actionable retention, 4/4 P1
recall, zero validation rejection, and beat the deterministic category and
priority baselines.

Read that as it is written: eight conditions, all of which must hold in each of
three passes. It is a stricter bar than any single threshold in it suggests, and
two of the conditions are exact matches on small denominators — 4/4 P1 recall
over four cases, and 19/20 retention — so one intermittently wrong case can veto
a release on its own. That is deliberate: a missed P1 and a rejected response are
integrity failures rather than accuracy shortfalls. It also means a failure to
clear this gate is not by itself evidence that the design is wrong, and the
per-pass output now names which condition failed and on which tickets so the two
can be told apart.

Clearing it authorises keeping the candidate. It does not authorise a published
score.
