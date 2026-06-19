# Pre-Phase 1 Conflict Scan

Date: 2026-05-24
Repository: `/home/l/Desktop/AOIA-Core`
Purpose: detect naming conflicts and duplication risks before initializing the MHLM/MHSR Phase 1 skeleton.

## Scope

This scan was performed before creating the `MHLM_MHSR/` skeleton.

Excluded from review noise:

- `.git/`
- `runtime/.venv/`
- `__pycache__/`
- generated package/cache internals

## Existing Relevant Structures

Existing repository surfaces relevant to Phase 1:

- `docs/`
- `docs/ADR/`
- `docs/adr/`
- `docs/architecture/`
- `docs/forensic-runtime-audit/`
- `docs/refactor/`
- `docs/reports/`
- `governance/`
- `memory/`
- `provenance/`
- `retrieval/`
- `contradictions/`
- `runtime/`
- `runtime/knowledge/`
- `runtime/memory/`
- `runtime/obsidian_vault/`
- `runtime/prompts/`
- `runtime/state/`
- `state/`

## Duplicated Folder Names

Detected repeated purpose/name surfaces:

- `memory/` and `runtime/memory/`
- `state/` and `runtime/state/`
- `governance/` and future `MHLM_MHSR/framework/governance/`
- `provenance/` and future case-study `provenance/` folders
- `contradictions/` and future case-study `contradictions/` folders
- `docs/reports/` and future case-study `reports/` folders
- `runtime/prompts/` and future case-study `prompts/` folders

Resolution for Phase 1:

- Do not merge or move any existing folder.
- Keep existing AOIA runtime structures untouched.
- Create the Phase 1 framework under a single isolated `MHLM_MHSR/` root to prevent accidental mixing with AOIA runtime folders.
- Document reuse only where exact target paths already exist.

## Mixed-Case Duplicates

Detected mixed-case naming risks:

- `docs/ADR/` and `docs/adr/`
- `runtime/prompts/` and `runtime/obsidian_vault/Prompts/`
- `runtime/knowledge/` and `runtime/obsidian_vault/Knowledge/`
- `runtime/logs/` and `runtime/obsidian_vault/Logs/`
- `runtime/logs/sessions/` and `runtime/obsidian_vault/Sessions/`

Resolution for Phase 1:

- Do not create new ADR variants.
- Do not create new prompt/report/lineage variants outside the requested Phase 1 skeleton.
- Preserve the existing mixed-case folders as-is for later review.

## Possible Collisions With Requested Skeleton

Requested new root:

- `MHLM_MHSR/`

Current status:

- No existing `MHLM_MHSR/` directory was present at scan time.

Requested case studies:

- `MHLM_MHSR/case_studies/lst/`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/`

Current status:

- No existing `case_studies/` root was present at repository root.
- No existing `lst/` case-study directory was present under repository root.
- No existing `anti_hallucination_epi_app/` directory was present under repository root.

Requested imports:

- `MHLM_MHSR/imports/provider_exports/`
- `MHLM_MHSR/imports/repo_snapshots/`
- `MHLM_MHSR/imports/git_bundles/`

Current status:

- No existing `imports/` root was present at repository root.

## Naming Inconsistencies To Preserve For Now

Existing inconsistencies are recorded but not changed:

- uppercase/lowercase ADR folder split
- top-level architecture reports mixed with `docs/` reports
- runtime state duplicated conceptually across `state/` and `runtime/state/`
- memory/provenance/contradiction concepts represented both as top-level boundary folders and runtime persistence areas

## Phase 1 Safety Decision

Proceed with a single new root:

- `MHLM_MHSR/`

Do not:

- duplicate AOIA runtime
- move AOIA files
- move LST/LSC materials
- create parallel `docs_new`, `prompts_new`, `lineage_v2`, or `runtime_copy` folders
- normalize existing mixed-case folders during this phase

Phase 1 may create only the missing framework skeleton and required Phase 1 reports.
