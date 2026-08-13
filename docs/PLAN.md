# Plan — what is left

Forward-looking only. This is deliberately **not** the 439-line plan that was
deleted on 2026-08-13: the threat model moved to `THREAT_MODEL.md`, the
experiment history to `CASE_STUDY.md`, and the diary was dropped on purpose.
Nothing here repeats them.

Five gaps, ordered by what unblocks the most. Items 1 and 2 are cheap and owned
by the repository. Item 3 needs a person and everything after it waits.

---

## Decision needed before item 3 can start

`LABEL_REVIEW.md` requires a support-domain practitioner who is not the author
and who never sees model output, prompts or expected labels.
`golden-v2.review.json` is `pending-human-review` with no reviewer and no date,
and ADR-002 is `blocked by evaluation`. So thirty sealed cases, the
structured-priority redesign and its ADR all wait on one unnamed person.

| | If a reviewer exists | If no reviewer is available |
|---|---|---|
| Path | Run the review as designed | Author-label, and say so publicly |
| Cost | Their time, plus one approval command | Nothing |
| What it buys | Labels the author cannot have biased | Progress, at the cost of the strongest claim |
| What it costs | A dependency with no date | The independence argument, which is most of why v2 exists |

**Recommendation: decide within the week, and prefer the fallback over an
indefinite wait.** Author-labelled data with the limitation stated is still
stronger than the great majority of portfolio projects, and a sealed set nobody
ever reviews is worth less than an honest one that ships. If the fallback is
taken, `LABEL_REVIEW.md` becomes a description of what *would* be done at scale,
and `golden-v2.review.json` records `author-labelled` rather than being left
pending forever.

---

## 1. Push, and find out whether CI works

**Why first.** Thirteen commits exist only on one laptop, `origin/main` is still
at the phase-1 close, and **CI has never run on any of this work** — not the five
offline checks, not the secret scan, not the `.gitattributes` LF handling that
exists specifically because the hook would otherwise die on Linux. Every claim
about CI in this repository is currently theory.

It also fixes a live defect: `CASE_STUDY.md` links to four commits by SHA, and
all of them 404 today because they are unpushed.

**Work.** Push `main`. Open the feature branch as a pull request rather than
merging it, so the branch protection story and the fork-PR path both get
exercised. Watch the run.

**Done when.** A green run exists on GitHub, and the CASE_STUDY links resolve.

**Cost.** Minutes. **Depends on.** Nothing.

**Risk to expect.** First Linux run of Python that has only ever executed on
Windows. Line endings, path separators and console encoding are the usual three;
the repository has guards for the first, and the third has already produced
mangled em-dashes locally.

---

## 2. Wire the provenance gate before the structured candidate merges

**Why.** `evals/live.py` already records `prompt_sha256`, `schema_sha256` and the
dataset SHA into every run — that half is done and is good. But nothing consumes
them: `scripts/check_page.py` never reads those fields, and the currently
published `evals/live-results.json` predates hashing, so it has none.

On `main` this is harmless — prompt and published numbers still match. It turns
into a real defect the moment the structured candidate merges, because that
branch changes the prompt while the page keeps citing numbers produced by the
old one. This is the same drift class that has already been caught twice by
hand, and the mechanism to stop it automatically is 90% built.

**Work.** Have `check_page.py` compare the recorded `prompt_sha256` and
`schema_sha256` against the live values and fail on mismatch, with a message
naming the re-record command. Treat a results file with **no** hash as a
failure rather than grandfathering it — the one such file will be replaced when
item 4 re-records anyway, and a silent exemption is how this kind of guard
quietly stops guarding.

**Done when.** Editing `SYSTEM` and running `check_page` fails with a message
that says what to re-run. Verified by mutation, as with the other gates.

**Cost.** Small, no paid run needed to build it. **Depends on.** Nothing.

---

## 3. Resolve the sealed-label review

**Work.** Whichever branch the decision above takes. If reviewed:
`python -m evals.review export`, hand over
`evals/golden-v2.blind-review.json`, resolve disagreements before any model
call, then `python -m evals.review approve`. If author-labelled: record that
honestly in the receipt and in `CASE_STUDY.md`, and state the limitation on the
page next to any number the set produces.

**Done when.** `golden-v2.review.json` carries a status that is not `pending`,
and a dataset SHA that matches the file.

**Cost.** Reviewer time, or nothing. **Depends on.** The decision above.

---

## 4. Close the two-golden-set fork

**Why.** `evals/run.py` still defaults to `golden.json` (15 cases) while
`golden-v2.json` (30) sits sealed and unused. The page cites v1; the newer
apparatus describes v2. Two sources of truth is tolerable while a candidate is
in flight and intolerable after it lands.

**Work.** Once item 3 unseals v2: decide whether v1 is retired or kept as a
regression set, point the offline scorecard at whichever is canonical, re-run
`evals.live` against it, and reconcile the page, ADR-001, `PRODUCT.md` and
`CASE_STUDY.md` to the new numbers. `check_page` will name anything missed.

**Done when.** One dataset is canonical, and every published number traces to a
run against it with matching prompt and schema hashes.

**Cost.** About $0.05 per live run, plus reconciliation. **Depends on.** 3, and
on 2 being in place first so the reconciliation is enforced rather than trusted.

---

## 5. Deploy

**Why.** Open since phase 1. It is one static file with no build step, and until
it is at a URL none of this argument is visible to anyone it was written for.

**Work.** Cloudflare Pages per the original plan, which also supplies the
`_headers` file for the CSP promised in `THREAT_MODEL.md`. Point it at `main`,
not the feature branch.

**Done when.** A cold visitor reaches the page over HTTPS, the documented
response headers are present, and the fixture renders with zero API calls.

**Cost.** An hour or so. **Depends on.** Item 1 only — it can run in parallel
with everything else.

---

## Deliberately not in this plan

| Not doing | Why |
|---|---|
| Expanding the dataset toward 300 incidents | The small corpus has produced more findings than a large one would have. Volume is not the bottleneck; label quality and the review gate are. |
| The Worker API, live mode, rate limiting | Phase 3. Nothing on the page implies they exist. |
| Astro and the docs site | Phase 4. One hand-written page is still the right size. |
| Fixing priority over-escalation by prompt alone | Tried twice, made things worse both times. ADR-002 is the current answer and it is gated on item 3. |
| A sixth category for network connectivity | Real gap, found by a withdrawn test case. It is a product decision, not a bug, and it can wait for evidence that real tickets need it. |
