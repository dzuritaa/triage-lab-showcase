#!/bin/sh
# Prove the secret gates actually work, in both directions.
#
# This exists because the stock gitleaks ruleset does NOT detect Anthropic keys:
# a correctly-shaped planted key scanned clean. A secret gate nobody has tested
# against a real-shaped secret is decoration.
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

CANARY="canary-check-$$.txt"
trap 'rm -f "$CANARY"' EXIT INT TERM

scan() {
  docker run --rm -v "$REPO:/repo" "$GITLEAKS" \
    detect --source=/repo --redact --no-git >/dev/null 2>&1
}

# A fake key. Correct shape, never valid: the segment after the prefix is
# structured text, not entropy from a real credential.
printf 'ANTHROPIC_API_KEY=sk-ant-api03-%s\n' \
  "CANARYcanaryCANARYcanaryCANARYcanaryCANARYcanaryCANARYcanaryCANARYcanaryCANARYcanaryCANARYcanary-AAxxAA" \
  > "$CANARY"

if scan; then
  echo "FAIL: planted canary was NOT detected — the gate is not protecting you." >&2
  exit 1
fi
echo "ok: canary detected"

rm -f "$CANARY"

if scan; then
  echo "ok: clean tree passes"
else
  echo "FAIL: clean tree reported a leak — the gate blocks legitimate work." >&2
  exit 1
fi

echo "both gates verified"
