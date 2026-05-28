# GT7 28.05 Batch 2 Root Stale Markdown Relocation Report

Date: 2026-05-28

## Scope

GT7 Batch 2 relocated only approved stale/historical root-level planning markdown files to:

`archive/historical_planning/root/`

No source code, runtime architecture, provenance implementation, Evidence Memory, Contradiction Registry, RHCSA/RHP/Linux knowledge assets, tests, scripts, runtime reports, runtime state, docs/governance, or docs/ADR files were modified.

## Branch

- main

## HEAD Before Batch

- 3dfe8445c5d7932061d6b38a39fb50e3f59fa3fc
- docs: archive legacy lowercase ADR tree

## Git Status Before

Only known local handoff/status artifacts were present:

- `?? docs/audit/GT7_28_05_BATCH1_COMMIT_PUSH_FINAL_REPORT.md`
- `?? docs/audit/GT7_28_05_HANDOFF_REPORT.md`
- `?? docs/audit/GT7_28_05_PLAN_COMMIT_PUSH_FINAL_REPORT.md`

## Root Markdown Files Before

- AOIA_CANONICAL_STRUCTURE_PLAN.md
- AOIA_CONTAMINATION_REPORT.md
- AOIA_DEPENDENCY_GRAPH.md
- AOIA_ENVIRONMENT_AUDIT.md
- AOIA_MEMORY_ONTOLOGY.md
- AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md
- AOIA_RUNTIME_MAP.md
- AOIA_TRANSITIONAL_COMPONENTS.md
- AUTHORITY_SCOPE.md
- CONTRADICTION_SEMANTICS.md
- CURRENT_MEMORY_FLOW.md
- FILESYSTEM_ONTOLOGY_LAYOUT.md
- MEMORY_BOUNDARY_ANALYSIS.md
- MEMORY_LAYER_DECOMPOSITION.md
- MUTABLE_STATE_ISOLATION_PLAN.md
- ORCHESTRATION_REMNANT_AUDIT.md
- PROVENANCE_FOUNDATION.md
- README.md
- ROADMAP.md
- ROUTING_AUTHORITY_ANALYSIS.md

## Files Moved

Target path:

`archive/historical_planning/root/`

Moved files:

- `AOIA_CANONICAL_STRUCTURE_PLAN.md` -> `archive/historical_planning/root/AOIA_CANONICAL_STRUCTURE_PLAN.md`
- `AOIA_CONTAMINATION_REPORT.md` -> `archive/historical_planning/root/AOIA_CONTAMINATION_REPORT.md`
- `AOIA_DEPENDENCY_GRAPH.md` -> `archive/historical_planning/root/AOIA_DEPENDENCY_GRAPH.md`
- `AOIA_ENVIRONMENT_AUDIT.md` -> `archive/historical_planning/root/AOIA_ENVIRONMENT_AUDIT.md`
- `AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md` -> `archive/historical_planning/root/AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md`
- `AOIA_TRANSITIONAL_COMPONENTS.md` -> `archive/historical_planning/root/AOIA_TRANSITIONAL_COMPONENTS.md`
- `CURRENT_MEMORY_FLOW.md` -> `archive/historical_planning/root/CURRENT_MEMORY_FLOW.md`
- `MEMORY_BOUNDARY_ANALYSIS.md` -> `archive/historical_planning/root/MEMORY_BOUNDARY_ANALYSIS.md`
- `MEMORY_LAYER_DECOMPOSITION.md` -> `archive/historical_planning/root/MEMORY_LAYER_DECOMPOSITION.md`
- `MUTABLE_STATE_ISOLATION_PLAN.md` -> `archive/historical_planning/root/MUTABLE_STATE_ISOLATION_PLAN.md`
- `ORCHESTRATION_REMNANT_AUDIT.md` -> `archive/historical_planning/root/ORCHESTRATION_REMNANT_AUDIT.md`
- `ROUTING_AUTHORITY_ANALYSIS.md` -> `archive/historical_planning/root/ROUTING_AUTHORITY_ANALYSIS.md`

## Root Markdown Files After

- AOIA_MEMORY_ONTOLOGY.md
- AOIA_RUNTIME_MAP.md
- AUTHORITY_SCOPE.md
- CONTRADICTION_SEMANTICS.md
- FILESYSTEM_ONTOLOGY_LAYOUT.md
- PROVENANCE_FOUNDATION.md
- README.md
- ROADMAP.md

## References Found Before

References to approved moved filenames existed in documentation, audit inventory, historical reports, forensic/export snapshots, and report manifests.

No references were found in:

- runtime/
- tests/
- scripts/

Source/runtime/test/script reference scan result:

- PASS: no source/runtime/test/script references to the approved root markdown filenames were found.

## References Remaining After

Filename references remain in historical/audit/report/forensic material and in the moved files themselves. These were not edited because they are historical or audit records.

Remaining reference counts after relocation:

- AOIA_CANONICAL_STRUCTURE_PLAN.md: 18
- AOIA_CONTAMINATION_REPORT.md: 23
- AOIA_DEPENDENCY_GRAPH.md: 21
- AOIA_ENVIRONMENT_AUDIT.md: 7
- AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md: 17
- AOIA_TRANSITIONAL_COMPONENTS.md: 17
- CURRENT_MEMORY_FLOW.md: 19
- MEMORY_BOUNDARY_ANALYSIS.md: 17
- MEMORY_LAYER_DECOMPOSITION.md: 17
- MUTABLE_STATE_ISOLATION_PLAN.md: 17
- ORCHESTRATION_REMNANT_AUDIT.md: 19
- ROUTING_AUTHORITY_ANALYSIS.md: 21

Post-move source/runtime/test/script reference scan:

- PASS: no source/runtime/test/script references were found.

## Validation Results

- `python3 -m compileall -q runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -v`: PASS
- Tests run: 145
- Skipped: 4

## Forbidden Change Check

No staged changes were found under:

- runtime/
- tests/
- scripts/
- docs/governance/
- docs/ADR/

No source/runtime/provenance/Evidence Memory/Contradiction/RHCSA/test/script files were changed.

## Batch 2 Commit Safety

Batch 2 is safe to commit after human review.

Expected commit contents:

- 12 root stale/historical planning markdown renames into `archive/historical_planning/root/`
- this Batch 2 report

Known local handoff/status artifacts should remain uncommitted unless explicitly approved:

- `docs/audit/GT7_28_05_HANDOFF_REPORT.md`
- `docs/audit/GT7_28_05_PLAN_COMMIT_PUSH_FINAL_REPORT.md`
- `docs/audit/GT7_28_05_BATCH1_COMMIT_PUSH_FINAL_REPORT.md`

## Recommended Commit Command

Do not run automatically:

```bash
git add docs/audit/GT7_28_05_BATCH2_ROOT_STALE_MARKDOWN_RELOCATION_REPORT.md
git commit -m "docs: archive stale root planning reports"
```

The 12 renames are already staged by `git mv`.

## Recommended Push Command

Do not run automatically:

```bash
git push origin main
```

## Recommended Next Step

GT7 Batch 2 commit/push only if clean.

Do not start GT7 Batch 3 yet.
Do not start Phase 1A Evidence Memory yet.
