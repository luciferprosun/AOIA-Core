# GT7 28.05 Controlled Cleanup Plan

Date: 2026-05-28

## Current Branch

- `main`

## Current HEAD

- `5d40ce1dd29e012276b30ab48ac66887bd4b6cb1`

## Git Status

Read-only planning started from:

- `?? docs/audit/GT6B_28_05_COMMIT_PUSH_FINAL_REPORT.md`
- `?? docs/audit/GT7_28_05_HANDOFF_REPORT.md`

This plan step is read-only with respect to repository content. No files were moved, deleted, renamed, committed, or pushed. No source code, runtime architecture, provenance, Evidence Memory, Contradiction Registry, or RHCSA/RHP/Linux knowledge assets were modified.

## Canonical Keep Set

These should remain canonical and should not be moved in GT7:

- `README.md`
- `ROADMAP.md`
- `AUTHORITY_SCOPE.md`
- `docs/governance/APPEND_ONLY_PROVENANCE_CONTRACT.md`
- `docs/governance/EVIDENCE_WRITE_CONTRACT.md`
- `docs/governance/GOVERNANCE_IMPLEMENTATION_STATUS.md`
- `docs/governance/PROVENANCE_VERIFICATION_CONTRACT.md`
- `docs/governance/TEST_ENVIRONMENT_POLICY.md`
- `docs/ADR/ADR-001-deterministic-routing.md`
- `docs/ADR/ADR-002-three-depth-model.md`
- `docs/ADR/ADR-003-local-first-execution.md`
- `docs/ADR/ADR-004-no-runtime-learning.md`
- `docs/ADR/ADR-005-fail-fast-philosophy.md`
- `runtime/knowledge/` canonical RHCSA/RHP/Linux knowledge assets
- all source code under `runtime/`, `tests/`, and `scripts/`

## Root Markdown Cleanup Plan

### Stay at root

- `README.md`
- `ROADMAP.md`
- `AUTHORITY_SCOPE.md`

### Move later to historical planning/archive

These are strong stale-planning candidates and create authority ambiguity at the repository root:

- `AOIA_CANONICAL_STRUCTURE_PLAN.md`
- `AOIA_CONTAMINATION_REPORT.md`
- `AOIA_DEPENDENCY_GRAPH.md`
- `AOIA_ENVIRONMENT_AUDIT.md`
- `AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md`
- `AOIA_TRANSITIONAL_COMPONENTS.md`
- `CURRENT_MEMORY_FLOW.md`
- `MEMORY_BOUNDARY_ANALYSIS.md`
- `MEMORY_LAYER_DECOMPOSITION.md`
- `MUTABLE_STATE_ISOLATION_PLAN.md`
- `ORCHESTRATION_REMNANT_AUDIT.md`
- `ROUTING_AUTHORITY_ANALYSIS.md`

Preferred future target:

- `archive/historical_planning/root/`

### Manual review before any move

These look potentially useful as architecture/governance references, but they overlap conceptually with newer doctrine and may still be cited:

- `AOIA_MEMORY_ONTOLOGY.md`
- `AOIA_RUNTIME_MAP.md`
- `CONTRADICTION_SEMANTICS.md`
- `FILESYSTEM_ONTOLOGY_LAYOUT.md`
- `PROVENANCE_FOUNDATION.md`

Proposed future targets after manual review:

- `docs/architecture/` if still current and uniquely valuable
- otherwise `docs/historical/` or `archive/historical_planning/`

## docs/ADR vs docs/adr Resolution Plan

Resolution target:

- `docs/ADR/` remains canonical
- `docs/adr/` becomes legacy material and should not remain a parallel authority tree

Reasoning:

- `docs/ADR/` contains the current five canonical deterministic/local-first ADRs
- `docs/adr/` uses a different naming scheme and overlaps semantically with the canonical ADR set
- case-only directory distinction is risky on case-insensitive filesystems and makes cross-platform tooling less predictable

Planned action:

1. diff each file in `docs/adr/` against the canonical `docs/ADR/` set
2. preserve anything not represented elsewhere
3. move `docs/adr/` to a legacy location such as `docs/historical/adr_legacy/`
4. update any references to `docs/adr/`

Risk note:

- this is the highest-priority GT7 batch because mixed-case parallel ADR trees are a structural authority hazard
- it is also one of the highest-risk moves because links and scripts may still refer to the lowercase path

## Forensic Export Quarantine/Archive Plan

`reports/forensic_export/` should not remain near live authority surfaces.

Policy:

- treat the entire tree as export material, not canonical doctrine
- treat `source_export/` as duplicated snapshot content, not a second repository authority root
- do not use any file from this tree as evidence merely because it exists in a forensic package

Preferred future target:

- `archive/forensic_exports/reports_forensic_export/`

Notes:

- `reports/forensic_export/source_export/` duplicates root docs, runtime code, tests, and other material
- `reports/forensic_export/chunked_markdown/`, HTML, PDF, and manifest files are review artifacts only
- `reports/linux-engineering/` is separate and should not be bundled automatically with forensic exports

## Runtime Generated-State Policy

These are generated-runtime surfaces and must never be treated as evidence by path alone:

- `runtime/logs/`
- `runtime/obsidian_vault/`
- `runtime/state/`
- `runtime/project_scan.json`
- `runtime/contradiction_registry.json`
- `runtime/memory/*.jsonl`
- `runtime/memory/hats/*.json`

Policy:

- remain local/ignored
- never become canonical by mere presence
- never be used as evidence without explicit doctrine and provenance rules

Tracked residue still present:

