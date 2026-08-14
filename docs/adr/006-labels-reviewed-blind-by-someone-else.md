# ADR-006: Evaluation labels are reviewed blind, by someone who is not the author

- **Status:** not adopted — no reviewer available, and the dataset it would have
  reviewed turned out not to be independent. See "Outcome" below.
- **Date:** 2026-08-13, closed 2026-08-14
- **Reverses:** nothing
- **Reversed by:** nothing yet

## Context

The evaluation scores are this project's product. The demo is the vehicle; the
numbers and the reasoning are what a reader is asked to judge.

Those numbers rest on labels, and the labels were written by the person who also
writes the prompts, reads the results, and decides what "correct" means. That is
not an accusation of dishonesty — it is the ordinary shape of confirmation bias,
and it has a specific failure mode here: **a ticket whose label is ambiguous can
be resolved, unconsciously, in the direction the system already behaves.**

The project has already demonstrated it can measure itself onto favourable
ground without noticing. Every answerable case in the first golden set shares
subject matter with the retrieval corpus, which made an abstention retention
score of 10 out of 10 look like a property of the tool when it was substantially
a property of the test (ADR-003). Nobody chose that; it emerged from one person
writing both the corpus and the cases.

## Decision

**The sealed dataset's labels are confirmed by a support-domain practitioner who
is not the author, working blind, before any model call is made against it.**

- The reviewer receives `golden-v2.blind-review.json` — **ticket text only**.
  Not the expected labels, not the prompt, not model output, not retrieval
  results.
- They record category, priority and the corpus documents they consider
  genuinely useful, against a written rubric (`docs/LABEL_REVIEW.md`).
- Disagreements are resolved **before** any measurement, by discussion, and one
  side is updated to match the resolution.
- `python -m evals.review approve` validates every label and writes the dataset
  SHA-256 into a receipt. `evals/live.py --sealed` refuses to run against a
  dataset whose hash does not match an approved receipt.
- The receipt records a **role, never a name or an employer.**

The hash binding is what makes this more than a promise: the labels cannot be
edited after approval without invalidating the receipt and blocking the run.

## Evidence

An independent blind pass over all 30 sealed cases — ticket text only, labels
unseen until afterwards — agreed with the sealed labels on:

| Field | Agreement |
|---|---|
| Category | **30 of 30** |
| Priority | **30 of 30** |
| Relevant documents | 26 of 30 |

Including all ten `unknown` cases and the traps: a ticket reading *"Everything
is unavailable for the whole company. This is a critical outage"* reads as P1 and
is not triageable, and both passes marked it so.

That is meaningful evidence the rubric is tight enough to be applied
consistently by someone other than its author. **It is not the review**, and it
does not satisfy this ADR: the pass was made by a language model, which is the
same class of system under test, and no honest string exists for `reviewer_role`.
It has been recorded as what it is and cannot approve the receipt.

The four disagreements are all in `relevant_docs`, the softest field — for
example a dashboard that refreshes slowly but always completes, labelled against
a gateway-timeout article when nothing in the ticket times out.

## The case against this decision

**It is a dependency with no date, on the critical path.** Thirty sealed cases,
the structured-priority redesign and its ADR all wait on one unnamed person. A
sealed set that is never unsealed is worth less than an honest one that ships.

**Exact agreement is a demanding gate that can defeat its own purpose.**
Approval requires the reviewer and the author to match on all three fields for
all thirty cases. The intended outcome is a conversation. A plausible outcome is
the author talking the reviewer into agreement, which produces a receipt that
looks independent and is not. The rubric mitigates this by being written down
first; nothing enforces it.

**One reviewer is not inter-rater reliability.** Two people agreeing tells you
less than a measured disagreement rate across several. This buys independence,
not statistical confidence.

**The exported form is not answerable as shipped.** It asks for corpus document
IDs and contains no corpus, so the reviewer cannot complete `relevant_docs`
without a separate index that nothing currently generates.

## Consequences

**Accepted.** The strongest claim the project can make about its own numbers —
that the ground truth was not written by the person the numbers flatter — with a
hash-bound receipt rather than an assurance.

**Given up.** Speed. The sealed set cannot be measured at all until this
resolves, by design.

**Fallback, stated in advance.** If no reviewer is available, label as author,
record `author-labelled` in the receipt rather than leaving it `pending`
forever, and state the limitation on the page beside any number the set
produces. That is weaker than independent review and stronger than an
indefinite wait, and saying so up front is what stops the fallback becoming a
quiet default.

## Outcome — 2026-08-14

No support-domain practitioner outside the project was available, and none is
expected. The decision cannot be executed, so it is closed as **not adopted**
rather than left proposed indefinitely.

**The pre-committed fallback was not taken either.** This document said in
advance that the answer would be to author-label, record `author-labelled` and
publish with the limitation stated. The decision actually taken is a third
option: `evals/golden-v2.json` stays **unreviewed and unspent**.
`golden-v2.review.json` remains `pending-human-review`, which is what makes
`evals/live.py --sealed` refuse to run, and the refusal is now the intended
behaviour rather than an obstacle.

The reasoning for going further than the fallback: author-labelled numbers from
a set the author also wrote would be presented as a held-out measurement, and
the failure this ADR exists to prevent — measuring onto favourable ground
without noticing — is exactly the one that survives author labelling. Publishing
nothing costs a number. Publishing an author-labelled number costs the argument
that every claim here is checkable, which is the whole product.

Consequences, all of them real:

- The structured-priority candidate has no publishable score and stays on its
  branch. The page keeps citing the phase-1 measurement.
- The development set can still say whether a candidate is worth keeping. It
  cannot say how good it is, because it is the set the candidate is tuned
  against.
- Thirty sealed cases and a written rubric remain, unspent and undisclosed. If a
  reviewer ever appears, the review is still runnable exactly as designed, which
  is why the tooling is kept rather than deleted.

**Amended the same day: reviewing those thirty cases would not have helped.**
`golden-v2.json` agrees with `evals/dev.json` on the expected priority of all
thirty cases and the expected category of all thirty, position for position —
see ADR-004. A blind reviewer confirming the labels would have confirmed labels
that were correct and still not independent, and the receipt would have carried
a reviewer's role beside a measurement that re-asked the development questions.
The review was blocked on a person; the dataset was broken regardless of the
person. That ordering matters: a missing reviewer looks like a scheduling
problem, and this was never one.
- A fallback stated in advance and then not taken is worth recording as such.
  Pre-committing to a weaker option makes it easier to choose, and that is the
  point of writing it down — but it does not oblige anyone to take it when the
  weaker option turns out to cost more than it buys.

## What would change this decision

- **The dataset grows past what one reviewer can read.** Sampled review with a
  measured agreement rate replaces full review.
- **A second reviewer becomes available.** Then inter-rater reliability is worth
  more than the exact-agreement gate, and the gate should be relaxed to a
  measured disagreement threshold.
- ~~**No reviewer is found within the week.** Take the fallback and say so.~~
  Resolved 2026-08-14: no reviewer, and the fallback was rejected in favour of
  leaving the set unspent. See "Outcome".

## Notes

The blind form is exported by tooling rather than assembled by hand
specifically so the author cannot accidentally include the answers. The
`export` command refuses to overwrite an existing form, so a completed review
cannot be silently regenerated.
