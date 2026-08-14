# ADR-005: A published measurement carries the hash of the code that produced it

- **Status:** accepted
- **Date:** 2026-08-13
- **Reverses:** nothing
- **Reversed by:** nothing yet

## Context

The landing page's entire argument is that every number on it is reproducible.
That property is easy to state and hard to keep, because the numbers and the
code that produced them live in different files and drift apart silently.

It has now drifted three times:

1. The page carried one recorded call's token counts while the ADR it links to
   as proof still carried an earlier call's. Found by an independent design
   review reading carefully.
2. The recorded fixture was re-recorded and the page's prose was not. Found by
   `scripts/check_page.py`, which had been written after the first incident.
3. **The system prompt changed and the published model scores were not
   re-recorded.** The page cited numbers produced by code that no longer existed
   in the repository. Nothing found this for three commits, because
   `check_page.py` compared the page against the results *file* and never asked
   whether that file still described the current system.

The third is the interesting one. A guard existed, it was working, and it was
guarding the wrong join. Comparing a claim to a receipt proves the claim was
copied correctly. It says nothing about whether the receipt is still valid.

## Decision

**Every recorded run stores the SHA-256 of the prompt, the response schema and
the dataset it ran against. `check_page.py` recomputes those hashes and fails on
a mismatch.**

A results file carrying **no** hash also fails, rather than being waved through.
There is exactly one such file in the project's history and it was replaced
rather than exempted, because an exemption outlives everyone's memory of why it
was granted — and a guard with one permanent exception is a guard that will
acquire a second one.

The hash helper lives in `evals/validate_data.py`, a standard-library-only
module, so both the recorder and the page checker compute it identically and CI
can verify provenance with nothing installed.

## Evidence

Mutation-tested across four states before being trusted. Only the last passes:

| Results file | Outcome |
|---|---|
| No hashes recorded | fails — "nothing can confirm the published scores came from the code in this repository" |
| Prompt hash wrong | fails, naming the prompt and the re-record command |
| Schema hash wrong | fails, naming the schema |
| Both correct | passes |

It then found the real defect immediately: the published numbers had been
measured before a kept prompt change, and were re-recorded to close it.

The import chain is verified too. The first implementation imported the hash
helper from `evals/live.py`, which imports `anthropic` at module level — that
would have broken CI with an `ImportError`, a worse failure than the drift it
was meant to catch. Every module in the offline chain is now imported with
`anthropic` hidden as part of the check.

## The case against this decision

**A hash proves sameness, not honesty.** It confirms the recorded run used this
prompt and this schema. It cannot confirm that the run happened, that the
numbers were not edited afterwards, or that the model behaved as reported. The
protection is indirect: editing a results file to flatter the numbers requires
its hashes to still match, and the only practical way to produce matching hashes
is to actually re-run.

**The coverage is incomplete, and the gap is real.** The prompt, schema and
evaluation dataset are hashed. **The retrieval corpus is not.** Editing
`data/kb.json` or `data/incidents.json` changes what retrieval returns and
therefore changes the results, and nothing would detect that the published
numbers predate the change. The model *identifier* is recorded but the model
behind it is not pinned — a provider-side update to `claude-haiku-4-5` is
invisible here by construction.

**It makes CI red on a real repository state.** The gate is only useful because
it fails, and it will fail every time a prompt is edited before the measurement
is refreshed. That is the intent, and it is also a standing invitation to add an
exemption the next time it is inconvenient.

## Consequences

**Accepted.** A published model score cannot outlive the code that produced it
by more than one commit without CI saying so.

**Given up.** The ability to change the prompt and reconcile the page later. The
two now move together or the build is red, which makes a prompt change cost
about $0.05 and four files rather than one line — recorded in
`docs/MAINTENANCE.md` so the cost is anticipated rather than discovered.

**Deferred.** Hashing the retrieval corpus. It has been stable while the prompt
has not, so the cheaper guard was built first. This is a known hole, not an
oversight.

## What would change this decision

- **The corpus starts changing.** Hash `data/` into the same receipt. The
  argument for deferring it disappears the moment the dataset expansion in the
  plan begins.
- **Runs become expensive enough that a red build blocks work.** The answer then
  is a shorter path to re-recording, not a softer gate.

## Notes

The lesson generalises past this project: a check that compares two artifacts
proves they agree, and proves nothing about whether either still describes
reality. Both earlier incidents were caught by a human reading carefully, which
is not a control. This one was caught by a machine, which is.
