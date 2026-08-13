# Handoff — triage-lab

Written 2026-08-12, at the close of phase 1. This is the document to read first
if you are picking the project up cold, including if you are the author six
months from now.

---

## 1. What this is

An incident triage assistant for enterprise IT support. Paste a raw ticket, get
a category, a priority with an SLA target, similar past incidents, a drafted
first reply and a root-cause direction.

The demo is the vehicle. The point is the **evidence**: a published evaluation
with baselines, architecture decisions written down with the case against them,
and a threat model, all reproducible from the repository. It exists because
twelve years of incident management, ITSM and internal tooling sit behind
corporate walls where no employer can read a line of it.

**Public repository:** https://github.com/dzuritaa/triage-lab-showcase

---

## 2. Where it stands

| Phase | State |
|---|---|
| 0 — Skeleton and guardrails | ✅ closed |
| 1 — Public vertical slice | ✅ closed (7/7 steps) |
| 2 — Dataset, core and eval expansion | started: priority scored, abstention built and baselined, page guarded |
| 3 — Worker API | not started |
| 4 — Web (Astro) | not started |
| 5 — Docs (remaining ADRs, C4) | 1 of ~6 ADRs written |
| 6 — Polish, launch, CV | not started |

Phase 1's bar was: *a cold visitor can see one complete result, inspect the code
and evaluation, understand one design decision and contact David, with zero API
calls.* All four are met.

### Measured, as of this handoff

| Metric | Score | Baseline |
|---|---|---|
| Retrieval recall@1 | 60% | 8% (random) |
| Retrieval recall@3 | 90% | 23% (random) |
| Category accuracy | 60% | 20% (majority class) |
| Priority accuracy | 70% | 40% (majority class) |

Priority is the newest and the least impressive of these despite scoring
highest: eight of the ten held-out cases are P2 or P3, so the four-way label
behaves like a two-way one. It is a bar for the model, not an achievement.

### The model, measured 2026-08-13 (`python -m evals.live`, $0.0424)

| Metric | Model | Baseline |
|---|---|---|
| Category accuracy | **10 of 10** | 6 of 10 (nearest neighbour) |
| Priority accuracy | **6 of 10** | 7 of 10 (nearest neighbour) |
| Abstained when it should | **5 of 5** | 0 of 5 measured, 3 of 5 best possible |
| Held firm when it should | **10 of 10**, but see below | 10 of 10 |

⚠️ **Held firm 10 of 10 is measured on friendly ground and must not be quoted
alone.** On the development set, whose tickets are about systems the corpus does
not cover, it is 4 of 9. See "Abstention is coupled to knowledge-base coverage"
in §5 — that is the single most important open defect in the project.

**Priority is the one metric where the model loses to a keyword search, and the
shape of the loss matters more than the number.** All four misses are
escalations, each by exactly one level; nothing was ever rated too low. The
likely cause is the system prompt's deadline rule, which only pushes upward: it
says deadline pressure raises priority and never says when a deadline is slack,
so EVAL-07's "mailing list is going out next month so we have time" was read as
pressure. EVAL-06 states no deadline at all and was raised on user count — the
exact thing the same sentence forbids.

The fix is a prompt change and is deliberately **not applied**: editing the
prompt invalidates the numbers above, so the order is publish, then change one
thing, then pay for another run. See the open items.

Abstention is scored on a separate set of **5 ambiguous cases** whose correct
answer is "ask the reporter". Every metric above is measured on the 10
answerable cases only; merging the sets would change what recall@3 means, since
retrieval recall over a case with no right answer is not a number.

| Metric | Baseline | Note |
|---|---|---|
| Abstained when it should | 0 of 5 | retrieval, at the pre-existing 3.0 low-score threshold |
| Best any threshold could do | 3 of 5 | oracle, chosen with sight of the answers |
| Held firm when it should | 10 of 10 | over-abstention is the costlier error |

