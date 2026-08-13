# Maintenance

## External facts

The default model ID and list prices are owned by Anthropic. Check them before
resuming the project after a gap or when live calls return 404.

- Model: `claude-haiku-4-5`, overridable with `TRIAGE_MODEL`.
- Pricing used by `evals/live.py`: $1/MTok input and $5/MTok output.

A model or prompt change invalidates the recorded fixture and paid evaluation.
Re-record only after development gates pass. A sealed run may replace
`evals/live-results.json` only when all three passes satisfy the release gate.

## Evaluation workflow

1. Validate data with `python -m evals.validate_data`.
2. Iterate only with `python -m evals.live --dev`.
3. Freeze the prompt and confirm it with `python -m evals.live --dev --runs 3`.
4. Export and approve a blind support-domain review using
   `docs/LABEL_REVIEW.md`; the utility records the matching SHA-256.
5. Run `python -m evals.live --sealed`. It always performs three passes and
   refuses unreviewed data. A failure is written to an ignored file and cannot
   overwrite published evidence.
6. Only after a pass: re-record `DEMO-01`, update published claims, and run
   `python -m scripts.check_page`.

Development receipts are ignored. Commit only the currently published
`live-results.json`; Git history and `docs/CASE_STUDY.md` preserve experiments.

## Supply-chain pins and secret gates

Dependabot updates SHA-pinned GitHub Actions. The gitleaks container digest in
CI is manual: pull the intended tag, read its digest, update the workflow, then
run `sh scripts/canary-check.sh`. The canary must be detected and tracked content
must pass cleanly.
