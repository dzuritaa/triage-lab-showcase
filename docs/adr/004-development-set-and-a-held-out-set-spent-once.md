# ADR-004: Prompts are tuned on a development set; the held-out set is spent once

- **Status:** accepted as a principle; **its second dataset failed to implement
  it** — see "The holdout was not one" below
- **Date:** 2026-08-13, amended 2026-08-14
- **Reverses:** the implicit practice of iterating against `golden.json`
- **Reversed by:** nothing yet

## Context

The first paid measurement found a systematic bias: priority scored below its
nearest-neighbour baseline, and **every miss was an escalation by exactly one
level**. Nothing was ever rated too low.

The diagnosis looked obvious. The system prompt's deadline rule only pushed
upward — it said deadline pressure raises priority and never said when a
deadline is slack — so any stated date read as pressure. The fix was to add the
missing downward half.

**It made things worse.** Priority fell from 6 of 10 to 4 of 10. It repaired one
case, broke three, and did nothing whatever to the three cases it was written
for, which escalated identically before and after. Category and retention each
fell by one. The clause that did the damage was the one that read as an obvious
clarification — *"reserve P1 for work that has stopped, not work that is slow,
degraded, or failing part of the time"* — which demoted a nightly load that had
halted with every dashboard in the business stale, the most clear-cut P1 in the
set.

Two lessons, neither about deadlines:

1. **The edit bundled two changes** into one "single" change, against a rule
   written into the project's own documentation hours earlier. The damage was
   attributable only because the failures happened to cluster on the P1/P2
   boundary. That was luck.
2. **There was nowhere to try a wording.** The only priority cases in the
   repository were the ten held-out ones, and tuning against those turns them
   into a training set — the leakage the plan explicitly warns about.

## Decision

**Two datasets with different jobs, and a discipline for spending them.**

- `evals/dev.json` exists **to be overfitted**. Tune against it as much as
  needed. Each case declares which failure mode it guards, so a change that
  fixes one class while breaking another is visible as two numbers moving in
  opposite directions rather than one average barely shifting.
- `evals/golden.json` (and its successor, the sealed set) is **spent once**, at
  the end, to find out whether anything real improved.
- **One change per run.** A run that cannot attribute its result taught nothing
  and cost money.
- Dev and sealed runs **write to different files**, so an iteration can never
  overwrite the measurement the landing page cites. Dev output is gitignored;
  it is regenerated on every attempt and meaningless out of context.
- **A regression in a guard class you were not aiming at is a stop signal**, not
  a rounding error.

## Evidence

The second attempt followed the discipline: one change, aimed at the abstention
bar, measured on the development set only.

| | Before | After |
|---|---|---|
| Held firm when it should | 4 of 9 | **6 of 9** |
| Category accuracy | 4 of 9 | **6 of 9** |
| Priority accuracy | 1 of 9 | **2 of 9** |
| Abstained when it should | 1 of 1 | 1 of 1 |

Nothing regressed, so it was kept — and the improvement survived to the
published measurement, where priority now reaches **7 of 10**, level with the
nearest-neighbour baseline it previously trailed.

The guard breakdown is what makes this readable. In a stubbed run that demoted a
single hard P1, the output reported `under-escalation 2 of 3` while the other
two classes stayed clean. A single accuracy figure would have shown a one-point
drop and hidden which failure mode had appeared.

The bias itself reproduced on cases it was never tuned against: of the four
development tickets that were triaged in the first baseline, three had the wrong
priority and **all three were escalations**. Across two independently written
sets that is seven escalations and zero de-escalations, which is what makes it a
bias rather than noise.

## The case against this decision

**It is slow, and it costs money to learn anything.** Every iteration is a paid
run — roughly $0.03 for the development set, $0.15 for a three-pass sealed run.
Prompt engineering by intuition is free and immediate; this is neither.

**The split is only as independent as its author.** Both sets were written by
the same person, from the same mental model of what a support ticket looks like.
Calling one "held out" describes how it is *used*, not where it came from. The
sealed set addresses this with a blind review (ADR-006); the development set
does not.

**Ten cases is small enough that a single spend is noisy.** A one-case change
moves the headline by ten points, which is why the three-pass gate exists — and
tripling the runs triples the cost.

**A guard class can be gamed.** Each development case declares what it guards,
and the labels were assigned by the same person tuning against them. A wording
that satisfies the guard without fixing the behaviour would pass.

## The holdout was not one — found 2026-08-14

`evals/golden-v2.json` was written to be the sealed set this decision requires.
It is not independent of `evals/dev.json`, and it never was. Compared row by row
in file order:

| Check | Result |
|---|---:|
| Same expected priority at the same position | **30/30** |
| Same expected category at the same position | **30/30** |
| Same relevant documents at the same position | 28/30 |

Thirty out of thirty on priority is not a coincidence between independent sets.
The two files were written case for case in the same order — same scenario
shape, same answer, same slot — so the "held-out" set re-asks the development
questions in different words. A prompt tuned until the development cases pass is
tuned onto its twin, and the sealed measurement would have come back optimistic
with nothing in the repository able to say so.

`python -m evals.validate_data` now prints those three figures on every run, so
the claim above is reproducible rather than asserted.

**Why the guard did not catch it.** `validate_dataset` asserted that no ticket
text was duplicated between the sets, and that assertion passed and still
passes. It checks for copied *words*; the leak was copied *structure*. A
uniqueness check on strings cannot see that case 17 in both files is the same
question.

**Consequence.** `golden-v2.json` is retired as sealed evidence. It may be used
as a regression set with its provenance stated, and it must never be described
as an independent measurement. A real holdout has to be written by someone who
has not read the development set, and kept out of this workspace until the
prompt and schema are frozen — which, with no independent author available, is
not a thing this project can currently produce. That is the honest end state
rather than a task waiting to be done.

**This is the second time a measurement here was made on favourable ground and
the repository could not see it.** The first was ADR-003's abstention retention,
10 out of 10 on cases that all shared subject matter with the corpus. Same
failure mode, one level up: the test was built by the person who built the
thing it tests.

## Consequences

**Accepted.** Prompt changes are attributable. The published number means what
it says, because it was not iterated against.

**Given up.** Fast iteration. Two prompt attempts consumed about $0.09 and most
of a working session, and one of them was reverted.

**Deferred.** Inter-rater reliability on the development set. One author, one
opinion, no second labeller.

## What would change this decision

- **Development and held-out results diverge systematically.** If a change that
  improves dev reliably fails golden, the split is measuring the difference
  between the two sets rather than the behaviour of the system, and both need
  rebuilding.
- **The corpus and datasets grow enough** that a single held-out spend stops
  being statistically fragile, at which point the ceremony around spending it
  can relax.
- **Someone who has not read `dev.json` writes the holdout.** That is the only
  thing that makes a second dataset independent, and it is a person, not a
  process. Until then this decision has a development set and no holdout, and
  says so.

## Notes

The discipline in this ADR was written down before the second attempt and
followed, which is the only reason the improvement is attributable to one
sentence. The first attempt was made after the same rule was written and before
it was believed.
