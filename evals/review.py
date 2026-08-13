"""Export and approve a blind human review of the sealed dataset."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from evals.validate_data import CATEGORIES, PRIORITIES, REVIEW, SEALED, sha256

ROOT = Path(__file__).resolve().parent.parent
BLIND = ROOT / "evals" / "golden-v2.blind-review.json"


def export() -> int:
    if BLIND.exists():
        print(f"refusing to overwrite {BLIND.relative_to(ROOT)}")
        return 2
    cases = json.loads(SEALED.read_text(encoding="utf-8"))
    form = [
        {
            "id": case["id"],
            "raw": case["raw"],
            "review_category": "",
            "review_priority": "",
            "review_relevant_docs": [],
        }
        for case in cases
    ]
    BLIND.write_text(json.dumps(form, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"wrote {BLIND.relative_to(ROOT)} with ticket text only; "
        "give this file, not golden-v2.json, to the reviewer"
    )
    return 0


def approve(reviewer_role: str) -> int:
    if not BLIND.exists():
        print("blind review form missing; run: python -m evals.review export")
        return 2
    sealed = {c["id"]: c for c in json.loads(SEALED.read_text(encoding="utf-8"))}
    reviewed = json.loads(BLIND.read_text(encoding="utf-8"))
    problems = []
    for row in reviewed:
        case_id = row.get("id", "<missing>")
        if case_id not in sealed:
            problems.append(f"{case_id}: unknown or duplicate case")
            continue
        category = row.get("review_category")
        priority = row.get("review_priority")
        relevant = row.get("review_relevant_docs")
        if category not in CATEGORIES or priority not in PRIORITIES or not isinstance(relevant, list):
            problems.append(f"{case_id}: review fields are incomplete or invalid")
            continue
        expected = sealed[case_id]
        if (
            category != expected["expected_category"]
            or priority != expected["expected_priority"]
            or set(relevant) != set(expected["relevant_docs"])
        ):
            problems.append(
                f"{case_id}: review disagrees; discuss and update the sealed labels "
                "or the agreed review form before approval"
            )
    if len(reviewed) != len(sealed) or len({r.get("id") for r in reviewed}) != len(sealed):
        problems.append("review must contain every sealed case exactly once")
    if problems:
        print("review not approved:\n  " + "\n  ".join(problems))
        return 1

    receipt = {
        "dataset": SEALED.name,
        "status": "approved",
        "reviewer_role": reviewer_role,
        "reviewed_at": date.today().isoformat(),
        "dataset_sha256": sha256(SEALED),
    }
    REVIEW.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"approved {SEALED.name} at sha256 {receipt['dataset_sha256']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("export")
    approve_parser = sub.add_parser("approve")
    approve_parser.add_argument("--reviewer-role", required=True)
    args = parser.parse_args()
    return export() if args.command == "export" else approve(args.reviewer_role)


if __name__ == "__main__":
    raise SystemExit(main())