**No model score exists for abstention yet.** The capability is built and the
eval is waiting for it; see the open items.

One recorded live call, Claude Haiku 4.5: 1,728 in / 285 out, **$0.0032**, about
1,600 tickets per $5. Reproduce the scores with `python -m evals.run`.

---

## 3. Repository map

```
triage-lab/
  data/            synthetic corpus + data dictionary (README.md is worth reading)
  core/retrieve.py BM25, standard library only, self-checking
  core/triage.py   the one module that calls the model (needs `anthropic`)
  evals/           golden.json (10 answerable + 5 ambiguous) + run.py (scorecard, CI gate)
  fixtures/        one recorded real result; the page renders this
  web/index.html   the landing page, single file, no build step
  docs/            PLAN.md (plan + threat model + audit log), adr/, MAINTENANCE.md
  scripts/         canary-check.sh — proves the secret gates work
                   check_page.py  — proves the page publishes only what it can produce
  PRODUCT.md       product truth (users, principles, what must not be invented)
  DESIGN.md        the visual system
```

### Running it

```bash
python -m core.retrieve            # retrieval self-check, no dependencies
python -m core.triage --check      # response validation rules, no key needed
python -m evals.run                # scorecard, no dependencies, no network
python -m scripts.check_page       # page matches the fixture and the scorecard
python -m core.triage --fixture    # replay the recorded result, no API call
sh scripts/canary-check.sh         # verify the secret gates (needs Docker)
```

Live calls only:

```bash
pip install -r requirements.txt
# copy .env.example to .env, put a real key in it
python -m core.triage "ticket text here"
python -m core.triage --record EVAL-03      # re-record the fixture
python -m evals.live                        # score the model, ~15 calls, ~$0.05
python -m evals.live --ambiguous            # the 5 abstention cases only, ~$0.02
python -m evals.live --dev                  # priority development set, 10 calls, ~$0.03
```

**Tune against `--dev`. Measure with the golden set, once, at the end.**
`evals/dev-priority.json` exists to be overfitted; `evals/golden.json` is held
out, and a prompt tuned until its ten cases pass is fitted to them. The two
runs write to different files so an iteration cannot overwrite the measurement
the landing page cites, and `evals/dev-results.json` is gitignored because it is
regenerated on every attempt.

The dev set is built from the failure modes actually observed, not from
imagined coverage, and every case declares which one it guards:

| Guard | Cases | What it pins |
|---|---|---|
| `over-escalation` | DEV-01, 02, 03, 07 | The measured bias — user count alone, a recurring meeting, a comfortable deadline, an intermittent fault |
| `under-escalation` | DEV-04, 05, 06 | The over-correction — a real external deadline, a dated commitment with an expensive workaround, and a genuine full stoppage |
| `abstention-leak` | DEV-08, 09, 10 | The regression nobody predicted — terse-but-sufficient and hedged-but-specific tickets must still be triaged, and an empty one must still abstain |

`--dev` prints a per-guard breakdown. That is the point of the set: a change
that fixes over-escalation while breaking the P1 floor shows as one class
improving and another regressing, which a single accuracy figure hides — and
which is exactly what the reverted attempt did.

DEV-06 and DEV-07 are deliberately the same system and symptom class, total
versus intermittent. A single case cannot pin a boundary; a pair can.

`evals/live.py` is the only thing that scores the *model*; everything in
`evals/run.py` measures what retrieval can do alone. It writes
`evals/live-results.json` so the numbers are citable rather than living in a
console scrollback. It is deliberately not wired into CI — that needs a trusted
workflow holding the secret, and it spends money on every push. Phase 2's
workflow-split item covers it.

**PowerShell note:** `&&` is not a statement separator in Windows PowerShell 5.1.
Run the commands separately.

---

## 4. Decisions worth knowing

Each of these was made deliberately and is reversible; the reasoning matters
more than the choice.

