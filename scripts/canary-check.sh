#!/bin/sh
# Prove the secret gates actually work, in both directions.
#
# This exists because the stock gitleaks ruleset does NOT detect Anthropic keys:
# a correctly-shaped planted key scanned clean. A secret gate nobody has tested
# against a real-shaped secret is decoration.
#
# Two separate checks, deliberately scoped:
#
#   1. The rule catches a planted key -> scan an isolated scratch directory.
#   2. A clean repository passes      -> scan git-tracked content only.
#
# Check 2 runs in git mode on purpose. An earlier version used --no-git, which
# ignores .gitignore and therefore scanned the developer's real .env - so the
# check started failing the moment someone followed the README and created one,
# blocking legitimate commits. Untracked and ignored files cannot reach the
# repository, so they are not this check's business; the pre-commit hook
# (protect --staged) is what guards anything actually on its way in.
#
# Usage:  sh scripts/canary-check.sh     (from the repo root)

set -e

GITLEAKS="zricethezav/gitleaks@sha256:cdbb7c955abce02001a9f6c9f602fb195b7fadc1e812065883f695d1eeaba854"

[ -f .gitleaks.toml ] || { echo "run me from the repo root" >&2; exit 2; }
command -v docker >/dev/null 2>&1 || { echo "docker required" >&2; exit 2; }

REPO=$(pwd)
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) REPO=$(pwd -W); export MSYS_NO_PATHCONV=1 ;;
esac

# Kept inside the repo so the Windows path translation above applies to it too.
CANARY_DIR=.canary-check-tmp
rm -rf "$CANARY_DIR"
trap 'rm -rf "$CANARY_DIR"' EXIT INT TERM
mkdir -p "$CANARY_DIR"

# --redact is not optional. Without it gitleaks prints the matched secret in
# full, which turns a diagnostic into a disclosure. This was learned the hard
# way by running the scan by hand without it.
scan() {
  docker run --rm -v "$REPO:/repo" "$GITLEAKS" \
    detect --source="$1" --config=/repo/.gitleaks.toml --redact $2 \
    >/dev/null 2>&1
}

# A fake key. Correct shape, never valid: the segment after the prefix is
# structured text, not entropy from a real credential. Length matters - the
# rule requires 80+ characters after the prefix, so a shorter probe passes
# cleanly and looks like the gate is broken when it isn't.
printf 'ANTHROPIC_API_KEY=sk-ant-api03-%s\n' \
  "CANARYcanaryCANARYcanaryCANARYcanaryCANARYcanaryCANARYcanaryCANARYcanaryCANARYcanaryCANARYcanary-AAxxAA" \
  > "$CANARY_DIR/canary.txt"

if scan "/repo/$CANARY_DIR" --no-git; then
  echo "FAIL: planted canary was NOT detected - the gate is not protecting you." >&2
  exit 1
fi
echo "ok: canary detected"

rm -rf "$CANARY_DIR"

if scan /repo ""; then
  echo "ok: tracked content is clean"
else
  echo "FAIL: committed content contains a secret - do not push." >&2
  exit 1
fi

echo "both gates verified"
