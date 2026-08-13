# ADR-001: BM25 over embeddings for retrieval

- **Status:** accepted
- **Date:** 2026-08-12
- **Reverses:** nothing
- **Reversed by:** nothing yet — see *What would change this decision*

## Context

Given an incoming support ticket, the assistant must surface similar past
incidents and knowledge base articles. The corpus is **25 documents**: 10
resolved incidents and 15 KB articles.

The reflex for "find similar documents" is embeddings and a vector database.
Three facts argued against reaching for it first:

1. **Anthropic ships no embeddings endpoint.** Using vectors means adding a
   second vendor, a second API key and a second bill on day one of a project
   whose deployment budget is zero.
2. **Twenty-five documents is not a retrieval problem yet.** A vector index over
   a corpus this size is infrastructure in search of a justification.
3. **Phase 1 required a baseline anyway.** If a baseline had to exist to make
   any retrieval number meaningful, the cheapest useful baseline might simply be
   good enough to ship.

## Decision

Retrieval is **BM25 Okapi**, implemented in about 150 lines of Python using only
the standard library (`core/retrieve.py`). No embeddings, no vector store, no
second vendor. The production deployment ships a flat index; local development
uses Postgres with pgvector behind the same `search()` signature, so the second
adapter exists and is exercised without being paid for.

## Evidence

Measured on 10 held-out cases that share no generation template with the corpus.
Reproduce with `python -m evals.run`.

| Metric | BM25 | Baseline | Baseline is |
|---|---|---|---|
| Retrieval recall@1 | **60%** | 8% | drawing 1 document at random |
| Retrieval recall@3 | **90%** | 23% | drawing 3 documents at random |
| Category accuracy | **60%** | 20% | always guessing the most common category |

The random baselines are computed exactly by combinatorics rather than sampled,
so there is no seed and no variance to argue about.

Category accuracy is nearest-neighbour: predict the category of the top
retrieved document. It is deliberately included as the number the language model
has to beat. A model that cannot outscore "return the category of the closest
document" is not earning its cost or its latency.

### Cost

One recorded live call on Claude Haiku 4.5 (`fixtures/example.json`): 1,254
input and 263 output tokens, **$0.0026 per ticket** at list pricing, or roughly
1,900 tickets per $5 of credit. Retrieval itself costs nothing and adds no
network latency, because it runs locally.

## The case against this decision

Recall@3 of 90% flatters BM25, and the honest reading is in the failure.

**EVAL-02** is a contractor who cannot open the finance application before an
audit starts tomorrow. The correct documents are `KB-202` and `INC-1002`, both
about **security group membership**. BM25 retrieved a branch-office WAN slowness
article, an SSO redirect-loop incident, and the change freeze calendar.

The ticket and the answer share almost no vocabulary. "Cannot open the finance
application" and "the logon script maps only the drives the account already has
rights to" are the same problem in two vocabularies, and a lexical matcher
cannot cross that gap by construction. No amount of tuning k1 and b fixes it.
This is precisely the gap embeddings exist to close.

Two further observations from the same case, recorded because they qualify the
result rather than support it:

- **Precision at ranks 2 and 3 is weak** across the board. Recall@3 counts a hit
  anywhere in three results; the second and third are frequently noise that
  happens to share common words.
- **The model produced the right answer anyway.** Given three irrelevant
  documents, it returned the correct category and priority, and a root-cause
  direction about group membership and provisioning — matching the content of
  the KB article it was never shown. On this case the assistant succeeded
  *despite* retrieval, not because of it.

That last point cuts both ways. It is evidence the system degrades gracefully,
and evidence that recall@3 overstates how much retrieval is currently
contributing.

## Consequences

**Accepted.** No vendor lock-in, no key to leak, no index to rebuild or keep
warm, no cold-start latency, no monthly bill. The whole retrieval path is
readable in one sitting and testable with no network. CI runs it with nothing
installed, so pull requests from forks — which cannot access secrets — still get
scored.

**Given up.** Any match that requires crossing a vocabulary gap. Synonyms,
paraphrase and domain jargon all fail. EVAL-02 is the standing proof.

**Deferred.** Phase 2 adds an embedding adapter behind the same interface and
scores both on the same golden set. The decision to adopt it will be a
measurement, not a preference — and if embeddings do not beat 90% recall@3 on a
corpus this size, that null result is worth publishing too.

## What would change this decision

Any one of these:

- The corpus passes roughly **5,000 documents**, where lexical scoring stops
  scaling and index maintenance stops being free.
- **Recall@1 starts mattering more than recall@3** — for example, if retrieval
  begins feeding an automated action rather than a human reading three results.
- The embedding adapter beats BM25 on the golden set by a margin that justifies
  a second vendor, a second key and a recurring cost.
- Vocabulary-gap misses like EVAL-02 turn out to be common in the expanded
  dataset rather than a single interesting case.

## Notes

The eval's regression floors sit about ten points below measured performance, so
ordinary variation does not break CI but a real drop does. An earlier version set
the category floor at 70% before anything had been measured — above what the
baseline has ever achieved — which would have left CI permanently red. A floor
above a system's demonstrated performance is an aspiration, and aspirations
belong in a document like this one, not in an assertion.