| Decision | Why | Reverses when |
|---|---|---|
| **BM25, no vector database** | 25 documents. No embeddings endpoint from Anthropic, so vectors mean a second vendor and bill on day one. Beats random 4×. | Corpus past ~5,000 docs, or recall@1 starts mattering more than recall@3. Full reasoning in `docs/adr/001`. |
| **Model is Haiku 4.5, `TRIAGE_MODEL` overrides** | The operator's explicit call, not a cost downgrade chosen for them. $1/$5 per MTok vs Opus 5's $5/$25. | Evals show the cheap tier failing on cases that matter. |
| **Official `anthropic` SDK, not hand-rolled HTTP** | Anthropic's guidance is the SDK where one exists. Only `core/triage.py` takes the dependency. | Never — but keep `retrieve.py` and `evals/` standard-library so CI installs nothing and fork PRs need no secret. |
| **`thinking` deliberately unset** | Newer models think adaptively by default, older ones do not think unless asked. Both correct here. Explicitly disabling it on newer models can leak internal tags into visible output. | — |
| **The tool may decline to classify** | A ticket that names no system and no symptom has no category, and guessing one is worse than asking. `insufficient-information` is a triage outcome, which is how ServiceNow and Jira SM already model it, so it extends the category enum rather than adding a parallel flag. Extending an enum also cannot break structured output, and this repository cannot test a request shape without spending a key on it. | Evals show it abstaining on tickets the desk could have acted on. That is the costlier error and it is scored separately. |
| **Fixtures by default, live mode opt-in** | A recruiter opening the page must cost nothing and never see a broken demo. | — |
| **Synthetic data only, labelled where shown** | No employer, client or university data, ever. Stated publicly as judgement, not limitation. | Never. |
| **Auto-reload OFF on the API account** | The load-bearing cost control. A $5 balance is a hard stop that cannot bill the card without a human action; no application-level limiter can promise that. | Never turn it on. |

---

## 5. Issues found and how they were fixed

Kept because most of these are the kind that recur, and several were found only
because something was tested rather than assumed.

### Security and secrets

**gitleaks does not detect Anthropic keys out of the box.** A correctly-shaped
key was planted and the stock ruleset reported "no leaks found". Had the standard
action been wired up and trusted, the key would have had zero protection behind a
green badge. → Custom `anthropic-api-key` rule in `.gitleaks.toml`, tested in
both directions, plus a GitHub PAT to confirm the default rules were active at
all.

**CI is detection, not prevention.** A key that reaches history must be rotated
even if never pushed. Proven concretely: a key was committed, the file deleted,
the deletion committed — a spotless working tree — and CI still failed, because
history is permanent. → Added a pre-commit hook (`.githooks/pre-commit`) that
blocks the commit before it exists.

**The pre-commit hook blocked every commit whenever Docker Desktop was
installed but not running** — the state a laptop is in most of the time. It
tested `command -v docker`, which finds the CLI on PATH and says nothing about
the daemon, so the guard passed, `docker run` failed on an npipe connection
error, and `set -e` turned that into a blocked commit with a message about
named pipes. The hook's own comment and the README both promise it warns and
defers to CI when Docker is unavailable. It did the opposite, and neither CI
nor `canary-check.sh` could catch it: both need Docker running to run at all,
which is precisely the case where the bug is invisible. → Probe `docker info`,
which covers a missing binary and a stopped daemon in one check. Found by
trying to commit.

**The pre-commit hook would have died on Linux CI.** Windows checkout would have
given it CRLF line endings and an opaque "bad interpreter" error. → `.gitattributes`
forcing LF.

**A real API key was printed into a chat transcript.** A gitleaks scan was run by
hand without `--redact`, which prints matched secrets in full. The repository was
never at risk (`.env` is gitignored and was never staged); the transcript was the
whole exposure. → Key rotated. `--redact` is now non-optional inside
`canary-check.sh`'s `scan()` with a comment saying why.

