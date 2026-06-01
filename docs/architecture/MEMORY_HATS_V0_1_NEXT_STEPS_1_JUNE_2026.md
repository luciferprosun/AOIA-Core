# Memory Hats / WhiteHat v0.1 Next Steps — 1 June 2026

## 1. Immediate Next Engineering Steps

- Stop feature coding before NLnet unless there is a deliberate review decision.
- Human-review GT-HAT-1 through GT-HAT-9 commits, reports, and tests.
- Optionally review JSONL import/export hardening after the NLnet boundary is safe.
- Clean up docs wording for reviewer clarity.
- Keep `main` frozen at the protected NLnet-safe checkpoint until an explicit merge decision is made.
- Do not merge Memory Hats to `main` before deliberate human review.

## 2. Month 1 Roadmap

- Freeze the v0.1 prototype as a dev-branch evidence point.
- Create a reviewer quickstart that explains the local-only advisory flow.
- Add more focused tests around malformed records, duplicate tags, and lookup edge cases.
- Clean docs for plain reviewer language.
- Prepare a public developer-preview branch only after repository hygiene review.

## 3. Month 2 Roadmap

- Expand the ERCC command corpus with reviewed and candidate Linux/RHCSA entries.
- Target 2,000 reviewed/candidate entries only if provenance and deduplication remain clean.
- Strengthen deterministic deduplication and evidence reference conventions.
- Harden RHCSA/RHCE command family boundaries without treating grammar matches as safety proof.

## 4. Month 3 Roadmap

- Design Memory Hats v0.2 based on measured v0.1 gaps.
- Harden JSONL import/export validation and compatibility checks.
- Add a clearer candidate/confirmed/rejected review workflow.
- Consider optional advisory object consumers only after boundaries remain stable.
- Do not add sync unless it has an explicit design, threat model, and review process.

## 5. Month 4 Roadmap

- Prepare a developer preview with examples and docs.
- Add safe demos only if they do not execute commands or modify runtime policy.
- Consider a safe CLI/demo if explicitly approved and kept separate from executor behavior.
- Continue repository hygiene and reduce stale or confusing docs.

## 6. Month 5 Optional Roadmap

- Coding Hat.
- Security/Secrets Hat.
- Research Claim Boundary Hat.
- Project Memory Hat.
- Memory Garden design note only.
- Signed packs design note only.

These are optional roadmap items, not v0.1 requirements.

## 7. Hard No-Go Before Review

- No broad refactor.
- No sync or global tags.
- No Phi code as retrieval, ranking, indexing, deduplication, or truth logic.
- No command execution.
- No autonomous runtime changes.
- No truth-engine claims.
- No executor/router/provider/kernel/provenance/TUI/web integration.
- No merge to `main` before deliberate review.
