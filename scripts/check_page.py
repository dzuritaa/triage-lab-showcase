"""Assert the landing page publishes only what the repository can produce.

The page's entire argument is that every number on it is reproducible. That
property held once and then broke silently: the page carried EVAL-03's token
counts while the ADR it links to as proof still carried EVAL-02's, because the
fixture was re-recorded and the prose was not. The independent design review
found it. Nothing would have.

`docs/HANDOFF.md` recorded that a script now guards this. It did not exist.
This is that script.

It checks two things, both against sources rather than against a copy:

  1. Every result string the page renders appears verbatim in
     fixtures/example.json — no paraphrasing under a "Recorded" stamp.
  2. Every score the page prints matches what evals.run computes right now.

    python -m scripts.check_page

Standard library only, so CI runs it with nothing installed.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

from evals.run import evaluate

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "web" / "index.html"
FIXTURE = ROOT / "fixtures" / "example.json"

_TAGS = re.compile(r"<(script|style)\b.*?</\1>|<[^>]+>", re.S | re.I)
_SPACE = re.compile(r"\s+")


def page_text() -> str:
    """Visible page text, whitespace-collapsed, entities resolved.

    Source newlines are an accident of hand-wrapped HTML, so a fixture sentence
    split across three lines must still match. Non-breaking hyphens are folded
    to ASCII: the page uses them for typesetting, the fixture does not.
    """
    raw = PAGE.read_text(encoding="utf-8")
    text = html.unescape(_TAGS.sub(" ", raw))
    return _SPACE.sub(" ", text.replace("‑", "-").replace("‐", "-"))


def normalise(s: str) -> str:
    return _SPACE.sub(" ", s.replace("‑", "-").replace("‐", "-")).strip()


def check() -> list[str]:
    text = page_text()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = fixture["result"]
    r = evaluate()
    problems: list[str] = []

    def want(claim: str, label: str) -> None:
        if normalise(claim) not in text:
            problems.append(f"  {label}: page does not contain {normalise(claim)[:90]!r}")

    # 1. The recorded result, verbatim. The reply is the one most likely to be
    # quietly tidied, which is exactly why it is checked whole rather than by
    # its opening words.
    want(fixture["ticket"], "ticket")
    want(result["reasoning"], "reasoning")
    want(result["root_cause_direction"], "root cause")
    want(result["draft_reply"], "draft reply")
    want(result["category"], "category")
    for hit in result["similar"]:
        want(hit["id"], "retrieved id")

    meta = result["_meta"]
    want(f"{meta['input_tokens']:,} input and {meta['output_tokens']:,} output tokens",
         "token counts")

    # 2. The scores, against what evals.run computes on this checkout — not
    # against a number pasted here, which would only prove the paste matches.
    scores = [
        ("Retrieval recall @3", r["retrieval_recall_at_3"], r["retrieval_random_at_3"], "random"),
        ("Retrieval recall @1", r["retrieval_recall_at_1"], r["retrieval_random_at_1"], "random"),
        ("Category accuracy", r["category_accuracy_1nn"], r["category_accuracy_majority"], "majority"),
        ("Priority accuracy", r["priority_accuracy_1nn"], r["priority_accuracy_majority"], "majority"),
    ]
    n = r["n_cases"]
    for label, score, base, kind in scores:
        want(f"{label} {score:.0%} vs {base:.0%} {kind}", f"{label} summary")
        want(f"{label} {round(score * n)} of {n} cases", f"{label} tally")

    return problems


def main() -> int:
    problems = check()
    if problems:
        print("PAGE DOES NOT MATCH ITS SOURCES\n" + "\n".join(problems))
        print("\nFix the page, or re-record the fixture - do not edit the claim.\n")
        return 1
    print("page ok: recorded strings verbatim, every score matches evals.run\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
