# Maintenance

## Updating pinned supply-chain references

Everything in CI is pinned to something immutable. Tags are mutable — whoever
controls a repo can repoint `v4` at new code — so a tag pin is not a pin.

### GitHub Actions (automated)

Dependabot proposes these weekly. It rewrites the SHA and the trailing version
comment together, so review the diff normally.

### gitleaks container (manual)

Dependabot does **not** cover this one: its docker ecosystem reads Dockerfiles
and compose files, not images invoked inside a workflow `run:` step. Pretending
otherwise would leave a stale scanner silently.

To update:

```bash
docker pull zricethezav/gitleaks:v8.29.0
docker images --digests zricethezav/gitleaks --format '{{.Tag}} {{.Digest}}'
```

Put the printed digest in `.github/workflows/ci.yml` and update the trailing
version comment to match. Then re-run the canary test below — a scanner upgrade
can change the ruleset.

## Facts that live outside this repository

Two things the code states as fact are owned by Anthropic, not by this project.
Nothing in CI can detect them going stale, because CI has no key and makes no
calls. They are checked by hand, on the cadence below.

### The model ID

`claude-haiku-4-5`, chosen deliberately (see the decisions table in
`docs/HANDOFF.md`) and overridable with `TRIAGE_MODEL`. Models are deprecated
and eventually retired; a retired ID returns 404 and every live path breaks at
once, while the whole offline suite stays green.

Appears in `core/triage.py` (the default), `docs/PLAN.md` (the decision), and
`fixtures/example.json` plus the recorded eval runs, where it is **history and
must not be edited** — those files record which model produced those numbers.

Check when a live command fails with a 404, and once when picking up the project
after a gap. Changing it means re-recording the fixture and re-running
`evals.live`, because every published number was produced by the old model.

### List pricing

$1 per million input tokens, $5 per million output. Every cost figure in the
project is derived from these two numbers and nothing in the repository can
verify them — this is the one class of published claim that needs an outside
source, which the landing page says in the sentence next to the figure.

| Where | What breaks if it drifts |
|---|---|
| `evals/live.py` — `PRICE_IN, PRICE_OUT` | Every future run reports the wrong cost |
| `web/index.html` | Two published figures: the per-ticket cost and the run cost |
| `docs/adr/001-…md` | The cost argument for BM25 over embeddings |
| `PRODUCT.md`, `docs/HANDOFF.md`, `docs/PLAN.md` | Prose figures |

If the rates change, update `evals/live.py` first, re-run
`python -m evals.live`, and take the printed figure to the other four. Do not
recalculate by hand — the runner prints it from the recorded token counts.

## What goes stale when the system prompt changes

Editing `SYSTEM` in `core/triage.py` invalidates more than it looks like. The
chain, in the order it must be repaired:

1. **`fixtures/example.json`** — recorded under the old prompt. Re-record with
   `python -m core.triage --record EVAL-03`. Input token count changes even when
   the wording of the result does not, because the prompt is part of the input.
2. **The landing page** — renders the fixture verbatim and publishes its token
   counts and cost. `python -m scripts.check_page` names every stale claim; it
   has caught this every time so far, which is the only reason the page and the
   ADR have not drifted apart a second time.
3. **`evals/live-results.json`** — the published measurement, produced by the
   old prompt. Re-run `python -m evals.live` (~$0.05) and reconcile the page,
   `docs/adr/001`, `PRODUCT.md` and `docs/HANDOFF.md` to it.

A prompt change is therefore about $0.05 and four files, not one line. That cost
is the reason for the discipline in the next section rather than an argument
against changing the prompt.

### Changing the prompt without wasting the money

Learned twice, expensively, on 2026-08-13 — both attempts are written up in
`docs/HANDOFF.md` §5.

- **One change per run.** The first attempt bundled two edits, and only luck in
  where the failures landed made the damage attributable at all.
- **Tune against `evals/dev-priority.json`, never against `golden.json`.** The
  golden set is the measurement; a prompt tuned until its cases pass is fitted
  to them and the number stops meaning anything.
- **Read all three guard classes, not the one being aimed at.** The failed
  attempt improved nothing it targeted and broke a class nobody was watching.
- **A regression in a class you were not aiming at is a stop signal**, not a
  rounding error.

## Recorded runs: what is committed and what is not

| File | Committed | Why |
|---|---|---|
| `evals/live-results.json` | yes | The measurement the landing page cites |
| `evals/live-results-failed-deadline-fix.json` | yes | Evidence for a published claim that a fix made things worse |
| `evals/dev-results-baseline.json` | yes | The before state for the abstention defect |
| `evals/dev-results.json` | **no**, gitignored | Regenerated on every tuning iteration; meaningless out of context |

The rule: a run that something published points at gets committed. A run made
while iterating does not. Recorded output is never hand-edited — if a number is
wrong, re-record it, because the alternative is a "Recorded" stamp on something
nobody recorded, which is already a finding in `docs/HANDOFF.md` §5.

## Verifying the secret gates still work

Both gates are tested with a deliberately fake, correctly-shaped key. Run this
after any change to `.gitleaks.toml`, the hook, or the scanner version.

```bash
sh scripts/canary-check.sh
```

It must report both gates catching the canary and a clean tree passing. A green
CI badge on an untested scanner means nothing — the default gitleaks ruleset
does **not** detect Anthropic keys, which is exactly how this project's custom
rule came to exist.
