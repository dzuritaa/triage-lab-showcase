# Threat model

The public demo contains only synthetic data. Its primary asset is the API
budget; its primary attacker goal is cost exhaustion.

- Page loads use committed fixtures and make no API call.
- Any future live endpoint must accept only ticket text, cap input and output,
  rate-limit per IP, enforce a strongly consistent global daily budget, and fall
  back to fixtures after the cap.
- The model has no tools, writes, or network access. Retrieved context is static
  and read-only. Prompt injection can affect only the response returned to its
  author.
- Model output is schema-validated and rendered as plain text.
- The provider key remains server-side, auto-reload stays disabled, gitleaks
  scans history in CI, and the local hook prevents staged secrets.
- Request bodies are never logged; retain only counts, latency, token cost and status.

Worker implementation and deployment remain deferred. These controls are
requirements, not claims that a public API currently exists.
