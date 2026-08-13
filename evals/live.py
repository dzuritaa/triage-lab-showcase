"""Live evaluation: score the model against the baselines built to be beaten.

Everything in evals/run.py is deterministic and measures what the *retriever*
can do alone. Nothing has ever measured the model. This does, and it is a
separate file for one load-bearing reason: `evals/run.py` must stay
standard-library and offline so CI installs nothing and a fork pull request
needs no secret. This module calls the API and needs a key, so it can never run
there.

    python -m evals.live               # golden set, all 15 cases (~15 calls)
    python -m evals.live --ambiguous   # the 5 ambiguous cases only
    python -m evals.live --dev         # the priority development set, 10 cases

**Iterate against --dev. Measure with the golden set, once, at the end.**
`evals/golden.json` is held out, and a prompt tuned until its ten cases pass is
fitted to them — the number stops meaning anything, which is the leakage the
phase-2 plan warns about. `evals/dev-priority.json` exists to be overfitted:
tune there as much as you like, then spend one golden run to find out whether
anything real improved.

Costs real money. At Haiku 4.5 rates one full run is a few cents; the exact
figure is printed at the end from the token counts, not estimated.

Results are written to evals/live-results.json, or to
evals/dev-results.json for a development run — separate files, so a dev
iteration can never overwrite the measurement the landing page cites.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from core.retrieve import Bm25, load_corpus
from core.triage import ABSTAIN, MODEL, SCHEMA, SYSTEM, triage
from evals.run import GOLDEN, evaluate, text_hash

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals" / "live-results.json"
DEV = ROOT / "evals" / "dev-priority.json"
DEV_RESULTS = ROOT / "evals" / "dev-results.json"

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
    dev = "--dev" in argv
    source = DEV if dev else GOLDEN
    out = DEV_RESULTS if dev else RESULTS

    all_cases = json.loads(source.read_text(encoding="utf-8"))
    if "--ambiguous" in argv:
        all_cases = [c for c in all_cases if c["expected_category"] == ABSTAIN]

    print(f"\nRunning {len(all_cases)} live calls against {MODEL}. This costs money.")
    print(f"Source: {source.name}"
          + ("  (development set - tune freely, this is not the measurement)"
             if dev else "  (held out - this is the measurement)") + "\n")

    index = Bm25(load_corpus())
    rows, failures = score(all_cases, index)

    scored = [r for r in rows if "rejected" not in r]
    ambiguous = [r for r in scored if r["should_abstain"]]
    answerable = [r for r in scored if not r["should_abstain"]]

    # Baselines are computed over the golden set, so they are meaningless next
    # to a development run and are left out rather than printed misleadingly.
    base = None if dev else evaluate()

    label = "DEV run" if dev else "LIVE evals"
    print(f"triage-lab {label} - {MODEL}, {date.today().isoformat()}\n")
    head = f"  {'metric':<26}{'model':>8}"
    if base:
        head += f"{'baseline':>11}   {'baseline is':<24}"
    print(head)
    print(f"  {'-' * 26}{'-' * 8}" + (f"{'-' * 11}   {'-' * 24}" if base else ""))

    def row(name: str, hits: int, total: int, base_key: str = "", base_is: str = "") -> None:
        line = f"  {name:<26}{hits / total:>7.0%}"
        if base and base_key:
            line += f"{base[base_key]:>11.0%}   {base_is}"
        print(line)

    if answerable:
        n = len(answerable)
        row("category accuracy",
            sum(r["got_category"] == r["expected_category"] for r in answerable), n,
            "category_accuracy_1nn", "nearest neighbour")
        row("priority accuracy",
            sum(r["got_priority"] == r["expected_priority"] for r in answerable), n,
            "priority_accuracy_1nn", "nearest neighbour")
        row("held firm when it should", sum(not r["abstained"] for r in answerable), n,
            "no_abstention_on_answerable", "score threshold")

    if ambiguous:
        row("abstained when it should", sum(r["abstained"] for r in ambiguous),
            len(ambiguous), "abstention_oracle", "best possible threshold")

    # Development cases declare which failure mode they guard. Grouping by that
    # is the whole point of the set: a change that fixes over-escalation while
    # breaking the P1 floor shows up here as one class improving and another
    # regressing, which a single accuracy figure hides.
    guards = [c for c in all_cases if c.get("guards")]
    if guards:
        by_id = {r["id"]: r for r in scored}
        print("\n  by failure mode guarded:")
        for name in sorted({c["guards"] for c in guards}):
            members = [c for c in guards if c["guards"] == name]
            ok = sum(
                by_id[c["id"]]["got_priority"] == c["expected_priority"]
                and by_id[c["id"]]["got_category"] == c["expected_category"]
                for c in members if c["id"] in by_id
            )
            print(f"    {name:<22}{ok} of {len(members)}")

    if failures:
        print("\n  cases below expectation:")
        print("\n".join(failures))

    tok_in = sum(r["tokens"]["input_tokens"] for r in scored)
    tok_out = sum(r["tokens"]["output_tokens"] for r in scored)
    cost = tok_in / 1e6 * PRICE_IN + tok_out / 1e6 * PRICE_OUT
    print(f"\n  {len(scored)} calls, {tok_in:,} in / {tok_out:,} out, "
          f"${cost:.4f} at list pricing\n")

    out.write_text(
        json.dumps(
            {
                "model": MODEL,
                "source": source.name,
                # Provenance. A model score is only reproducible if the thing
                # that produced it still exists, so the run records what it ran
                # against and scripts/check_page.py refuses to publish numbers
                # whose prompt or schema has since moved. Recording without
                # checking is a receipt nobody reads; both halves are needed.
                "prompt_sha256": text_hash(SYSTEM),
                "schema_sha256": text_hash(
                    json.dumps(SCHEMA, sort_keys=True, ensure_ascii=False)
                ),
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
    print(f"  written to {out.relative_to(ROOT)}\n")

    # Exit non-zero on any failure so this can gate a trusted workflow later,
    # but there are deliberately no floors yet: nothing has been measured, and a
    # floor set before the first measurement is the mistake evals/run.py already
    # records.
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
