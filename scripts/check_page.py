"""Assert the landing page publishes only what the repository can produce.

The page's entire argument is that every number on it is reproducible. That
property held once and then broke silently: the page carried EVAL-03's token
counts while the ADR it links to as proof still carried EVAL-02's, because the
fixture was re-recorded and the prose was not. The independent design review
found it. Nothing would have.

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

from core.triage import SCHEMA, SYSTEM
from evals.run import evaluate, summarize_live
from evals.validate_data import text_hash

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "web" / "index.html"
FIXTURE = ROOT / "fixtures" / "example.json"
# Written by `python -m evals.live`. Optional: the offline checks must pass on a
# clone that has never paid for a live run, so its absence is not a failure.
LIVE = ROOT / "evals" / "live-results.json"

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

    # 3. Abstention. The page's most checkable claim is that the emptiest ticket
    # outscores the clearest one, so the two scores behind it are asserted to
    # two decimals rather than described.
    amb = r["n_ambiguous"]
    want(f"Abstained when it should {round(r['abstention_on_ambiguous'] * amb)} of {amb} cases",
         "abstention tally")
    want(f"best possible threshold: {r['abstention_oracle_caught']} of {amb}",
         "abstention oracle")
    want(f"Held firm when it should {round(r['no_abstention_on_answerable'] * n)} of {n} cases",
         "over-abstention tally")
    want(r["ambiguous_worst"], "worst ambiguous case id")
    want(f"{r['ambiguous_score_max']:.2f}", "worst ambiguous case score")
    want(f"{r['answerable_score_max']:.2f}", "best answerable case score")

    # 4. The model's own scores, from the recorded live run. Checked the same
    # way as everything else: against the file the run wrote, never against a
    # number typed into the HTML. If the page is going to publish a result the
    # model has to be paid to produce, the claim and the receipt stay married.
    if LIVE.exists():
        live = json.loads(LIVE.read_text(encoding="utf-8"))

        # Provenance. evals/live.py records the prompt, schema and dataset it
        # ran against; until now nothing read those fields back, which made
        # them a receipt nobody checked. A model score is only reproducible if
        # the thing that produced it still exists, so a results file whose
        # prompt has since changed is not evidence for anything on the page.
        #
        # A file with no hash at all fails rather than being waved through.
        # Grandfathering is how a guard stops guarding, and the exemption
        # would outlive everyone's memory of why it was granted.
        recorded_prompt = live.get("prompt_sha256")
        recorded_schema = live.get("schema_sha256")
        current_prompt = text_hash(SYSTEM)
        current_schema = text_hash(
            json.dumps(SCHEMA, sort_keys=True, ensure_ascii=False)
        )
        if recorded_prompt is None or recorded_schema is None:
            problems.append(
                f"  provenance: {LIVE.name} records no prompt or schema hash, so "
                f"nothing can confirm the published model scores came from the "
                f"code in this repository. Re-record with `python -m evals.live`."
            )
        else:
            for name, was, now in (
                ("prompt", recorded_prompt, current_prompt),
                ("schema", recorded_schema, current_schema),
            ):
                if was != now:
                    problems.append(
                        f"  provenance: the {name} changed since these scores were "
                        f"measured ({was[:12]} -> {now[:12]}). The page is citing "
                        f"numbers produced by code that no longer exists. Re-record "
                        f"with `python -m evals.live`, or stop publishing them."
                    )

        if live.get("schema_version") == 2:
            rows = live["cases"]
        else:
            rows = [
                {
                    "id": c["id"],
                    "expected_category": c["expected_category"],
                    "expected_priority": c["expected_priority"],
                    "attempts": [{**c, "run": 1}],
                }
                for c in live["cases"]
            ]
        live_summary = summarize_live(rows, r)["aggregate"]
        checks = [
            ("Model, abstained when it should", live_summary["correct_abstention"]),
            ("Model, held firm when it should", live_summary["actionable_retention"]),
            ("Model, category accuracy", live_summary["category"]),
            ("Model, priority accuracy", live_summary["priority"]),
        ]
        for label, metric in checks:
            want(f"{label} {metric['hits']} of {metric['total']} cases", f"{label} tally")

        want(f"${live['cost_usd']:.4f}", "live run cost")

        # The escalation claim is the page's strongest and most falsifiable
        # statement, so it is asserted rather than trusted: if a future run
        # produces a miss in the other direction, the page must stop saying
        # every one is an escalation.
        order = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
        # An abstention on an answerable case carries priority "unknown", which
        # is not a level and cannot be compared. It is already counted by the
        # held-firm tally, so exclude it here rather than ranking it. An earlier
        # version did not, and crashed with a KeyError the first time a run
        # actually produced one.
        attempts = [a for row in rows for a in row["attempts"]]
        misses = [
            c for c in attempts
            if "rejected" not in c
            and not c["should_abstain"]
            and c["got_priority"] != c["expected_priority"]
            and c["got_priority"] in order
        ]
        if misses and all(
            order[c["got_priority"]] < order[c["expected_priority"]] for c in misses
        ):
            want("escalation, by\n      exactly one level", "escalation claim")
        elif misses:
            problems.append(
                "  escalation claim: the page says every priority miss is an "
                "escalation, but the recorded run contains a miss in the other "
                "direction - rewrite the section"
            )

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
