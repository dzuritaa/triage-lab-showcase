# Data dictionary

**Everything here is synthetic.** These tickets were written for this project.
They are not derived from any employer's, client's or university's ticket system,
and contain no real people, systems or data. Any resemblance to a real incident is
because enterprise IT fails in a small number of recognisable ways.

## Files

| File | Rows | Purpose |
|---|---|---|
| `incidents.json` | 10 | Resolved past incidents. Retrieval corpus + labelled examples. |
| `kb.json` | 15 | Knowledge base articles. Retrieval corpus. |
| `../evals/golden.json` | 10 | Held-out incoming tickets with expected labels. Never used as retrieval corpus. |

## Categories

| Category | Covers |
|---|---|
| `access-identity` | Authentication, SSO, group membership, permissions, lockouts |
| `integration` | File transfers, webhooks, APIs, credentials between systems |
| `performance` | Timeouts, slowness, saturation, degradation |
| `data-quality` | Duplicates, rounding, mismatched or malformed values |
| `batch-reporting` | Scheduled jobs, report generation and delivery |
| `process` | KB only. Reference material, not an incident category. |

`process` exists so the corpus contains documents that are plausible but not
tied to any one incident. Retrieval that cannot ignore them is not working.

## Priority and SLA

| Priority | Resolution target | Definition |
|---|---|---|
| P1 | 4 h | Business-stopping, or a whole site or department affected |
| P2 | 8 h | Significant impairment with a workaround, or a dated deadline at risk |
| P3 | 24 h | Single user, or non-urgent fault |
| P4 | 72 h | Request or cosmetic issue |

**Deadline pressure raises priority.** A single-user issue that blocks payroll
cutoff or month end close is P2, not P3. This rule is deliberate: it is the kind
of judgement a triage tool most often gets wrong, and the eval set includes cases
that turn on it.

## Incident fields

| Field | Notes |
|---|---|
| `id` | `INC-1001`+ |
| `channel` | `portal`, `email` or `phone`. Phone tickets are transcribed and read differently. |
| `reporter_role` | Job role, not a name. Shapes vocabulary and detail. |
| `raw` | The ticket as submitted. **Deliberately imperfect** — see below. |
| `category`, `priority`, `sla_hours` | Ground-truth labels |
| `resolution` | What actually fixed it |
| `root_cause` | Why it happened, distinct from the fix |

## Why the ticket text is messy

Real tickets are written by people having a bad morning. `raw` therefore contains
missing punctuation, absent capitalisation, run-on sentences, emotional framing,
irrelevant detail and — critically — **omitted information the triager actually
needs**. Several tickets never state the affected system.

Clean, well-structured synthetic tickets would inflate every score in the eval
and make the tool look better than it is. A support lead recognises fake tickets
immediately, and a demo built on them proves nothing.

## Known limitations

- Ten incidents is too few to generalise from. Phase 2 expands toward ~300.
- Categories are balanced two-per-category; real queues are heavily skewed
  toward access and password work.
- Every incident here was resolved. Real queues contain unresolved, misrouted and
  duplicate tickets.
- All text is British-English office register from a single author, so vocabulary
  variety is narrower than a real multi-site queue.
- **Not ambiguous enough.** Every ticket here carries enough detail to work out
  what it is about. A real queue contains tickets like "cannot enter site" with
  no system, no user and no context, which a human triager can only resolve by
  going back to the reporter. Reviewed by a support lead against this set, that
  was the gap worth naming: these are under-specified, but real ones are worse.
  Phase 2 adds genuinely ambiguous tickets, and the correct answer for some of
  them is "insufficient information — ask the reporter" rather than a category.
  A triage tool that confidently guesses on those is worse than one that admits
  it cannot tell.
