# Blind label review rubric

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

Resolve disagreements with the project author before any model call and update
the sealed labels or agreed review form to match the resolution. Then run:

```bash
python -m evals.review approve --reviewer-role "support practitioner"
```

The command validates every label and writes the matching dataset SHA-256 into
the approval receipt. Record only a general role—never a name or employer.