**The canary script blocked legitimate commits.** It scanned with `--no-git`,
which ignores `.gitignore`, so it read the developer's real `.env` and failed its
own clean-tree assertion — it broke the moment someone followed the README. →
Now scans a scratch directory for the canary and git-tracked content for the
clean check. The script behaved correctly in one sense: it is designed to fail
loudly when the gate blocks legitimate work, and it did.

**A hook test read as a false failure.** The probe key was 71 characters after
the prefix; the rule requires 80+. It looked like the hook was broken when the
hook was fine. → Correct-length probe, and the length requirement is now noted in
the script.

**Work email on every public commit.** All commits carried a Temenos address,
which is both harvestable and attributes a personal project to an employer
identity. → History rewritten to a GitHub noreply address. The repository was
deleted and recreated rather than force-pushed, because orphaned commits stay
reachable by direct SHA after a rewrite. Recorded as a pre-push check in
`docs/PLAN.md` §4, which also checks the *committer*, not just the author.

### Abstention is coupled to knowledge-base coverage, and the golden set cannot see it

The first `--dev` run was meant to establish a priority baseline. It found
something worse. **The tool refused 5 of the 9 answerable development tickets**,
against 0 of 10 on the golden set.

The cause is not vagueness. It asked for the exact error message, the payment
gateway vendor, the VPN client version — diagnostic detail. DEV-06 reads
*"Customers cannot pay. The checkout gets to the card step and then errors,
every single time, for everyone. Nothing is going through at all. This is the
whole online shop."* — system and symptom both named, and refused. The
abstention criterion has drifted from *can I triage this* to *can I diagnose
this*, and the prompt's own definition is the narrower one: "you can tell what
system is involved and what it is doing wrong."

The pattern across the nine is close to mechanical, and it is not length or
retrieval score — the two sets match almost exactly on both (45 vs 47 words,
11.5 vs 12.3 median top score):

| Retrieval returned | Cases | Outcome |
|---|---|---|
| Something topically related | DEV-01, 02, 04, 05 | all triaged |
| Something unrelated | DEV-06, 07, 08, 09 | all refused |

Checkout tickets pulled back an overnight batch failure and an account-lockout
article; the VPN ticket pulled back SFTP key rotation. DEV-03 is the single
exception — a related hit, refused anyway.

**Abstention therefore tracks what the corpus happens to cover rather than what
the ticket says.** For a service desk that is backwards: an unfamiliar system is
exactly when a triager wants help, and the behaviour degrades silently every
time the business adds one.

**Why the golden set was blind to it.** Its answerable cases are paraphrases of
corpus incidents — same subjects by construction, which is what makes them a
fair retrieval test. That same property means every one of them lands on
friendly ground for abstention, so "held firm 10 of 10" measured subject overlap
as much as judgement. The dev set broke the overlap by accident, writing about
checkout, VPN and purchase-order screens because those were convenient priority
scenarios, not because anyone set out to test corpus coverage.

The landing page has been corrected: 10 of 10 now carries the condition it was
measured under, and 4 of 9 is published beside it. Baseline run kept as
`evals/dev-results-baseline.json`.

**Practical consequence: this blocks the priority work.** Five of nine dev cases
never reach a priority, so the set cannot do the job it was written for until
abstention is fixed. Fix that first, re-baseline, then tune priority.

### Candidate 1: narrowing the abstention bar, which helped and did not finish

The first fix attempt that survived contact. The prompt already said "ask only
for what actually blocks the decision", which was too abstract to bite. The edit
names the decision — a category, a priority, a first step — lists the detail
that does *not* change any of the three, and gives the model somewhere else to
put it: **"When you want that detail, ask for it in draft_reply and triage the
ticket anyway."** That last clause is the substance. The model wanted to ask
those questions and the schema left it only two options: abstain, or drop them.

