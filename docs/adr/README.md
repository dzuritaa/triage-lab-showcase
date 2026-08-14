# Architecture decision records

One decision per file. Each records what was decided, the evidence, **the case
against it**, and what would reverse it. The case-against section is not
decoration: a decision recorded without its cost is a advertisement.

| # | Decision | Status |
|---|---|---|
| [001](001-bm25-over-embeddings.md) | BM25 over embeddings for retrieval | accepted |
| 002 | Structured decision factors and deterministic priority | **proposed** — on `feature/structured-triage-evidence`, blocked by evaluation |
| [003](003-abstention-as-a-triage-outcome.md) | Abstention is a triage outcome, not a confidence score | accepted, with a known defect |
| [004](004-development-set-and-a-held-out-set-spent-once.md) | Prompts are tuned on a development set; the held-out set is spent once | accepted |
| [005](005-published-numbers-carry-their-provenance.md) | A published measurement carries the hash of the code that produced it | accepted |
| [006](006-labels-reviewed-blind-by-someone-else.md) | Evaluation labels are reviewed blind, by someone who is not the author | proposed — blocked on a reviewer |

**002 is missing from this branch on purpose.** It proposes replacing
prompt-derived priority with decision factors the model extracts and Python maps
deterministically. It failed its three-pass development gate — passing once out
of three frozen runs — so it stays on its branch and the published evidence is
unchanged. `docs/CASE_STUDY.md` on that branch carries the numbers.

## Reading order

If you only read two: **001** for why there is no vector database, and **005**
for how the numbers on the landing page are kept honest.

If you want the part that went wrong: **003** and **004** are a pair. 003
describes a capability that works on the set it was measured against and refuses
ordinary tickets outside it; 004 is the process change that came out of trying
to fix a different defect and making it worse.
