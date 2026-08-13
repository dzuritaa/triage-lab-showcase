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
| 2 — Dataset, core and eval expansion | started: priority scored, page guarded |
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

One recorded live call, Claude Haiku 4.5: 1,254 in / 263 out, **$0.0026**, about
1,900 tickets per $5. Reproduce the scores with `python -m evals.run`.

---

## 3. Repository map

```
triage-lab/
  data/            synthetic corpus + data dictionary (README.md is worth reading)
  core/retrieve.py BM25, standard library only, self-checking
  core/triage.py   the one module that calls the model (needs `anthropic`)
  evals/           golden.json (10 held-out cases) + run.py (scorecard, CI gate)
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
```

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
