# triage-lab

An incident triage assistant for enterprise support teams — with public
architecture decision records explaining every choice, and a CI eval suite
proving the prompts don't regress.

**Status:** the published vertical slice runs. A structured-priority candidate
is implemented on its feature branch but failed its three-pass development gate,
so the current page and evidence remain unchanged.

## What it does

Paste a raw support ticket, get back:

1. Category and priority, with a suggested SLA target
2. Similar past incidents, retrieved from a knowledge base
3. A drafted first response
4. A suggested root-cause direction

Or, when the ticket does not say enough to act on, the questions that would
make it triageable — and no category, priority or SLA. A ticket reading
`cannot enter site` names no system and no symptom, and a tool that answers it
with a confident category and a 24-hour clock has invented both.

Everything except the model call is deterministic and runs with no API key:

```bash
python -m core.retrieve            # BM25 retrieval self-check
python -m core.triage --check      # response validation rules
python -m evals.run                # the scorecard, with baselines
python -m evals.validate_data      # 30-case development/sealed-set invariants
python -m core.triage --fixture    # replay one real recorded result
```

## Why it exists

Twelve years of incident management, ITSM and internal tooling — all of it behind
corporate walls. This is that experience rebuilt in the open, where the code, the
reasoning and the evals can actually be read.

The interesting part is not the demo. It's [`docs/adr/`](docs/adr/) — six
decision records, each carrying the case against itself: why this deliberately
has **no vector database**, why the tool is allowed to **refuse a ticket** and
where that still fails, why a published number is worthless without the hash of
the prompt that produced it, and why the evaluation labels should not be
reviewed by the person who wrote them. The **threat model** is
[`docs/PLAN.md` §4](docs/PLAN.md#4-security), and the
[evaluation case study](docs/CASE_STUDY.md) carries the experiments that failed.

## No real data, ever

Every ticket and knowledge-base article in this repo is **synthetic**, generated
for the project. No client data, no employer data, no PII. That is a deliberate
constraint, not a limitation of the demo.

Requests to the live endpoint are **not logged**. Metrics only: count, latency,
token cost, status.

## Cost and abuse guardrails

The public demo runs on free tiers with a real API key behind it, so the primary
threat is cost exhaustion rather than data theft:

- Recorded fixtures are served by default — a page load costs nothing
- Live mode is opt-in per click, rate-limited per IP, and capped globally per day
- Past the cap the demo degrades back to fixtures instead of erroring
- An independent spend cap is set on the API key itself

Threat model: [`docs/PLAN.md` §4](docs/PLAN.md#4-security).

## Development

```bash
cp .env.example .env
```

Enable the secret-scanning pre-commit hook — **once per clone**:

```bash
git config core.hooksPath .githooks
```

CI scans too, but that is detection rather than prevention: a key that reaches
git history must be rotated even if the commit is never pushed. The hook is the
gate that actually saves you. It needs Docker; without it the hook warns and
defers to CI rather than blocking your work.

Verify both gates still catch a real-shaped key:

```bash
sh scripts/canary-check.sh
```

Evaluation case study: [`docs/CASE_STUDY.md`](docs/CASE_STUDY.md) ·
Decision records: [`docs/adr/`](docs/adr/) ·
Maintenance: [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md)

Near-term roadmap: stabilize structured priority on the development set, obtain
blind human review for the sealed 30-case set, then run its three-pass gate. The
landing page and accepted evidence change only after that gate passes.

## Licence

MIT
