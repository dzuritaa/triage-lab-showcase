# Blind label review rubric

> **Not in use, and the dataset it describes is retired.** No independent
> support-domain reviewer was available, and `evals/golden-v2.json` was then
> found to agree with the development set on the expected priority and category
> of all thirty cases, position for position — it is a rewrite of `dev.json`,
> not a holdout (ADR-004). Reviewing it would have confirmed correct labels on a
> dataset that could not measure anything independently.
>
> The rubric is kept because the procedure is still right and would apply
> unchanged to a set written by someone who has not read the development cases.
> `evals/live.py --sealed` refuses to run, and nothing here should be taken as a
> route to unblocking it.

The reviewer must be a support-domain practitioner and must not see model output,
retrieval results, prompt text, or expected labels. Export the blind form first:

```bash
python -m evals.review export
```

Give the reviewer only `evals/golden-v2.blind-review.json`. They complete its
three `review_*` fields for every ticket.

For every case, record independently:

1. Whether the ticket names enough to choose a category and sensible first step.
2. Category, or `insufficient-information`.
3. Priority using the mapping below.
4. Which corpus documents, if any, would genuinely help a triager.

Priority mapping:

- P1: an explicitly named team, department, site or company cannot continue its
  primary work and has no workaround.
- P2: significant impairment with a workaround, or a real dated commitment at risk.
- P3: limited fault affecting isolated users or records, with no dated commitment.
- P4: a working-behavior change or presentation request; no malfunction.
- unknown: the ticket cannot be triaged from its own text.

Discuss disagreements with the project author before any model call, and resolve
each one by changing the **sealed label** or by recording that the sealed label
stands. Never edit the reviewer's answers: a review that can be rewritten until
it agrees is not a review, and the agreement rate is worth publishing precisely
because it might not be perfect. Then run:

```bash
python -m evals.review approve --reviewer-role "support practitioner"
```

The command validates every label and writes the matching dataset SHA-256 into
the approval receipt. Record only a general role—never a name or employer.
