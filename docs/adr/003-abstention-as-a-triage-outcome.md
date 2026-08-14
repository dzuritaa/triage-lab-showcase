# ADR-003: Abstention is a triage outcome, not a confidence score

- **Status:** accepted, with a known defect — see *The case against this decision*
- **Date:** 2026-08-13
- **Reverses:** nothing
- **Reversed by:** nothing yet

## Context

Real service desks receive tickets that cannot be triaged. `cannot enter site`
names no system and no symptom, and "site" could be a website or a building.
The useful response is a question back, not a category.

The tool could not give one. The response schema listed five categories and
required exactly one of them, so an empty ticket came back confidently
classified with a priority and an SLA target attached. **This was structural, not
a prompting problem** — no wording could have fixed it, which is probably why no
amount of prompt review had found it.

Three shapes were available:

1. A separate boolean field — `needs_clarification: true` alongside a category.
2. A nullable category — `"category": null` when the ticket is untriageable.
3. A sixth enum value.

## Decision

**A sixth enum value, `insufficient-information`, paired with priority
`unknown` and no SLA.**

It is a *triage outcome*, not a fault class. A service desk already models this
state — ServiceNow and Jira Service Management both ship a "needs info" status —
so it belongs in the same field as the other outcomes rather than in a parallel
flag that every consumer must remember to check.

Two supporting reasons, one principled and one practical:

- A nullable or branching schema may not be accepted by structured outputs.
  Extending an enum cannot break it. This repository **cannot test a request
  shape without spending someone's key on it**, so the shape least likely to
  fail was the correct default.
- No SLA is the point. Assigning P3 and a 24-hour clock to a ticket nobody can
  act on invents a commitment out of an unanswered question.

**Abstention is all-or-nothing**, enforced in `validate()` rather than in the
schema:

- category `insufficient-information` ⟺ priority `unknown`
- abstaining requires at least one clarifying question
- a triaged ticket must carry none — questions go in the drafted reply

A half-abstention — *"insufficient-information, P2, 8-hour SLA"* — is worse than
either honest answer, because a queue reads the priority and starts a clock.

## Evidence

Five ambiguous held-out cases whose correct answer is "ask the reporter".
Reproduce the baselines with `python -m evals.run`; the model figures come from
`evals/live-results.json`.

| | Model | Retrieval baseline |
|---|---|---|
| Abstained when it should | **5 of 5** | 0 of 5 |
| Held firm when it should | **10 of 10** | 10 of 10 |

Both directions are scored deliberately. A tool that abstains on everything
scores perfectly on the first row alone, so the second row is the one with a
regression floor.

**The deterministic system cannot do this at all**, and that is the clearest
cost justification for the model call anywhere in the project. BM25 score rises
with the number of words in a ticket, so it cannot express doubt: `AMB-04` is
four sentences of pleasantries naming no system and scores **28.42**, higher
than every answerable case, the best of which reaches 19.44. No cut-off
separates the two sets. The best any threshold could achieve is 3 of 5, and that
is measured with sight of the answers.

Asked about `cannot enter site`, the model asked which site — building location,
website domain, or application name. That is precisely the ambiguity the case
was written to test.

## The case against this decision

**The 10-of-10 retention figure was measured on friendly ground, and the feature
is not safe yet.**

Every answerable case in the golden set is a paraphrase of a corpus incident —
the property that makes it a fair *retrieval* test also means every one of them
lands on subject matter the knowledge base already covers. A second set written
later for an unrelated purpose broke that overlap by accident, and on its nine
answerable tickets about a checkout, an SSO loop and a purchase-order screen the
tool refused **five**.

Not because they were vague. `DEV-06` reads *"Customers cannot pay. The checkout
gets to the card step and then errors, every single time, for everyone. Nothing
is going through at all."* — system and symptom both named — and the tool asked
which payment gateway the shop uses. That is a diagnostic question, and this
tool does not diagnose.

The pattern was close to mechanical: where retrieval returned something
topically related the ticket was triaged, and where it returned an unrelated
document the ticket was refused. **Abstention tracks what the corpus happens to
cover rather than what the ticket says** — backwards for a service desk, where
an unfamiliar system is exactly when a triager wants help, and quietly worse
every time the business adds one.

Narrowing the bar to the triage decision improved retention from 4 of 9 to 6 of
9 with nothing regressing, so the change was kept. Three cases still refuse.

**A second, smaller flaw:** abstention is silently absorbing "no category fits".
A VPN connection failure matches none of the five categories — it is not
authentication, not systems talking to each other, not slowness — so the model
reached for `insufficient-information` because it is the only other value the
enum offers. Nothing in the output distinguishes *this ticket is unclear* from
*this taxonomy has no slot for it*, and a reader cannot tell which happened.

## Consequences

**Accepted.** The tool can decline, and it declines correctly on every
deliberately ambiguous case measured so far, without refusing anything in the
published golden set. The questions it asks are the right questions.

**Given up.** A guarantee that it will not refuse work it could do. That
guarantee currently holds only for tickets whose subject the knowledge base
already covers, and the page says so beside the number.

**Paid for.** The abstention rules lengthened the system prompt by roughly 470
input tokens, about half a tenth of a cent per ticket, charged on every ticket
whether it abstains or not.

## What would change this decision

- **Retention cannot be fixed.** If tickets about unfamiliar systems keep being
  refused after the retrieval coupling is addressed, the honest move is to drop
  the feature rather than publish it. A tool that refuses one ordinary ticket in
  three is worse than one that guesses, because the guess can be corrected and
  the refusal wastes a reporter's time.
- **"No category fits" earns its own value.** If the taxonomy gap turns out to
  be common in real tickets, that state should be separable from abstention
  rather than borrowing it.

## Notes

The eval that measures this was written before the capability existed, which is
the only reason the retention flaw was findable. Scoring only "did it abstain
when it should" would have reported 5 of 5 and missed everything in *The case
against*.
