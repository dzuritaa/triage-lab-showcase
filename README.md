# triage-lab

An incident triage assistant for enterprise support teams — with public
architecture decision records explaining every choice, and a CI eval suite
proving the prompts don't regress.

**Status:** phase 0 of 6. Skeleton and guardrails. Nothing to run yet.

## What it will do

Paste a raw support ticket, get back:

1. Category and priority, with a suggested SLA target
2. Similar past incidents, retrieved from a knowledge base
3. A drafted first response
4. A suggested root-cause direction

## Why it exists

Twelve years of incident management, ITSM and internal tooling — all of it behind
corporate walls. This is that experience rebuilt in the open, where the code, the
reasoning and the evals can actually be read.

The interesting part is not the demo. It's `docs/` — the decision records,
including why this deliberately has **no vector database** and what its
**threat model** is.

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

Full threat model: [`docs/PLAN.md` §4](docs/PLAN.md#4-security). It graduates into a
standalone ADR-006 in phase 5.

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

Build plan and phases: [`docs/PLAN.md`](docs/PLAN.md) ·
Supply-chain updates: [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md)

## Licence

MIT
