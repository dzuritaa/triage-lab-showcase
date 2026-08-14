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

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from core.retrieve import LOW_SCORE, Bm25, load_corpus

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "evals" / "golden.json"

# Cases whose correct answer is "I cannot tell from this, ask the reporter".
# They are scored apart from the answerable ten, and every metric here states
# which of the two sets it ran on. Merging them would have quietly changed the
# meaning of recall@3 - retrieval recall over a case with no right answer is not
# a number - and silently moved every figure already published.
ABSTAIN = "insufficient-information"

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
    # Refusing a ticket the tool can actually triage is the more expensive
    # mistake, so the guard is on over-abstention, which measures 100%.
    #
    # There is deliberately no floor on abstention itself. It measures 0%, and a
    # floor of zero asserts nothing. The number is here to be beaten by the
    # model, and the floor goes in when there is a model score to protect -
    # writing one now would repeat the mistake this file already records, of a
    # threshold set above anything the system has ever achieved.
    "no_abstention_on_answerable": 0.90,
}


def text_hash(value: str) -> str:
    """Hash a prompt or a serialized schema.

    Lives in this module because both the recorder and the page checker need it
    and must agree byte for byte, while only the recorder may import
    `anthropic`. This file is standard library only, which is what lets CI
    verify provenance with nothing installed.

    Note for whoever merges the structured-triage branch: that branch puts the
    same function in `evals/validate_data.py`, which does not exist here. Keep
    one of them, not both.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def evaluate(source: Path = GOLDEN) -> dict:
    corpus = load_corpus()
    index = Bm25(corpus)
    all_cases = json.loads(source.read_text(encoding="utf-8"))
    cases = [c for c in all_cases if c["expected_category"] != ABSTAIN]
    ambiguous = [c for c in all_cases if c["expected_category"] == ABSTAIN]
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

    # Abstention. The deterministic system has exactly one signal for "nothing
    # here really matches": the top retrieval score. Whether that signal is
    # measuring what it appears to measure is the point of AMB-04.
    def top_score(raw: str) -> float:
        hit = index.search(raw, k=1)
        return hit[0]["score"] if hit else 0.0

    caught = 0
    for case in ambiguous:
        score = top_score(case["raw"])
        if score < LOW_SCORE:
            caught += 1
        else:
            failures.append(
                f"  {case['id']} abstention: did not abstain, top hit scored "
                f"{score:.2f} against a {LOW_SCORE:.1f} floor"
            )

    held = 0
    answerable_scores = []
    for case in cases:
        score = top_score(case["raw"])
        answerable_scores.append(score)
        if score >= LOW_SCORE:
            held += 1
        else:
            failures.append(
                f"  {case['id']} abstention: abstained on an answerable case"
            )

    # The obvious objection to a 0% result is that 3.0 is simply the wrong
    # threshold. So: the best score any threshold could possibly achieve on
    # these exact cases, chosen with full sight of the answers. It is an oracle,
    # not a score - the model gets no such advantage - and it exists to make the
    # baseline as strong as it can be before anything claims to beat it.
    #
    # The highest threshold that still keeps every answerable case is the lowest
    # score any of them achieved. Anything above that starts refusing tickets
    # the tool can actually triage, which is the more expensive failure.
    oracle_cut = min(answerable_scores) if answerable_scores else 0.0
    oracle_caught = sum(1 for c in ambiguous if top_score(c["raw"]) < oracle_cut)

    n = len(cases)
    n_amb = len(ambiguous)
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
        "n_ambiguous": n_amb,
        "abstention_on_ambiguous": caught / n_amb if n_amb else 0.0,
        "no_abstention_on_answerable": held / n,
        "abstention_oracle": oracle_caught / n_amb if n_amb else 0.0,
        "abstention_oracle_caught": oracle_caught,
        "abstention_oracle_cut": oracle_cut,
        # Published on the landing page, so computed here rather than read off a
        # console once and typed into HTML.
        "answerable_score_max": max(answerable_scores) if answerable_scores else 0.0,
        "ambiguous_score_max": max((top_score(c["raw"]) for c in ambiguous), default=0.0),
        "ambiguous_worst": max(ambiguous, key=lambda c: top_score(c["raw"]))["id"]
        if ambiguous else "",
        "majority_category": majority_cat,
        "majority_priority": majority_prio,
        "failures": failures,
    }


def summarize_live(case_rows: list[dict], baseline: dict) -> dict:
    """One definition of live metrics for the runner and page checker."""

    def summarize_attempts(attempts: list[dict]) -> dict:
        accepted = [a for a in attempts if "rejected" not in a]
        all_answerable = [a for a in attempts if not a["should_abstain"]]
        all_ambiguous = [a for a in attempts if a["should_abstain"]]
        answerable = [a for a in accepted if not a["should_abstain"]]
        ambiguous = [a for a in accepted if a["should_abstain"]]
        all_p1 = [a for a in all_answerable if a["expected_priority"] == "P1"]
        p1 = [a for a in answerable if a["expected_priority"] == "P1"]

        def metric(hits: int, total: int) -> dict:
            return {"hits": hits, "total": total, "rate": hits / total if total else 0.0}

        return {
            "category": metric(
                sum(a["got_category"] == a["expected_category"] for a in answerable),
                len(all_answerable),
            ),
            "priority": metric(
                sum(a["got_priority"] == a["expected_priority"] for a in answerable),
                len(all_answerable),
            ),
            "actionable_retention": metric(
                sum(not a["abstained"] for a in answerable), len(all_answerable)
            ),
            "correct_abstention": metric(
                sum(a["abstained"] for a in ambiguous), len(all_ambiguous)
            ),
            "p1_recall": metric(
                sum(a["got_priority"] == "P1" for a in p1), len(all_p1)
            ),
            "rejected": len(attempts) - len(accepted),
        }

    attempts = [
        {**attempt, "id": row["id"]}
        for row in case_rows
        for attempt in row["attempts"]
    ]
    run_numbers = sorted({a["run"] for a in attempts})
    per_run = {
        str(run): summarize_attempts([a for a in attempts if a["run"] == run])
        for run in run_numbers
    }
    aggregate = summarize_attempts(attempts)

    for metrics in per_run.values():
        metrics["passes_gate"] = (
            metrics["category"]["rate"] >= 0.90
            and metrics["priority"]["rate"] >= 0.80
            and metrics["correct_abstention"]["rate"] >= 0.90
            and metrics["actionable_retention"]["rate"] >= 0.95
            and metrics["p1_recall"]["hits"] == metrics["p1_recall"]["total"]
            and metrics["rejected"] == 0
            and metrics["category"]["rate"] > baseline["category_accuracy_1nn"]
            and metrics["priority"]["rate"] > baseline["priority_accuracy_1nn"]
        )

    unanimous = 0
    for row in case_rows:
        if all(
            "rejected" not in a
            and a["got_category"] == row["expected_category"]
            and a["got_priority"] == row["expected_priority"]
            for a in row["attempts"]
        ):
            unanimous += 1

    return {
        "baseline": {
            "category_accuracy_1nn": baseline["category_accuracy_1nn"],
            "priority_accuracy_1nn": baseline["priority_accuracy_1nn"],
        },
        "per_run": per_run,
        "aggregate": aggregate,
        "ranges": {
            name: {
                "min": min(metrics[name]["rate"] for metrics in per_run.values()),
                "max": max(metrics[name]["rate"] for metrics in per_run.values()),
            }
            for name in (
                "category",
                "priority",
                "correct_abstention",
                "actionable_retention",
                "p1_recall",
            )
        } if per_run else {},
        "unanimously_correct_cases": unanimous,
        "total_cases": len(case_rows),
        "passes_gate": bool(per_run) and all(m["passes_gate"] for m in per_run.values()),
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

    print(f"\n  abstention - {r['n_ambiguous']} ambiguous cases, "
          f"correct answer is 'ask the reporter'\n")
    print(f"  {'metric':<22}{'score':>8}{'baseline':>11}   {'baseline is':<22}")
    print(f"  {'-' * 22}{'-' * 8}{'-' * 11}   {'-' * 22}")
    print(f"  {'abstained when it should':<22}{r['abstention_on_ambiguous']:>7.0%}"
          f"{r['abstention_oracle']:>11.0%}   best possible threshold")
    print(f"  {'held firm when it should':<22}{r['no_abstention_on_answerable']:>7.0%}"
          f"{'-':>11}   {'':<22}")
    print(f"\n  Retrieval score cannot express doubt. It rises with the number of")
    print(f"  words in a ticket, so the emptiest case in the set (AMB-04, padding")
    print(f"  and no content) scores higher than every answerable case. No cut-off")
    print(f"  separates them: the best any threshold could do is "
          f"{r['abstention_oracle']:.0%}, and that is")
    print(f"  measured with sight of the answers. Abstention needs the model.")

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