| | Baseline | After |
|---|---|---|
| Held firm when it should | 4 of 9 | **6 of 9** |
| Category accuracy | 4 of 9 | **6 of 9** |
| Priority accuracy | 1 of 9 | **2 of 9** |
| Abstained when it should | 1 of 1 | 1 of 1 |

DEV-03 and DEV-07 recovered. Nothing regressed, so the change was kept.

**It did not finish, and the way it failed is informative.** DEV-06, 08 and 09
still refuse, and what they ask for is precisely the four things the new text
names as non-blocking: the exact error message, the vendor, the version, the
time it started. The instruction is being read and overridden on the hardest
cases, which suggests something other than ignorance of the rule is driving the
refusal on those three — retrieval coupling remains the live hypothesis for
DEV-06 and DEV-09, both of which still pull back unrelated documents.

DEV-08 turned out to be a bad case rather than a bad result; see the taxonomy
item in the open list. One mild cost: DEV-03 recovered from abstaining into P4
where P3 was wanted, the first de-escalation seen from any prompt version.

### The escalation bias reproduces on cases it was never tuned against

Smaller, and good news for the diagnosis. Of the four dev tickets that were
triaged, three have the wrong priority and **all three are escalations** —
DEV-01 and DEV-02 P3→P2, DEV-05 P2→P1. Combined with the golden run's four of
four, that is seven escalations and zero de-escalations across two independently
written sets. The bias is real and not an artifact of the golden set.

### The obvious fix for the escalation bias, which made it worse

The first live run showed priority at 6/10 with all four misses escalating by
exactly one level. The diagnosis looked solid: the system prompt's deadline rule
only pushes upward, so any stated date reads as pressure. The fix was to add the
missing downward half — a comfortable deadline is not pressure, an absent
deadline means judging on impact alone, user count alone does not raise
priority, and P1 is for work that has stopped rather than work that is degraded.

**It took priority from 6/10 to 4/10.** Nothing else was touched; the golden set
was not edited, so the delta is attributable to the prompt.

| Case | Expected | Before | After | |
|---|---|---|---|---|
| EVAL-04 | P2 | P1 | **P2** | fixed |
| EVAL-05 | P2 | P2 | **abstained** | broke — stopped triaging an answerable ticket |
| EVAL-06 | P3 | P2 | P2 | unchanged — a target of the fix |
| EVAL-07 | P3 | P2 | P2 | unchanged — a target of the fix |
| EVAL-08 | P2 | P2 | **P3** | broke |
| EVAL-09 | P1 | P1 | **P2** | broke |
| EVAL-10 | P3 | P2 | P2 | unchanged — a target of the fix |

Category also fell 10/10 → 9/10 and held-firm 10/10 → 9/10. Abstention held at
5/5. The failed run is kept as `evals/live-results-failed-deadline-fix.json`.

Three things this actually teaches, none of them the thing being tested:

**The clause that did the damage was the confident one.** "Reserve P1 for work
that has stopped, not work that is slow, degraded, or failing part of the time"
reads as an obvious clarification of a vague definition. It demoted EVAL-09 — a
nightly load that had halted with every dashboard in the business stale, which
is the most clear-cut P1 in the set. The model matched "degraded" and stopped
reading.

**The counterweight did nothing to its targets.** EVAL-06, 07 and 10 escalated
identically before and after. The part of the edit aimed at the measured bias
had no measurable effect; the part added for tidiness caused all the harm.

**Two changes were bundled into one "single" edit**, against the discipline
written into this document a few hours earlier. The damage is still mostly
attributable because the failures cluster on the P1/P2 boundary, but that is
luck. Had they been spread, the run would have cost $0.04 and settled nothing.

A fourth observation with no explanation: EVAL-05 began abstaining on a ticket
it had previously triaged correctly, though nothing in the edit concerned
abstention. Prompt edits are not local, and a metric that only watches the thing
being changed will not notice.

