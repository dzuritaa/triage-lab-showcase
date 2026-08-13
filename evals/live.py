"""Paid model evaluation with explicit development and sealed modes.

Development is intentionally repeatable and disposable::

    python -m evals.live --dev
    python -m evals.live --dev --runs 3

The sealed run requires an approved review receipt whose dataset hash matches::

    python -m evals.live --sealed

A failed sealed run never overwrites the published live-results.json.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import anthropic

from core.retrieve import Bm25, load_corpus
from core.triage import MODEL, SCHEMA, SYSTEM, triage
from evals.run import evaluate, summarize_live
from evals.validate_data import DEV, REVIEW, SEALED, review_is_approved, sha256, validate_dataset

ROOT = Path(__file__).resolve().parent.parent
PUBLISHED = ROOT / "evals" / "live-results.json"
DEV_RESULTS = ROOT / "evals" / "dev-results.json"
FAILED_SEALED = ROOT / "evals" / "sealed-results.failed.json"
PRICE_IN, PRICE_OUT = 1.0, 5.0


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_runs(argv: list[str], default: int) -> int:
    if "--runs" not in argv:
        return default
    pos = argv.index("--runs")
    if pos + 1 >= len(argv):
        raise SystemExit("--runs needs a positive integer")
    try:
        runs = int(argv[pos + 1])
    except ValueError as exc:
        raise SystemExit("--runs needs a positive integer") from exc
    if runs < 1:
        raise SystemExit("--runs needs a positive integer")
    return runs


def run_pass(cases: list[dict], index: Bm25, run: int) -> list[dict]:
    attempts = []
    for number, case in enumerate(cases, 1):
        print(f"  run {run}  {number:02}/{len(cases)}  {case['id']}", flush=True)
        try:
            result = triage(case["raw"], index=index)
        except (RuntimeError, anthropic.APIError) as exc:
            attempts.append(
                {
                    "id": case["id"],
                    "run": run,
                    "rejected": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        attempts.append(
            {
                "id": case["id"],
                "run": run,
                "got_category": result["category"],
                "got_priority": result["priority"],
                "abstained": not result["decision_factors"]["triageable"],
                "decision_factors": result["decision_factors"],
                "tokens": result["_meta"],
            }
        )
    return attempts


def group_cases(cases: list[dict], attempts: list[dict]) -> list[dict]:
    return [
        {
            "id": case["id"],
            "expected_category": case["expected_category"],
            "expected_priority": case["expected_priority"],
            "attempts": [
                {
                    **attempt,
                    "should_abstain": case["expected_priority"] == "unknown",
                    "expected_category": case["expected_category"],
                    "expected_priority": case["expected_priority"],
                }
                for attempt in attempts
                if attempt["id"] == case["id"]
            ],
        }
        for case in cases
    ]


def print_summary(summary: dict) -> None:
    print("\n  per-run release gates")
    print(f"  {'run':<5}{'category':>11}{'priority':>11}{'abstain':>11}{'retained':>11}{'P1':>9}  gate")
    for run, metrics in summary["per_run"].items():
        def count(name: str) -> str:
            value = metrics[name]
            return f"{value['hits']}/{value['total']}"

        print(
            f"  {run:<5}{count('category'):>11}{count('priority'):>11}"
            f"{count('correct_abstention'):>11}{count('actionable_retention'):>11}"
            f"{count('p1_recall'):>9}  {'PASS' if metrics['passes_gate'] else 'FAIL'}"
        )
    print(
        f"\n  unanimously correct: {summary['unanimously_correct_cases']}/"
        f"{summary['total_cases']} cases"
    )


def main(argv: list[str]) -> int:
    dev = "--dev" in argv
    sealed = "--sealed" in argv
    if dev == sealed:
        print("choose exactly one mode: --dev or --sealed", file=sys.stderr)
        return 2

    source = DEV if dev else SEALED
    cases = validate_dataset(source, require_guards=dev)
    runs = parse_runs(argv, 1 if dev else 3)
    if sealed and runs != 3:
        print("sealed evaluation requires exactly three runs", file=sys.stderr)
        return 2
    if sealed and not review_is_approved():
        print(
            "sealed evaluation blocked: golden-v2.review.json must record an approved "
            "human review for the current dataset hash",
            file=sys.stderr,
        )
        return 2

    print(f"\nRunning {runs} x {len(cases)} calls against {MODEL}. This costs money.")
    print(f"Dataset: {source.name}  sha256={sha256(source)}\n")

    index = Bm25(load_corpus())
    attempts = []
    for run in range(1, runs + 1):
        attempts.extend(run_pass(cases, index, run))

    rows = group_cases(cases, attempts)
    baseline = evaluate(source)
    summary = summarize_live(rows, baseline)
    print_summary(summary)

    accepted = [a for a in attempts if "rejected" not in a]
    tok_in = sum(a["tokens"]["input_tokens"] for a in accepted)
    tok_out = sum(a["tokens"]["output_tokens"] for a in accepted)
    cost = tok_in / 1e6 * PRICE_IN + tok_out / 1e6 * PRICE_OUT
    payload = {
        "schema_version": 2,
        "model": MODEL,
        "dataset": {"file": source.name, "sha256": sha256(source)},
        "prompt_sha256": text_hash(SYSTEM),
        "schema_sha256": text_hash(
            json.dumps(SCHEMA, sort_keys=True, ensure_ascii=False)
        ),
        "date": date.today().isoformat(),
        "runs": runs,
        "n_cases": len(cases),
        "input_tokens": tok_in,
        "output_tokens": tok_out,
        "cost_usd": round(cost, 6),
        "summary": summary,
        "cases": rows,
    }

    if dev:
        out = DEV_RESULTS
    elif summary["passes_gate"]:
        out = PUBLISHED
    else:
        out = FAILED_SEALED
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if sealed and not summary["passes_gate"]:
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        review.update(
            {
                "status": "measured-failed",
                "measured_prompt_sha256": payload["prompt_sha256"],
                "measured_schema_sha256": payload["schema_sha256"],
                "summary": summary,
            }
        )
        REVIEW.write_text(
            json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(f"\n  {len(accepted)} calls, {tok_in:,} in / {tok_out:,} out, ${cost:.4f}")
    print(f"  written to {out.relative_to(ROOT)}\n")
    return 0 if summary["passes_gate"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