- `runtime/reports/*.md` is still tracked and should be handled carefully
- `runtime/memory/__init__.py`
- `runtime/memory/gemma_worker_memory.py`
- `runtime/memory/rhcsa_context.py`

Important distinction:

- tracked Python files under `runtime/memory/` are source code and must not be moved in GT7
- generated JSONL/JSON/markdown vault/log/state artifacts should remain local-only
- tracked `runtime/reports/` files are generated/report-like and should be handled only in a separate batch with explicit file lists and human approval

## docs/audit Policy

Default GT7 policy:

- keep `docs/audit/` in place during GT7
- treat GT2-GT6B reports as valid historical engineering record
- do not move active audit artifacts during the same phase as ADR or root cleanup

Special case:

- explicitly model-generated or web-informed files such as `docs/audit/AOIA_CLEANUP_PHASE1_WEB_INFORMED_MASTER_REPORT.md` should be candidates for later quarantine or explicit labeling, not silent deletion

## Governance and Stabilization Policy

### docs/governance/

Keep in place. These are canonical contracts and should not move in GT7.

### docs/stabilization/

Treat as historical milestones, not repository-root doctrine.

Recommended stance:

- keep in `docs/stabilization/` for now
- optionally reclassify later under `docs/historical/stabilization/` only after links, README references, and reviewer navigation are updated

## RHCSA / Linux Knowledge Policy

Do not alter content or location of canonical retrieval assets in GT7 unless a future phase proves an operational necessity.

Safe policy:

- keep `runtime/knowledge/` intact
- do not mix it with runtime-generated reports
- do not move source PDFs, canonical indexes, manifests, validators, or examples during GT7
- preserve retrieval path stability for tests and runtime behavior

## Tests, Scripts, and Source Code

Must not move during GT7 cleanup:

- `runtime/**/*.py`
- `tests/**/*.py`
- `scripts/**/*`
- provider config, router code, provenance tooling, validator code, retrieval code

## Manual Review List

Highest-priority manual review categories:

- root doctrine/architecture files with `unknown-needs-review` classification
- lowercase `docs/adr/` files before any relocation
- tracked `runtime/reports/` markdowns
- `docs/reports/` and `docs/refactor/` legacy planning/report surfaces
- `docs/checkpoints/` short-term checkpoint material
- explicit external-model-output records that still live in `docs/audit/`

Do not resolve these by guessing. They need file-by-file confirmation before any physical move.

## Files and Directories Not To Touch

- `runtime/knowledge/`
- `runtime/**/*.py`
- `tests/`
- `scripts/`
- `docs/governance/`
- canonical `docs/ADR/`
- all RHCSA/RHP/Linux knowledge source and retrieval files

## Proposed GT7 Move Batches

### Batch 1

`docs/ADR` vs `docs/adr` resolution only

- preflight: `git status --short`, exact diff list, reference scan for `docs/adr/`
- execution: legacy ADR relocation only
- validation: `compileall`, `unittest`, reference scan, `git diff --stat`

### Batch 2

Root stale planning markdown relocation only

- preflight: freeze exact file list
- execution: move stale root planning docs to historical/archive target
- validation: `rg` for broken references, `compileall`, `unittest`

### Batch 3

Forensic exports quarantine/archive only

- preflight: confirm no operational dependency on `reports/forensic_export/`
- execution: move export tree into archive/quarantine target
- validation: reference scan, `git status`, `git diff --stat`

### Batch 4

Runtime generated report handling only, if safe

- preflight: distinguish tracked reports from ignored/local runtime state
- execution: only if exact tracked file list is approved
- validation: `compileall`, `unittest`, ignore rules check, no source changes

### Batch 5

Documentation index/update only

- execution: update README or documentation indexes to point to the new locations
- validation: link/reference scan plus test suite

## Expected Risk Level

- overall GT7 risk: `medium`
- highest-risk subareas:
  - `docs/ADR` vs `docs/adr` consolidation
  - `reports/forensic_export/source_export/` relocation
  - any move involving tracked `runtime/reports/`

## Reference Breakage Risks

Expected breakage sources if moves are executed without a reference pass:

- markdown links
- hard-coded path mentions in audit/history docs
- repository-tree snapshots such as `docs/FULL_PROJECT_TREE.txt`
- transfer/state reports under `docs/`
- forensic export manifests that embed original paths

## Rollback Plan

Future physical GT7 execution must be reversible per batch:

1. record `git status --short` before batch
2. move only one approved batch at a time
3. validate after batch
4. if references or tests fail, revert only that batch before touching the next one
5. commit after each safe batch, or do one final commit only if explicitly approved

## Preflight Checks Required Before Actual GT7 Move

- `git status --short`
- exact approved file list for the batch
- `git ls-files` confirmation for every moved path
- `rg` scan for references to old paths
- confirmation that no source code files are included by mistake
- confirmation that GT7 handoff marker is not included accidentally

## Validation Required After Actual GT7 Move

- `git status --short`
- `git diff --stat`
- `python3 -m compileall -q runtime tests`
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -v`
- targeted `rg` scans for old paths such as `docs/adr/`, `reports/forensic_export/`, and selected root markdown names

## Recommended Next Step

After human review of this plan:

1. execute Batch 1 only
2. validate and commit that batch if approved
3. proceed to Batch 2 only after Batch 1 is clean
4. do not start Phase 1A Evidence Memory yet
5. do not build GUI/dashboard

## GT7 Start Safety

Actual GT7 physical cleanup is conditionally safe to start only after human review and only in small batches. It is not safe to execute as one large archive/move sweep.
