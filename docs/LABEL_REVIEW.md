# Blind label review rubric

The reviewer must be a support-domain practitioner and must not see model output,
retrieval results, prompt text, or expected labels before reviewing each ticket.

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

Resolve disagreements with the project author before any model call. Once all
30 labels are agreed, compute `python -m evals.validate_data`, copy the full
SHA-256 into `golden-v2.review.json`, set status to `approved`, and record only
the reviewer role and date—never a name or employer.
