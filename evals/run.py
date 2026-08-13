"""Offline evaluation. No API key, no network, fully deterministic.

Runs on every pull request, including from forks, because it never needs a
secret. Live-model scoring is a separate, trusted workflow (phase 2).

What this measures today:

  Retrieval    BM25 recall@1 and @3, against the exact expected recall of
               drawing k documents at random.
  Category     BM25 nearest-neighbour, against always guessing the most common
               category in the corpus.
  Priority     Same two. This one was expected to be the weak baseline —
               priority is business impact and the closest document matches on
               symptom — and it is not: 1nn scores 70%, above category's 60%.
               Two reasons, neither flattering to the metric. Four classes where
               eight of ten held-out cases are P2 or P3 is a narrow target, and
               a symptom that resembles a past incident often carries a similar
               impact. So 70% is the bar the model must clear, and clearing it
               is not the same as being good at priority. The case that
               separates them is the deadline rule, which only three cases test.

The nearest-neighbour scores matter more than they look: they are what the
language model has to beat in step 4. A model that cannot outscore "return the
category of the closest document" is not earning its cost or its latency.

    python -m evals.run
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from core.retrieve import Bm25, load_corpus

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "evals" / "golden.json"

# Regression floors: roughly ten points below measured performance, so ordinary
# variation does not break CI but a real drop does.
#
# These are floors, NOT targets. An earlier version set the category floor at
# 70% before anything had been measured; the baseline actually scores 60%, which
# would have left CI permanently red. A floor above anything the system has ever
# achieved is an aspiration, and aspirations belong in the ADR, not in an assert.
#
# Measured 2026-08-12: recall@1 60%, recall@3 90%, category 1nn 60%.
# Measured 2026-08-13: priority 1nn 70%.
THRESHOLDS = {
    "retrieval_recall_at_3": 0.80,
    "retrieval_recall_at_1": 0.50,
    "category_accuracy_1nn": 0.50,
    "priority_accuracy_1nn": 0.60,
}


def expected_random_recall(n_docs: int, n_relevant: int, k: int) -> float:
    """Exact probability that k documents drawn at random include >=1 relevant.

    Computed rather than sampled: no seed, no variance, no flaky CI.
    """
    if n_relevant <= 0 or k <= 0:
        return 0.0
    k = min(k, n_docs)
    misses = math.comb(n_docs - n_relevant, k) if n_docs - n_relevant >= k else 0
    return 1.0 - misses / math.comb(n_docs, k)


def majority_label(values: list[str]) -> str:
    """Most common value; ties broken alphabetically so the result is stable."""
    counts = Counter(values)
    return min(sorted(counts), key=lambda v: -counts[v])


def evaluate() -> dict:
    corpus = load_corpus()
    index = Bm25(corpus)
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))
    by_id = {d["id"]: d for d in corpus}

    # Baseline labels come from the corpus, never from the held-out set.
    incident_cats = [d["category"] for d in corpus if d["type"] == "incident"]
    majority_cat = majority_label(incident_cats)

    incident_prios = [d["priority"] for d in corpus if d["type"] == "incident"]
    majority_prio = majority_label(incident_prios)

    hits1 = hits3 = cat_1nn = cat_major = prio_1nn = prio_major = 0
    random3 = random1 = 0.0
    failures: list[str] = []

    for case in cases:
        relevant = set(case["relevant_docs"])
        missing = relevant - by_id.keys()
        assert not missing, f"{case['id']} references unknown docs: {missing}"

        top3 = [h["id"] for h in index.search(case["raw"], k=3)]
        got1 = bool(top3[:1]) and top3[0] in relevant
        got3 = bool(relevant & set(top3))
        hits1 += got1
        hits3 += got3
        if not got3:
            failures.append(
                f"  {case['id']} retrieval: wanted any of {sorted(relevant)}, got {top3}"
            )

        random3 += expected_random_recall(len(corpus), len(relevant), 3)
        random1 += expected_random_recall(len(corpus), len(relevant), 1)

        # Nearest-neighbour category: the category of the single closest document.
        predicted = by_id[top3[0]]["category"] if top3 else majority_cat
        if predicted == case["expected_category"]:
            cat_1nn += 1
        else:
            failures.append(
                f"  {case['id']} category:  expected {case['expected_category']}, "
                f"1nn said {predicted} (via {top3[0] if top3 else 'n/a'})"
            )
        cat_major += majority_cat == case["expected_category"]

        # Nearest-neighbour priority, falling back to the majority when the top
        # hit is a KB article. Not a fudge: a baseline that scored only the
        # cases where retrieval happened to land on an incident would be scored
        # on a different, easier set than every other metric here.
        top_prio = by_id[top3[0]]["priority"] if top3 else None
        predicted_prio = top_prio or majority_prio
        if predicted_prio == case["expected_priority"]:
            prio_1nn += 1
        else:
            failures.append(
                f"  {case['id']} priority:  expected {case['expected_priority']}, "
                f"1nn said {predicted_prio}"
                f"{'' if top_prio else f' (majority; top hit {top3[0]} is a KB article)'}"
            )
        prio_major += majority_prio == case["expected_priority"]

    n = len(cases)
    return {
        "n_cases": n,
        "n_docs": len(corpus),
        "retrieval_recall_at_1": hits1 / n,
        "retrieval_recall_at_3": hits3 / n,
        "retrieval_random_at_1": random1 / n,
        "retrieval_random_at_3": random3 / n,
        "category_accuracy_1nn": cat_1nn / n,
        "category_accuracy_majority": cat_major / n,
        "priority_accuracy_1nn": prio_1nn / n,
        "priority_accuracy_majority": prio_major / n,
        "majority_category": majority_cat,
        "majority_priority": majority_prio,
        "failures": failures,
    }


def main() -> int:
    r = evaluate()

    # ASCII only: this prints to a Windows console under cp1252 as often as to
    # a UTF-8 CI log, and mojibake in a scorecard undermines the point of it.
    print(f"\ntriage-lab offline evals - {r['n_cases']} held-out cases, "
          f"{r['n_docs']} corpus documents\n")
    rows = [
        ("retrieval recall@1", r["retrieval_recall_at_1"], r["retrieval_random_at_1"], "random"),
        ("retrieval recall@3", r["retrieval_recall_at_3"], r["retrieval_random_at_3"], "random"),
        ("category accuracy", r["category_accuracy_1nn"], r["category_accuracy_majority"],
         f"always '{r['majority_category']}'"),
        ("priority accuracy", r["priority_accuracy_1nn"], r["priority_accuracy_majority"],
         f"always '{r['majority_priority']}'"),
    ]
    print(f"  {'metric':<22}{'score':>8}{'baseline':>11}   {'baseline is':<22}")
    print(f"  {'-' * 22}{'-' * 8}{'-' * 11}   {'-' * 22}")
    for name, score, base, label in rows:
        print(f"  {name:<22}{score:>7.0%}{base:>11.0%}   {label}")

    if r["failures"]:
        print("\n  cases below expectation:")
        print("\n".join(r["failures"]))

    print()
    breached = [
        f"  {metric}: {r[metric]:.0%} is below the {floor:.0%} floor"
        for metric, floor in THRESHOLDS.items()
        if r[metric] < floor
    ]
    if breached:
        print("REGRESSION\n" + "\n".join(breached) + "\n")
        return 1

    print("all metrics at or above their regression floors\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
