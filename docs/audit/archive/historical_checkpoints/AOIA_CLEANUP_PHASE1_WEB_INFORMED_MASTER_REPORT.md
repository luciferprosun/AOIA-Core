# AOIA Cleanup Phase 1 Web-Informed Master Report

Date: 2026-05-28
Scope: safe cleanup audit and AOIA-Nano provenance kernel planning only.

## 1. Repository Identity

- Path: `/home/l/Desktop/AOIA-Core`
- Branch: `main`
- HEAD: `ee6f64a`
- Remote: `https://github.com/luciferprosun/AOIA-Core.git`
- Canonical public URL: `https://github.com/luciferprosun/AOIA-Core`
- Naming recommendation: use `AOIA`, not `AIOA`.

## 2. Health Status

Repository was clean before audit reports. `python` is not installed, but `python3` compile checks pass.

## 3. Test Status

`pytest` is unavailable. Fallback `unittest` discovery ran:

```text
Ran 145 tests in 3.439s
FAILED (errors=2, skipped=2)
```

143 tests pass. The 2 errors are optional TUI import failures caused by missing `textual`. The 2 skips are Playwright-dependent browser tests.

## 4. Boot Blockers

Primary blockers:

- `runtime/main.py` initializes memory, worker memory, provider manager, router, retrieval, executor, and optional orchestrator-adjacent state in one boot path.
- `runtime/tools/memory.py` writes state, memory JSONL, logs, and Obsidian vault artifacts into the repo tree.
- `runtime/providers/config.py` writes provider state under repo `state`.
- `runtime/commands/local_commands.py` contains a hardcoded desktop helper path.
- Event/provenance sinks are fragmented.

## 5. Must-Keep Core

Must keep:

- `runtime/tools/provenance.py`
- `runtime/tools/provenance_readout.py`
- provenance verification tests
- deterministic router
- immutable config loader
- RHCSA retrieval facade
- RHCSA retrieval engine
- validator and invariant tests
- canonical/index/manifest RHCSA assets
- bounded executor
- governance contracts
- non-goals doctrine

Must-keep count: 17 files/folders/groups.

## 6. Safe Archive Candidates

Safe archive candidates include:

- `reports/forensic_export/`
- `docs/forensic-runtime-audit/`
- `runtime/reports/`
- stale root phase reports
- `docs/PHASE*.md`
- generated PDF/HTML exports

## 7. Safe Remove Candidates

Remove only after confirmation:

- generated `__pycache__/`
- generated scan artifacts
- duplicated top-level mutable state files
- generated knowledge reports if archived elsewhere

## 8. Runtime State Pollution

Runtime state currently exists in:

- `runtime/logs/`
- `runtime/memory/`
- `runtime/obsidian_vault/`
- `runtime/state/`
- `state/`

This should move to an ignored/external runtime home before AOIA-Nano extraction.

## 9. Single Event Ledger Plan

Target ledger:

```text
provenance.log.jsonl
```

Minimal event kinds:

- `request_received`
- `route_decision`
- `retrieval_hit`
- `retrieval_miss`
- `action_proposed`
- `action_approved`
- `action_result`
- `provider_call_requested`
- `provider_call_completed`
- `replay_verified`

## 10. Provenance Standard Mapping

AOIA should align conceptually with:

- W3C PROV: entity, activity, agent, used, wasGeneratedBy, wasAttributedTo.
- OpenLineage: run, job, dataset/artifact, facet/metadata.
- SLSA: subject, builder, invocation/build definition, materials, verification.
- Sigstore/Rekor: immutable transparency log, signed metadata, inclusion/integrity verification.

Do not implement these standards in Phase 1.

## 11. RHCSA Knowledge Separation Plan

AOIA-Core should ship only:

- canonical knowledge
- index
- manifest
- schema/policy

Future `aoia-knowledge-rhcsa` should own:

- raw/source PDFs
- extracted/parsed inputs
- candidates/review queues
- validator/build pipeline
- generated reports

## 12. AOIA-Nano Core Mapping

Future AOIA-Nano should contain:

- config
- deterministic router
- retrieval facade
- provenance ledger/readout
- bounded executor
- deterministic mock provider
- one real provider only after MVP

Do not port `runtime/main.py` wholesale.

## 13. Future Compatibility Notes

Future adapters may include:

- MCP adapter
- OpenLineage exporter
- SLSA-style attestation exporter
- Sigstore/Rekor anchoring
- DVC/lakeFS-style knowledge versioning
- LangGraph integration only after MVP, if needed

## 14. Next 7 Prompt Sequence

1. Prompt 2: Fix boot blockers only.
2. Prompt 3: Move generated runtime state out of repo and update `.gitignore`.
3. Prompt 4: Archive stale docs and forensic exports.
4. Prompt 5: Remove/archive dead orchestrator, circadian, environment systems.
5. Prompt 6: Unify ADR structure.
6. Prompt 7: Prepare RHCSA canonical library integration.
7. Prompt 8: Begin AOIA-Nano runtime extraction.

## 15. Risks

- Moving runtime state can break memory/executor tests if paths are not injectable.
- Removing orchestrator code can break command/UI status tests if commands still expose `/orchestrator`.
- RHCSA split can break retrieval if canonical/index paths are not stable.
- TUI test failures will remain until optional `textual` is installed or tests are dependency-gated.
- Web/browser tests remain environment-dependent without Playwright.

## 16. Exact Recommended Next Prompt

```text
AOIA-Core Cleanup Phase 2 - Fix Boot Blockers Only

Analysis from Phase 1 is complete. Make only the smallest runtime changes needed to let the deterministic kernel boot without initializing generated repo state or experimental orchestration surfaces. Do not remove features yet. Do not archive docs yet. Preserve all passing tests. Run focused main/router/provider/memory tests and document any optional dependency gaps.
```

## Generated Reports

- `docs/audit/AOIA_CLEANUP_REPO_IDENTITY.md`
- `docs/audit/AOIA_CLEANUP_HEALTHCHECK.md`
- `docs/audit/AOIA_BOOT_BLOCKERS.md`
- `docs/audit/AOIA_PROVENANCE_STANDARD_MAPPING.md`
- `docs/audit/AOIA_SINGLE_EVENT_LEDGER_PLAN.md`
- `docs/audit/AOIA_CLEANUP_CLASSIFICATION.md`
- `docs/audit/AOIA_RHCSA_KNOWLEDGE_SEPARATION_PLAN.md`
- `docs/audit/AOIA_NANO_CORE_MAPPING.md`
- `docs/audit/AOIA_FUTURE_COMPATIBILITY_NOTES.md`
- `docs/audit/AOIA_CLEANUP_EXECUTION_SEQUENCE.md`
- `docs/audit/AOIA_CLEANUP_PHASE1_WEB_INFORMED_MASTER_REPORT.md`
