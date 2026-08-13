"""Live evaluation: score the model against the baselines built to be beaten.

Everything in evals/run.py is deterministic and measures what the *retriever*
can do alone. Nothing has ever measured the model. This does, and it is a
separate file for one load-bearing reason: `evals/run.py` must stay
standard-library and offline so CI installs nothing and a fork pull request
needs no secret. This module calls the API and needs a key, so it can never run
there.

    python -m evals.live               # all 15 cases (~15 calls)
    python -m evals.live --ambiguous   # the 5 ambiguous cases only

Costs real money. At Haiku 4.5 rates one full run is a few cents; the exact
figure is printed at the end from the token counts, not estimated.

Results are written to evals/live-results.json so the numbers are inspectable
and citable rather than living in a console scrollback.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from core.retrieve import Bm25, load_corpus
from core.triage import ABSTAIN, MODEL, triage
from evals.run import GOLDEN, evaluate

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals" / "live-results.json"

# Haiku 4.5 list pricing, dollars per million tokens. Not in the repository
# anywhere else, and not derivable from it - the cost figure is the one number
# here that needs an outside source, so it is named rather than buried.
PRICE_IN, PRICE_OUT = 1.0, 5.0


def score(cases: list[dict], index: Bm25) -> tuple[list[dict], list[str]]:
    """Run the model over cases. Returns per-case rows and a failure list."""
    rows, failures = [], []

    for case in cases:
        try:
            result = triage(case["raw"], index=index)
        except RuntimeError as exc:
            # A schema or half-abstention rejection is a real result, not a
            # crash: it means the model produced something the contract refuses.
            failures.append(f"  {case['id']}: rejected by validation - {exc}")
            rows.append({"id": case["id"], "rejected": str(exc)})
            continue

        want_abstain = case["expected_category"] == ABSTAIN
        did_abstain = result["category"] == ABSTAIN
        row = {
            "id": case["id"],
            "expected_category": case["expected_category"],
            "got_category": result["category"],
            "expected_priority": case["expected_priority"],
            "got_priority": result["priority"],
            "abstained": did_abstain,
            "should_abstain": want_abstain,
            "questions": result.get("clarifying_questions", []),
            "tokens": result["_meta"],
        }
        rows.append(row)

        if want_abstain and not did_abstain:
            failures.append(
                f"  {case['id']}: guessed {result['category']}/{result['priority']} "
                f"on a ticket with nothing to go on"
            )
        elif did_abstain and not want_abstain:
            failures.append(
                f"  {case['id']}: abstained on an answerable ticket "
                f"(expected {case['expected_category']})"
            )
        elif not want_abstain:
            if result["category"] != case["expected_category"]:
                failures.append(
                    f"  {case['id']} category: expected {case['expected_category']}, "
                    f"got {result['category']}"
                )
            if result["priority"] != case["expected_priority"]:
                failures.append(
                    f"  {case['id']} priority: expected {case['expected_priority']}, "
                    f"got {result['priority']}"
                )

    return rows, failures


def main(argv: list[str]) -> int:
    all_cases = json.loads(GOLDEN.read_text(encoding="utf-8"))
    if "--ambiguous" in argv:
        all_cases = [c for c in all_cases if c["expected_category"] == ABSTAIN]

    print(f"\nRunning {len(all_cases)} live calls against {MODEL}. This costs money.\n")

    index = Bm25(load_corpus())
    rows, failures = score(all_cases, index)

    scored = [r for r in rows if "rejected" not in r]
    ambiguous = [r for r in scored if r["should_abstain"]]
    answerable = [r for r in scored if not r["should_abstain"]]

    base = evaluate()  # the deterministic baselines, for the comparison column

    print(f"triage-lab LIVE evals - {MODEL}, {date.today().isoformat()}\n")
    print(f"  {'metric':<26}{'model':>8}{'baseline':>11}   {'baseline is':<24}")
    print(f"  {'-' * 26}{'-' * 8}{'-' * 11}   {'-' * 24}")

    if answerable:
        cat = sum(r["got_category"] == r["expected_category"] for r in answerable)
        pri = sum(r["got_priority"] == r["expected_priority"] for r in answerable)
        held = sum(not r["abstained"] for r in answerable)
        n = len(answerable)
        print(f"  {'category accuracy':<26}{cat / n:>7.0%}"
              f"{base['category_accuracy_1nn']:>11.0%}   nearest neighbour")
        print(f"  {'priority accuracy':<26}{pri / n:>7.0%}"
              f"{base['priority_accuracy_1nn']:>11.0%}   nearest neighbour")
        print(f"  {'held firm when it should':<26}{held / n:>7.0%}"
              f"{base['no_abstention_on_answerable']:>11.0%}   score threshold")

    if ambiguous:
        caught = sum(r["abstained"] for r in ambiguous)
        n_amb = len(ambiguous)
        print(f"  {'abstained when it should':<26}{caught / n_amb:>7.0%}"
              f"{base['abstention_oracle']:>11.0%}   best possible threshold")

    if failures:
        print("\n  cases below expectation:")
        print("\n".join(failures))

    tok_in = sum(r["tokens"]["input_tokens"] for r in scored)
    tok_out = sum(r["tokens"]["output_tokens"] for r in scored)
    cost = tok_in / 1e6 * PRICE_IN + tok_out / 1e6 * PRICE_OUT
    print(f"\n  {len(scored)} calls, {tok_in:,} in / {tok_out:,} out, "
          f"${cost:.4f} at list pricing\n")

    RESULTS.write_text(
        json.dumps(
            {
                "model": MODEL,
                "date": date.today().isoformat(),
                "n_cases": len(scored),
                "input_tokens": tok_in,
                "output_tokens": tok_out,
                "cost_usd": round(cost, 6),
                "cases": rows,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"  written to {RESULTS.relative_to(ROOT)}\n")

    # Exit non-zero on any failure so this can gate a trusted workflow later,
    # but there are deliberately no floors yet: nothing has been measured, and a
    # floor set before the first measurement is the mistake evals/run.py already
    # records.
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