### Correctness

**Ground truth was under-labelled.** Seven of ten eval cases listed only the KB
article as relevant when the matching past incident is equally useful to a
triager. Fixing it moved recall@3 from 40% to 90% — a suspicious-looking jump. It
is a labelling fix rather than a loosened metric because the labelling was
already inconsistent: two cases had both documents before anything was run. One
case deliberately keeps its single label, because the similar-sounding incident
is genuinely a different fault.

**A regression floor was set above measured performance.** The category floor was
70%, written before anything was measured; the baseline scores 60%. CI would have
been permanently red. → Floors now sit ~10 points below measured. A floor above
what a system has ever achieved is an aspiration, and aspirations belong in an
ADR, not an assert.

**`effort` is rejected by Haiku 4.5.** Not ignored — a 400. Choosing the cheaper
tier would have made the first live call fail with a parameter error that looks
nothing like its cause. → Set only on tiers that accept it, verified across four
model IDs.

**Two pinned SHAs were wrong from memory.** `actions/setup-python` differed by one
character from the real v6.0.0. → Both resolved with `git ls-remote` and
`docker images --digests`. Memory is not a pin; the same lesson as the gitleaks
digest.

**Nothing read `.env`.** `.env.example` told the user to copy it; the SDK reads
the environment. Following the README exactly produced an auth error with a
correctly-set key. → Ten-line loader in `core/triage.py`; real environment
variables still win over the file.

**The SDK's missing-key error is a `TypeError` from inside its header builder**,
which reads like a bug in this code. → Check first, print the actual fix, never
echo the value.

### Found by the independent design review

The landing page was reviewed by a separate agent, deliberately outside the
thread that built it, against the direction contract, DESIGN.md and PRODUCT.md.
It found defects the build thread had missed, which is the argument for running
the review somewhere the builder is not.

**The page and the document it linked to published different numbers for the
same call.** The page carried EVAL-03's figures (1,254 / 263 / $0.0026); the ADR
and PRODUCT.md still carried EVAL-02's (1,126 / 243 / $0.0023), because the ADR
was written before the fixture was re-recorded. The page links to the ADR *as its
proof*, so the one reader who checks was the one who would find the
contradiction. On a page whose thesis is "measured, not claimed", this was the
most serious defect in the build. → All three files reconciled to the fixture,
which is the single source of truth.

**Recorded strings had been silently rewritten.** Under a stamp reading
"Recorded", retrieval titles were paraphrased, the model's opening word was
dropped from its reasoning, and the drafted reply lost its final sentence with no
ellipsis. → Every string is now rendered verbatim from `fixtures/example.json`,
with truncation shown rather than tidied, and a note explaining that the
retriever stores the first 80 characters of an incident.

**That fix had no guard, and this document claimed it did.** The line here used
to end "a script asserts the page text still matches the fixture". No such
script existed, so the defect the review caught by hand could return the way it
arrived. → `scripts/check_page.py`, now in CI, comparing the page against the
fixture and against `evals.run`'s live output rather than a pasted copy. Proven
in both directions: a one-word paraphrase of the recorded reply fails it, and so
does nudging a published score by two points.

**DESIGN.md did not describe what shipped** — wrong hex for `--urgent`, a token
used throughout the build and absent from the table, stamps documented as
overprinting when every one sat inline, and a masthead serial (`FORM 001 · REV
2026-08`) that identified nothing, which the document's own rule forbids. → The
document now matches the build, and the invented serial was replaced with a real
field, `PREPARED BY / DAVID ZURITA`.

**"Every number on this page comes out of one command" was false.** Token counts
and cost come from the fixture, and the dollar figure additionally needs a price
list that is not in the repository. → Narrowed to the section it is true of, with
the cost note carrying its source.

**White on hazard amber measured 3.79:1**, below the 4.5 floor. → Black on amber,
which is both the authentic hazard rendering and 8.54:1.

