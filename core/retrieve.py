"""BM25 retrieval over the incident and knowledge-base corpus.

Standard library only, on purpose. At this corpus size (25 documents) BM25 is a
few dozen lines and needs no API, no key, no second vendor and no cost. Anthropic
ships no embeddings endpoint, so "just use vectors" means adding a whole
dependency chain on day one. ADR-001 records the decision and the eval numbers
that back it.

Upgrade path: if recall@3 stops improving as the corpus grows past a few thousand
documents, swap this for embeddings behind the same search() signature.

    python -m core.retrieve                 # self-check
    python -m core.retrieve "some query"    # ad-hoc search
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Standard BM25 parameters. k1 controls term-frequency saturation, b controls
# length normalisation. These are the usual defaults; the eval is what tells us
# whether they need touching.
K1 = 1.5
B = 0.75

# The score below which a top hit is treated as "nothing here really matches".
# This value is not new and was not chosen for the abstention eval that now
# consumes it: it was written for the self-check's off-topic assertion, where a
# question about annual leave had to not return a confident match. Reusing a
# threshold that predates the measurement keeps it from being quietly tuned
# until the numbers look good. See evals/run.py for what it scores.
LOW_SCORE = 3.0

# Deliberately short. An aggressive stopword list removes words that carry real
# signal in support text ("cannot", "not", "after", "before").
STOPWORDS = frozenset("""
a an the and or of to in on at for with is are was were be been being
it its this that these those i we you they he she my our your their
have has had do does did will would can could should there here as by
from if then than so but
""".split())

_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords and bare digits.

    No stemming: "logging"/"logged" stay distinct. Adding a stemmer is a real
    change to recall, so it belongs behind an eval rather than a hunch.
    """
    return [
        t for t in _WORD.findall(text.lower())
        if t not in STOPWORDS and not t.isdigit() and len(t) > 1
    ]


def load_corpus() -> list[dict]:
    """Incidents and KB articles as one searchable corpus.

    A real service desk searches both together, and the caller wants "things
    that help with this ticket" rather than a document class.
    """
    corpus: list[dict] = []

    for inc in json.loads((DATA / "incidents.json").read_text(encoding="utf-8")):
        corpus.append({
            "id": inc["id"],
            "type": "incident",
            "title": inc["raw"][:80].strip(),
            "category": inc["category"],
            # Carried so the eval can score a nearest-neighbour priority baseline.
            # KB articles have none: an article describes a fault class, not one
            # incident's business impact, and impact is what sets priority.
            "priority": inc["priority"],
            # Index symptom, fix and cause together: a new ticket describes the
            # symptom, but the value of a past incident is mostly in the other two.
            "text": " ".join((inc["raw"], inc["resolution"], inc["root_cause"])),
        })

    for art in json.loads((DATA / "kb.json").read_text(encoding="utf-8")):
        corpus.append({
            "id": art["id"],
            "type": "kb",
            "title": art["title"],
            "category": art["category"],
            "priority": None,
            "text": " ".join((art["title"], art["body"])),
        })

    return corpus


class Bm25:
    """BM25 Okapi over an in-memory corpus."""

    def __init__(self, docs: list[dict]) -> None:
        if not docs:
            raise ValueError("empty corpus")
        self.docs = docs
        self.tokens = [tokenize(d["text"]) for d in docs]
        self.lengths = [len(t) for t in self.tokens]
        # Guard: a corpus of empty documents would divide by zero below.
        self.avg_len = (sum(self.lengths) / len(self.lengths)) or 1.0

        self.freqs: list[dict[str, int]] = []
        doc_freq: dict[str, int] = {}
        for toks in self.tokens:
            counts: dict[str, int] = {}
            for t in toks:
                counts[t] = counts.get(t, 0) + 1
            self.freqs.append(counts)
            for term in counts:
                doc_freq[term] = doc_freq.get(term, 0) + 1

        n = len(docs)
        # Lucene-style IDF: the +1 inside log keeps this positive even for a term
        # present in every document, which the textbook form makes negative.
        self.idf = {
            term: math.log(1 + (n - df + 0.5) / (df + 0.5))
            for term, df in doc_freq.items()
        }

    def search(self, query: str, k: int = 3) -> list[dict]:
        """Top-k documents for a query, each with its score. Ties broken by id."""
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        scored: list[tuple[float, str, dict]] = []
        for i, doc in enumerate(self.docs):
            freqs, dl = self.freqs[i], self.lengths[i]
            score = 0.0
            for term in q_tokens:
                f = freqs.get(term)
                if not f:
                    continue
                denom = f + K1 * (1 - B + B * dl / self.avg_len)
                score += self.idf[term] * (f * (K1 + 1)) / denom
            if score > 0:
                scored.append((score, doc["id"], doc))

        scored.sort(key=lambda s: (-s[0], s[1]))
        return [{**doc, "score": round(score, 4)} for score, _, doc in scored[:k]]


def _self_check() -> None:
    """Fails loudly if retrieval stops working. No framework, no fixtures."""
    corpus = load_corpus()
    assert len(corpus) == 25, f"expected 25 docs, got {len(corpus)}"
    bm25 = Bm25(corpus)

    # Empty and stopword-only queries must return nothing, not crash or return
    # an arbitrary document.
    assert bm25.search("") == []
    assert bm25.search("the and of") == []

    # Each case is a paraphrase, not a copy: no phrase here appears verbatim in
    # the document it should find. Matching on copied text would prove nothing.
    #
    # Each topic has two genuinely useful documents — the past incident and the
    # KB article — so a hit on either counts. An earlier version of this check
    # demanded one specific id and "failed" while returning the other document,
    # which was the test being wrong rather than retrieval.
    cases = [
        ("keep getting sent back to the login screen after changing my password", {"KB-201", "INC-1001"}),
        ("file never arrived at the external provider overnight", {"KB-204", "INC-1003"}),
        ("same lead created three times from the website", {"KB-205", "INC-1004"}),
        ("report fails after a few minutes but small ones work", {"KB-207", "INC-1005"}),
        ("one office is slow, everyone else is fine", {"KB-209", "INC-1006"}),
        ("supplier names differ only by capitals and Ltd", {"KB-210", "INC-1007"}),
        ("pdf total differs from the screen by one penny", {"KB-211", "INC-1008"}),
        ("scheduled email stopped arriving for one person only", {"KB-213", "INC-1010"}),
    ]
    misses, top1 = [], 0
    for query, acceptable in cases:
        hits = [h["id"] for h in bm25.search(query, k=3)]
        if not acceptable & set(hits):
            misses.append(f"  none of {sorted(acceptable)} in {hits} for {query!r}")
        if hits and hits[0] in acceptable:
            top1 += 1
    assert not misses, "recall@3 failures:\n" + "\n".join(misses)

    # A query about something the corpus does not cover should not confidently
    # return a top hit with a high score.
    off_topic = bm25.search("how do I book annual leave", k=1)
    assert not off_topic or off_topic[0]["score"] < LOW_SCORE, (
        f"off-topic query scored too high: {off_topic}"
    )

    print(
        f"self-check ok: {len(corpus)} docs, "
        f"recall@3 {len(cases)}/{len(cases)}, top-1 {top1}/{len(cases)}"
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        index = Bm25(load_corpus())
        for hit in index.search(" ".join(sys.argv[1:]), k=5):
            print(f"{hit['score']:7.3f}  {hit['id']:<9} {hit['type']:<9} {hit['title'][:60]}")
    else:
        _self_check()
