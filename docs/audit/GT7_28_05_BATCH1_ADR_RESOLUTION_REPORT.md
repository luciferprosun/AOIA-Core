# GT7 28.05 Batch 1 ADR Resolution Report

Date: 2026-05-28

## Branch

- `main`

## HEAD Before Batch

- `84fd877d80cdd1c70456e4889efb9936d084becf`

## Git Status Before

```text
?? docs/audit/GT7_28_05_HANDOFF_REPORT.md
?? docs/audit/GT7_28_05_PLAN_COMMIT_PUSH_FINAL_REPORT.md
```

No tracked modifications were present before Batch 1.

## Scope

Batch 1 scope was limited to resolving the duplicate ADR authority split:

- canonical ADR tree kept at `docs/ADR/`
- legacy lowercase ADR tree moved from `docs/adr/` to `docs/historical/adr_legacy/`

No source code, runtime architecture, provenance implementation, Evidence Memory, Contradiction Registry, RHCSA/RHP/Linux knowledge assets, tests, scripts, runtime reports, runtime state, forensic exports, or root markdown files were moved or modified.

## Files Moved

All moves are exact `R100` renames with no content edits:

- `docs/adr/0001-keep-aoia-isolated.md` -> `docs/historical/adr_legacy/0001-keep-aoia-isolated.md`
- `docs/adr/0002-minimal-deterministic-router-skeleton.md` -> `docs/historical/adr_legacy/0002-minimal-deterministic-router-skeleton.md`
- `docs/adr/0003-immutable-startup-configuration.md` -> `docs/historical/adr_legacy/0003-immutable-startup-configuration.md`
- `docs/adr/0004-stdout-only-plain-text-logging.md` -> `docs/historical/adr_legacy/0004-stdout-only-plain-text-logging.md`
- `docs/adr/0005-test-constitution-determinism-first.md` -> `docs/historical/adr_legacy/0005-test-constitution-determinism-first.md`
- `docs/adr/README.md` -> `docs/historical/adr_legacy/README.md`

## Old Path

- `docs/adr/`

## New Path

- `docs/historical/adr_legacy/`

## References Found Before

Preflight reference scan found lowercase `docs/adr` references in:

- historical docs under `docs/`
- audit inventories and GT planning reports under `docs/audit/`
- root historical/planning markdown files
- forensic export snapshots under `reports/forensic_export/`

No source code reference to `docs/adr` was found under `runtime/`, `tests/`, or `scripts/`.

## References Remaining After

Post-move scan still finds references to the old lowercase string because historical reports and inventories preserve old paths:

- total files containing `docs/adr`: `30`
- files containing `docs/adr` excluding `reports/forensic_export/`: `19`
- source/runtime/test/script references: `0`

Remaining non-forensic references are in historical/planning/audit files only:

- `AOIA_CANONICAL_STRUCTURE_PLAN.md`
- `AOIA_CONTAMINATION_REPORT.md`
- `AOIA_TRANSITIONAL_COMPONENTS.md`
- `docs/PHASE1_COMPLETE_REPORT.md`
- `docs/PHASE1_POSTCHECK.md`
- `docs/PRE_PHASE1_CONFLICT_SCAN.md`
- `docs/REPOSITORY_STATE_REPORT.md`
- `docs/REPO_STRUCTURE.md`
- `docs/TRANSFER_CONTENT_REPORT.txt`
- `docs/audit/AOIA_CLEANUP_CLASSIFICATION.md`
- `docs/audit/AOIA_CLEANUP_EXECUTION_SEQUENCE.md`
- `docs/audit/GT6B_28_05_FULL_FILE_MANIFEST_AUDIT_REPORT.md`
- `docs/audit/GT6B_28_05_FULL_FILE_MANIFEST_INVENTORY.csv`
- `docs/audit/GT6B_28_05_FULL_FILE_MANIFEST_INVENTORY.json`
- `docs/audit/GT6_28_05_DOCUMENT_AUTHORITY_INVENTORY.json`
- `docs/audit/GT6_28_05_STALE_DOCS_FORENSIC_EXPORTS_AUDIT_REPORT.md`
- `docs/audit/GT7_28_05_CONTROLLED_CLEANUP_PLAN.md`
- `docs/audit/GT7_28_05_PLAN_COMMIT_PUSH_FINAL_REPORT.md`
- `docs/audit/GT7_28_05_PROPOSED_MOVE_MAP.json`

These were not rewritten in Batch 1 because they are historical records, GT planning artifacts, or audit inventories. Forensic export snapshots were intentionally not edited.

## Canonical ADR Status

- `docs/ADR/` remains canonical: yes
- `docs/ADR/` files moved or modified: no

Canonical files still present:

- `docs/ADR/ADR-001-deterministic-routing.md`
- `docs/ADR/ADR-002-three-depth-model.md`
- `docs/ADR/ADR-003-local-first-execution.md`
- `docs/ADR/ADR-004-no-runtime-learning.md`
- `docs/ADR/ADR-005-fail-fast-philosophy.md`

## Lowercase ADR Directory Status

- `docs/adr/` files moved: yes
- empty `docs/adr/` directory removed: yes

## Validation Results

- `python3 -m compileall -q runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -v`: PASS
- Tests run: `145`
- Skipped: `4`

Known optional skips:

- Playwright-dependent browser tests
- `textual`-dependent TUI tests

## Unexpected Change Check

No unexpected source/runtime/provenance/Evidence Memory/Contradiction/RHCSA files changed.

`git diff --cached --name-status` contains only the six ADR renames listed above.

## Batch 1 Commit Safety

Batch 1 is safe to commit after human review.

## Recommended Commit Command

Do not run automatically in this step.

```bash
git add docs/audit/GT7_28_05_BATCH1_ADR_RESOLUTION_REPORT.md
git commit -m "docs: archive legacy lowercase ADR tree"
```

## Recommended Push Command

Do not run automatically in this step.

```bash
git push origin main
```

## Recommended Next Step

Perform `GT7 Batch 1 commit/push only` if the staged ADR renames and this report are accepted.

Do not start GT7 Batch 2 yet.
Do not start Phase 1A Evidence Memory yet.