**The page failed its own persuade job at the top.** A recruiter arriving from
LinkedIn met a wordmark and an invented form number; David's name first appeared
three screens down. → Named in the masthead, with the contact link promoted to
signal red as the one visually distinct action above the fold.

**The h1 was the only unverifiable claim on the page** — "Most AI demos claim" is
an assertion about other people's work carrying no number, opening a page that
argues assertions without numbers are worthless. → Replaced with the measured
result: *"Nine of ten tickets retrieve the right past incident. The tenth is on
this page too."*

**The build used two of the form's devices and stopped.** Perforation and
tear-off were delivered; overprint, tally boxes, the punched hole and a
carbon-copy treatment were not. → All four added. The tally boxes matter most:
ten ruled squares with nine ticked lets a non-technical reader see "nine out of
ten" without parsing a percentage.

**Cadence tells no mechanical detector catches**: comma-lists-of-three in nearly
every paragraph, four negation-antithesis constructions, every section closing on
the same grey qualifier, and claims restated instead of proved. → Rewritten.

### Process and presentation

**The plan publicly critiqued the author's own CV.** Lines like "nothing on the
CV proves architecture design" were fine as private notes and actively harmful on
the public repository built to sell him. → Reframed as forward-looking
positioning; engineering content untouched.

**Two stated plans were wrong and were corrected rather than shipped around.**
Hand-rolled `urllib` (Anthropic's guidance is the official SDK where one exists)
and "cheapest model that passes evals" (a cost downgrade is the operator's
decision, not the assistant's). Both corrections are recorded in `docs/PLAN.md`,
not just in commit messages.

**`PLAN.md` sat outside the repository.** The README's `../PLAN.md` link would
have broken on publication. → Moved to `docs/PLAN.md`.

**Fourteen em-dashes on the landing page.** The mechanical design detector caught
the AI cadence tell. → Ten passages rewritten with ordinary punctuation.

**A `git reset --hard` destroyed uncommitted work.** Recovered because the
valuable artifacts were untracked and untouched, but the lesson stands: `--hard`
plus `checkout -- .` discards work in progress.

---

## 6. Open items

- [x] ~~The recorded fixture predates the abstention schema and no longer
      validates.~~ **Re-recorded 2026-08-13** against the current schema. It was
      deliberately left broken rather than hand-edited — patching a recorded
      artifact under a "Recorded" stamp is already a finding in §5, and a CI
      assertion would have left the build red until someone with a key could fix
      it. The page, ADR-001, `PRODUCT.md` and the metrics above were reconciled
      to the new call in the same commit; `scripts/check_page.py` caught the
      drift, which is the first time that guard has earned its place.
- [x] ~~Run `python -m evals.live` and publish what it says.~~ **Done
      2026-08-13.** Abstention landed at 5 of 5 with no false abstentions;
      category at 10 of 10; priority at 6 of 10, below the baseline. All of it
      is on the landing page, including the loss.
- [x] ~~Fix the one-directional deadline rule.~~ **Tried 2026-08-13 and it made
      things worse — reverted.** See §5, "The obvious fix for the escalation
      bias". Priority went 6/10 → 4/10. Do not retry this wording.
- [ ] **Priority over-escalation is still unfixed. The dev set now exists; the
      tuning has not been done.** Three cases (EVAL-06, 07, 10) escalate under
      both prompts tried so far. `evals/dev-priority.json` and
      `python -m evals.live --dev` are the tools — iterate there until the
      per-guard breakdown is clean in all three classes, *then* spend one golden
      run. Two rules learned the expensive way: change one thing per run, and
      treat a regression in a guard class you were not aiming at as a stop
      signal rather than a rounding error.
- [x] ~~The dev set has never been run against the live model.~~ **Baselined
      2026-08-13**, and it immediately found the abstention defect above rather
      than the priority baseline it was written for.
- [x] ~~Candidate 1: tighten the abstention bar to the triage decision.~~
      **Applied and kept 2026-08-13.** Held firm went 4/9 → 6/9, category
      4/9 → 6/9, priority 1/9 → 2/9, abstention on the ambiguous case unchanged
      at 1/1. Nothing regressed, so it stays — but it is an improvement, not a
      fix. See §5.
- [ ] **Three cases still refuse. Candidate 2 is the next thing to try:** cut
      the coupling to retrieval. The line *"a confident-looking match is not
      evidence the ticket is triageable"* appears to have generalised into its
      converse. State the converse explicitly — *"and an unrelated match is not
      evidence that it is untriageable; a ticket about a system the knowledge
      base has never seen is still triageable on its own text."* One change,
      re-run `--dev`, watch all three guard classes.
- [ ] **The category taxonomy has no slot for network connectivity, and
      abstention is absorbing the gap.** Found by DEV-08, which asked the tool
      to categorise a VPN connection failure: access-identity is authentication,
      integration is systems talking to each other, performance is slowness.
      None of them fit, and `insufficient-information` is the only other value
      the enum offers — so the schema conflates *this ticket is unclear* with
      *this taxonomy has no slot for it*, and a reader of the output cannot tell
      which happened. Two decisions, both for David: whether the corpus needs a
      sixth category, and whether "no category fits" deserves its own value
      rather than borrowing abstention's. The dev case was rewritten to stay
      inside the taxonomy, because a case with no correct answer tests nothing.
- [ ] **Consider whether over-escalation deserves its own metric.** Averaged
      into a single accuracy figure the bias is invisible — six of ten reads as
      noise until you look at which way each miss went. A signed mean error, or
      simply "escalated / de-escalated" counts, would make a regression visible
      that accuracy alone would hide. `scripts/check_page.py` already asserts
      the direction, so the data is there.
- [ ] Abstention has no regression floor, deliberately — the measured baseline
      is 0% and a floor of zero asserts nothing. Add one once there is a model
      score to protect.
- [ ] Confirm the project name. The repository is `triage-lab-showcase`; the
      docs say `triage-lab`. Cosmetic, cheapest to settle before anything links
      to it.
- [ ] `dzuritaa/triage-lab` (the earlier empty private repository) can be deleted.
- [ ] Deploy `web/index.html` to a real URL. Cloudflare Pages per the plan, which
      also supplies the `_headers` file for the CSP promised in the threat model.
- [ ] Alerts on the API account fire at $5 and $8 against a $5 balance, so they
      will never fire. Lower to ~$2/$4 for warning rather than notification.
- [ ] **Nothing checks that the model keeps the prompt's no-timing-promises
      rule.** This item used to say the fixture promised "before 9am tomorrow";
      it does not, and has not since the fixture was re-recorded from EVAL-02 to
      EVAL-03 — that phrase is in EVAL-02's *ticket*, not in any reply. The note
      outlived the thing it described, which is its own lesson. The rule is
      still unverified, and a keyword check for "tomorrow" or "within the hour"
      would fire on the current reply's legitimate "prioritize the log review
      now". Needs a real assertion or an honest deletion, not a regex.

## 7. Audit findings still open

`docs/PLAN.md` §8 carries the full table with verification conditions. Four are
closed; the rest map to later phases:

| Finding | Phase |
|---|---|
| Workers KV cannot enforce a hard cost cap (use a Durable Object) | 3 |
| Fork PRs cannot run live-model evals (split trusted workflows) | 2 |
| Response security headers need a tested `_headers` file | 4 |
| CV needs a quantified Selected AI Project section | 6 |
| Frontend accessibility/performance audit with recorded results | 6 |

---

## 8. If you change one thing, know this

Every number on the landing page is reproducible from the repository with one
command, and that property is the whole argument. Adding a claim the code cannot
produce does more damage than shipping nothing, because the repository is public
and a reader can check.
