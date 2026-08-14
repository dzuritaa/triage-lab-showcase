"""Validate development and sealed evaluation datasets without model calls."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEV = ROOT / "evals" / "dev.json"
SEALED = ROOT / "evals" / "golden-v2.json"
REVIEW = ROOT / "evals" / "golden-v2.review.json"

CATEGORIES = {
    "access-identity",
    "integration",
    "performance",
    "data-quality",
    "batch-reporting",
    "insufficient-information",
}
PRIORITIES = {"P1", "P2", "P3", "P4", "unknown"}
ANSWERABLE_CATEGORY_COUNTS = {
    "access-identity": 4,
    "integration": 4,
    "performance": 4,
    "data-quality": 4,
    "batch-reporting": 4,
}
ANSWERABLE_PRIORITY_COUNTS = {"P1": 4, "P2": 6, "P3": 6, "P4": 4}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_hash(value: str) -> str:
    """Hash a prompt or a serialized schema.

    Lives here rather than in evals/live.py because both the recorder and the
    page checker need it and they must agree byte for byte, while only one of
    them may import `anthropic`. This module is standard library only, which is
    what lets CI check provenance with nothing installed.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_dataset(path: Path, require_guards: bool = False) -> list[dict]:
    cases = load(path)
    assert len(cases) == 30, f"{path.name}: expected 30 cases, got {len(cases)}"
    assert len({c["id"] for c in cases}) == 30, f"{path.name}: duplicate ids"
    assert len({c["raw"].casefold().strip() for c in cases}) == 30, (
        f"{path.name}: duplicate ticket text"
    )

    corpus_ids = {
        d["id"]
        for name in ("incidents.json", "kb.json")
        for d in json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))
    }
    for case in cases:
        assert case["expected_category"] in CATEGORIES, f"{case['id']}: bad category"
        assert case["expected_priority"] in PRIORITIES, f"{case['id']}: bad priority"
        relevant = set(case["relevant_docs"])
        assert relevant <= corpus_ids, f"{case['id']}: unknown relevant docs {relevant-corpus_ids}"
        ambiguous = case["expected_category"] == "insufficient-information"
        assert ambiguous == (case["expected_priority"] == "unknown"), (
            f"{case['id']}: abstention must use unknown priority"
        )
        assert ambiguous == (not relevant), (
            f"{case['id']}: answerable cases need relevant docs; ambiguous cases need none"
        )
        if require_guards:
            assert case.get("guards"), f"{case['id']}: development case needs guards"

    answerable = [c for c in cases if c["expected_priority"] != "unknown"]
    ambiguous = [c for c in cases if c["expected_priority"] == "unknown"]
    assert len(answerable) == 20 and len(ambiguous) == 10, (
        f"{path.name}: expected 20 answerable and 10 ambiguous"
    )
    assert Counter(c["expected_category"] for c in answerable) == ANSWERABLE_CATEGORY_COUNTS
    assert Counter(c["expected_priority"] for c in answerable) == ANSWERABLE_PRIORITY_COUNTS
    return cases


def review_is_approved() -> bool:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    return (
        review.get("status") == "approved"
        and bool(review.get("reviewer_role"))
        and bool(review.get("reviewed_at"))
        and review.get("dataset_sha256") == sha256(SEALED)
    )


def separation(dev: list[dict], sealed: list[dict]) -> dict:
    """How independent the sealed set is from the development set.

    The uniqueness assertion below only ever checked for copied *text*, and it
    passed. It could not see that the two sets were written case for case in the
    same order, which is what actually destroys a holdout: the same answer in
    the same slot means the sealed set re-asks the development questions.

    Reported rather than asserted. A threshold here would be a guess, and the
    number is the evidence - a set that agrees with its own development twin on
    every priority is not independent, whatever a cutoff would have said.
    """
    pairs = list(zip(dev, sealed))
    return {
        "priority": sum(d["expected_priority"] == s["expected_priority"] for d, s in pairs),
        "category": sum(d["expected_category"] == s["expected_category"] for d, s in pairs),
        "relevant_docs": sum(
            set(d["relevant_docs"]) == set(s["relevant_docs"]) for d, s in pairs
        ),
        "total": len(pairs),
    }


def main() -> int:
    dev = validate_dataset(DEV, require_guards=True)
    sealed = validate_dataset(SEALED)
    assert not ({c["raw"].casefold() for c in dev} & {c["raw"].casefold() for c in sealed}), (
        "development and sealed sets overlap"
    )
    state = "approved" if review_is_approved() else "pending human review"
    print(
        f"datasets ok: dev 20+10, sealed 20+10; "
        f"sealed sha256 {sha256(SEALED)[:12]}...; {state}"
    )
    sep = separation(dev, sealed)
    print(
        f"  position-aligned agreement with dev.json: "
        f"priority {sep['priority']}/{sep['total']}, "
        f"category {sep['category']}/{sep['total']}, "
        f"docs {sep['relevant_docs']}/{sep['total']}"
    )
    if sep["priority"] == sep["total"]:
        print(
            "  golden-v2.json is a position-for-position rewrite of the development\n"
            "  set, not an independent holdout. It must never be published as sealed\n"
            "  evidence - see docs/adr/004 and docs/adr/006."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
