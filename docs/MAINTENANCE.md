# Maintenance

## Updating pinned supply-chain references

Everything in CI is pinned to something immutable. Tags are mutable — whoever
controls a repo can repoint `v4` at new code — so a tag pin is not a pin.

### GitHub Actions (automated)

Dependabot proposes these weekly. It rewrites the SHA and the trailing version
comment together, so review the diff normally.

### gitleaks container (manual)

Dependabot does **not** cover this one: its docker ecosystem reads Dockerfiles
and compose files, not images invoked inside a workflow `run:` step. Pretending
otherwise would leave a stale scanner silently.

To update:

```bash
docker pull zricethezav/gitleaks:v8.29.0
docker images --digests zricethezav/gitleaks --format '{{.Tag}} {{.Digest}}'
```

Put the printed digest in `.github/workflows/ci.yml` and update the trailing
version comment to match. Then re-run the canary test below — a scanner upgrade
can change the ruleset.

## Verifying the secret gates still work

Both gates are tested with a deliberately fake, correctly-shaped key. Run this
after any change to `.gitleaks.toml`, the hook, or the scanner version.

```bash
sh scripts/canary-check.sh
```

It must report both gates catching the canary and a clean tree passing. A green
CI badge on an untested scanner means nothing — the default gitleaks ruleset
does **not** detect Anthropic keys, which is exactly how this project's custom
rule came to exist.
