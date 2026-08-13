# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary: hiring managers and technical recruiters** screening David Zurita for
remote engineering, support-engineering or AI-tooling roles, mostly on US hours
from Quito. They arrive from a CV, a LinkedIn message or a GitHub link, skim for
well under a minute, and are often not deeply technical themselves. Success is
that they make contact.

**Secondary: prospective consulting clients** — companies wanting AI built into
an existing support or operations function. Same page, lower on it; success is a
discovery conversation.

**Tertiary: engineers** who will actually read `evals/run.py` and the ADR. They
are not the audience the page is composed for, but nothing on it may insult
them, because they are the ones who can verify the claims.

## Product Purpose

triage-lab is an incident triage assistant for enterprise IT support: paste a
raw ticket, get a category, a priority with an SLA target, similar past
incidents, a drafted first reply and a root-cause direction.

Its real purpose is evidentiary. Twelve years of incident management, ITSM and
internal tooling sit behind corporate walls where no employer can read a line of
it. This rebuilds that experience in the open. The demo is the vehicle; the
published evaluation and the architecture decisions are the substance.

## Positioning

**Measured, not claimed.** The project publishes its own scorecard — including
the cases it gets wrong — against stated baselines. Almost every portfolio that
says "AI-powered" has no number attached to it and no way for a reader to check.
This one ships a golden set, a random baseline, regression floors in CI, and a
recorded failure.

The domain is the second half: enterprise incident triage from someone who ran a
service desk at ~200 incidents a month, not a generic chatbot demo.

## Operating Context

- A recruiter skims on a laptop, mid-shortlist, with other tabs open. A phone
  read is common from a LinkedIn message.
- The repository is public; the page and the code are read together, and a
  claim on the page that the code contradicts is worse than no claim.
- Everything must be viewable at zero cost and zero latency: the demo is a
  recorded fixture, not a live API call.

## Capabilities and Constraints

- One static HTML file. **No build step, no framework, no bundler.** Deployed on
  a free tier.
- Retrieval is BM25 over 25 documents, standard-library Python, no vector store.
- The recorded result comes from one real Claude Haiku 4.5 call: 1,254 input /
  263 output tokens, $0.0026 at list pricing.
- Measured evaluation on 10 held-out cases: retrieval recall@3 90% (random
  23%), recall@1 60% (random 8%), category accuracy 60% via nearest-neighbour
  (majority-class 20%), priority accuracy 70% (majority-class 40%).
- Priority's baseline is high because eight of the ten cases are P2 or P3. Say
  so wherever the number appears; a four-way label that behaves like a two-way
  one is not a hard target, and 70% is a bar to clear rather than a result.
- The tool can decline to classify. Five further held-out cases are ambiguous by
  design and their correct output is `insufficient-information` with questions
  back to the reporter. **The model's abstention rate is not measured yet** and
  must not be implied anywhere. What is measured is the baseline: retrieval
  abstains on 0 of 5, and the best any score threshold could achieve is 3 of 5
  even when chosen with the answers in hand.
- Abstention is all or nothing wherever it is shown. A category of
  `insufficient-information` carries no priority and no SLA, because a clock
  cannot start on a ticket nobody can act on yet.
- **All data is synthetic** and must be labelled as such wherever a visitor
  could mistake it for real. No employer, client or university data, ever.
- Live mode, the Cloudflare Worker, rate limiting and the budget cap are phase 3
  and do not exist yet. The page must not imply they do.

## Brand Commitments

- Name: David Zurita. Contact by email (dzuritaa@gmail.com), LinkedIn
  (linkedin.com/in/davidzuritaa) and GitHub (github.com/dzuritaa).
- Voice: plain and specific. No hype, no "revolutionise", no emoji headings.
  The project's credibility rests on restraint — overselling contradicts the
  thesis.
- Failures are shown, not hidden. The retrieval miss is a feature of the
  argument, not an embarrassment to bury.

## Evidence on Hand

- `fixtures/example.json` — a real recorded triage result for EVAL-03. Correct
  category and priority, and retrieval returned the right past incident at rank 1.
- `evals/golden.json`, `evals/run.py` — 10 held-out cases and the scorecard.
- `data/incidents.json`, `data/kb.json`, `data/README.md` — the synthetic
  corpus and its data dictionary, including its stated limitations.
- `docs/PLAN.md` — build plan, threat model, and the recorded audit findings.
- `.gitleaks.toml`, `scripts/canary-check.sh` — the secret-scanning gates and
  the test that proves they work.

**Absent, and not to be invented:** no testimonials, no named customers, no
competitor benchmarks, no production deployment, no user numbers, no uptime or
accuracy claims beyond the measured ones above.

## Product Principles

1. **Every number on the page is reproducible from the repository.** If a
   visitor cannot run the command that produces it, it does not go on the page.
2. **Show the miss.** The failure case is the strongest evidence of honest
   measurement and the clearest argument for what comes next.
3. **Synthetic data is labelled where it is shown**, not disclosed in a footer.
4. **Costs nothing to look at.** No API call on page load, ever.
5. **The page may never outrun the code.** No capability is implied that the
   repository does not contain today.

## Accessibility & Inclusion

Read on unknown hardware by people who did not choose to be there. Keyboard
reachable, legible at a phone width, and readable without colour as the sole
carrier of meaning. Content visible by default rather than revealed by motion.
