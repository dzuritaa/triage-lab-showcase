# ADR-002: Structured decision factors and deterministic priority

- **Status:** proposed; blocked by evaluation
- **Date:** 2026-08-13

## Context

The first paid measurement scored priority 6/10, below a 7/10 nearest-neighbour
baseline, with every miss escalating by one level. Prompt-only corrections
regressed other behavior.

## Proposed decision

Keep one model call, but ask the model for ticket-grounded evidence:
triageability, affected people, business impact, and a dated deadline. Python
maps those factors deterministically to priority and SLA. Retrieval appears
after the ticket and cannot supply missing decision facts.

The public response remains backward-compatible and adds `decision_factors`.
Model-supplied `priority` or `sla_hours` is rejected.

## Evidence and status

One development pass cleared the balanced gate. A frozen three-pass confirmation
then passed only once; see `docs/CASE_STUDY.md`. The sealed set remains unreviewed
and unqueried. Therefore this decision is implemented experimentally but not
accepted for publication or merge.

## Acceptance condition

All three development and human-reviewed sealed passes must independently reach
18/20 category, 16/20 priority, 9/10 abstention, 19/20 actionable retention,
4/4 P1 recall, zero validation rejection, and beat deterministic category and
priority baselines.
