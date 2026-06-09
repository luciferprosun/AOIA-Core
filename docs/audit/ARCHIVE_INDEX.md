# AOIA-Core docs/audit Archive Index

This index is a cleanup manifest for docs/audit. It does not delete, move, or deprecate files by itself. It classifies audit documents so later framework cleanup can reduce documentation overload without losing traceability.

## 1. Purpose

This file classifies the `docs/audit/` surface for later controlled cleanup.

It exists to answer:

- which audit files should stay visible during framework cleanup
- which files are current safety references
- which files are historical checkpoint evidence
- which files are model-review artifacts
- which files are future planning
- which files can later move to an archive area after human review

## 2. Current docs/audit Problem

126 docs/audit files were found in the framework cleanup inventory.

Current inspection also found 126 top-level files directly under `docs/audit/`, plus additional nested files under `docs/audit/model_audit_archive/`.

The main overload is not one bad file. The problem is accumulation:

- current safety references sit beside large amounts of historical checkpoint history
- model review artifacts sit beside active reviewer-facing references
- future-planning documents sit beside current blocker material
- embedded PDFs, inventories, and export artifacts increase visual noise

## 3. Keep Visible During Cleanup

The following should remain visible during cleanup:

- `RED_1_BLOCKER_REGISTER.md` — `KEEP_VISIBLE`
- `ARCHIVE_INDEX.md` — `KEEP_VISIBLE`
- `AOIA_CORE_BOUNDARY_STATEMENT.md` — `KEEP_VISIBLE`
- `M0_A_PROVIDER_SECURITY_POLICY.md` — `KEEP_VISIBLE`
- `M0_B_MODEL_ROUTER_DECISION_RECORD.md` — `KEEP_VISIBLE`
- `M1_CONTROLLED_MODEL_ROUTER_FINAL_CHECKPOINT.md` — `KEEP_VISIBLE`
- `M1_ROUTER_CONTROLLED_MODEL_ROUTER_REVIEWER_NOTE.md` — `KEEP_VISIBLE`
- `REVIEWER_AUDIT_TRAIL_ENTRY_POINT.md` — `KEEP_VISIBLE`

These are the clearest current bridge documents between blocker status, runtime boundary claims, and reviewer navigation.

## 4. RED-1 Current Safety References

Current RED-1 safety references are narrow.

- `RED_1_BLOCKER_REGISTER.md` — `KEEP_CURRENT_SAFETY`

Supporting but not RED-1-specific current-safety context:

- `AOIA_CORE_BOUNDARY_STATEMENT.md` — `KEEP_CURRENT_SAFETY`
- `M0_A_PROVIDER_SECURITY_POLICY.md` — `KEEP_CURRENT_SAFETY`
- `M0_B_MODEL_ROUTER_DECISION_RECORD.md` — `KEEP_CURRENT_SAFETY`
- `M1_CONTROLLED_MODEL_ROUTER_FINAL_CHECKPOINT.md` — `KEEP_CURRENT_SAFETY`

Only `RED_1_BLOCKER_REGISTER.md` is clearly the primary RED-1 current safety reference.

## 5. Historical Checkpoint Reports

The following groups are primarily historical checkpoint material and should be treated as `ARCHIVE_LATER` after human review:

- `GT_RUNTIME_*` checkpoint reports and validation summaries — `ARCHIVE_LATER`
- `GT*_28_05_*` and similar dated GT closure/checkpoint reports — `ARCHIVE_LATER`
- `GT_HAT_*` memory-hats milestone reports — `ARCHIVE_LATER`
- `H12_*` through `H22_*` dated batch reports — `ARCHIVE_LATER`
- `M1_*` router checkpoint reports — `ARCHIVE_LATER` after a later consolidated release note exists
- `AIOA_WHITEHAT_STABLE_CHECKPOINT_*` and `NLNET_*CHECKPOINT*` reports — `ARCHIVE_LATER`
- `RED_*` intermediate checkpoint material, if added later — `REVIEW_LATER` first, then `ARCHIVE_LATER`

These files are evidence history, but they should not dominate the visible framework surface.

## 6. External Model Review Artifacts

The following groups are model/external review evidence and should be classified as `MODEL_REVIEW_ARTIFACT`:

- `EXTERNAL_AUDIT_INTAKE_CLAUDE_SONNET_*` — `MODEL_REVIEW_ARTIFACT`
- `AOIA_CORE_FULL_REPOSITORY_SNAPSHOT_EXTERNAL_MODEL_AUDIT_*` — `MODEL_REVIEW_ARTIFACT`
- `AOIA_CORE_POST_GT_RUNTIME_6_EXTERNAL_AUDIT_BASELINE_*` including `.pdf` — `MODEL_REVIEW_ARTIFACT`
- `AOIA_CORE_RUNTIME_ARCHITECTURE_FOR_BASH_MODULE_REVIEW_*` including `.pdf` — `MODEL_REVIEW_ARTIFACT`
- `H17_EXTERNAL_REVIEW_CONSOLIDATION_REPORT.md` — `MODEL_REVIEW_ARTIFACT`
- nested `docs/audit/model_audit_archive/` materials — `MODEL_REVIEW_ARTIFACT`

Future external-model artifacts with patterns such as `CLAUDE*`, `GEMINI*`, `GROK*`, `KIMI*`, `META*`, `PERPLEXITY*`, `DEEPSEEK*`, or `SONNET*` should also be classified as `MODEL_REVIEW_ARTIFACT`.

## 7. Future / Planning Documents

The following groups are primarily future or planning material and should be classified as `FUTURE_PLANNING` unless they later become active blocker references:

- `CHAT4_*` helper-bot, proposal, or governance planning files — `FUTURE_PLANNING`
- `HAT_004_*` governance or inert-schema planning files — `FUTURE_PLANNING`
- `AOIA_FUTURE_COMPATIBILITY_NOTES.md` — `FUTURE_PLANNING`
- `AOIA_RHCSA_KNOWLEDGE_SEPARATION_PLAN.md` — `FUTURE_PLANNING`
- `AOIA_SINGLE_EVENT_LEDGER_PLAN.md` — `FUTURE_PLANNING`
- `GT7_28_05_CONTROLLED_CLEANUP_PLAN.md` and `GT7_28_05_PROPOSED_MOVE_MAP.json` — `FUTURE_PLANNING`

These files are useful planning history, but they should not be mistaken for current approved runtime behavior.

## 8. Archive-Later Candidates

The main archive-later candidates are:

- dated checkpoint reports with `GT_*`, `GT_RUNTIME_*`, `GT_HAT_*`, `H*`, `M1_*`, and `NLNET_*CHECKPOINT*` naming — `ARCHIVE_LATER`
- embedded PDFs and export-style inventory artifacts such as `.pdf`, `.csv`, and `.json` evidence bundles — `ARCHIVE_LATER`
- closure, savepoint, restart, and final-push notes that are historically useful but not current operational references — `ARCHIVE_LATER`
- duplicate reviewer-facing entry documents inside `docs/audit/` that overlap with canonical top-level docs — `REVIEW_LATER`
- model-review evidence that should remain traceable but not front-and-center — `MODEL_REVIEW_ARTIFACT`

These are candidates for later movement into a compressed archive area after human review.

## 9. Do-Not-Move-Yet Candidates

The following should not move until framework cleanup decisions are reviewed:

- `RED_1_BLOCKER_REGISTER.md` — `DO_NOT_MOVE_YET`
- `ARCHIVE_INDEX.md` — `DO_NOT_MOVE_YET`
- `AOIA_CORE_BOUNDARY_STATEMENT.md` — `DO_NOT_MOVE_YET`
- `M0_A_PROVIDER_SECURITY_POLICY.md` — `DO_NOT_MOVE_YET`
- `M0_B_MODEL_ROUTER_DECISION_RECORD.md` — `DO_NOT_MOVE_YET`
- `M1_CONTROLLED_MODEL_ROUTER_FINAL_CHECKPOINT.md` — `DO_NOT_MOVE_YET`
- `M1_ROUTER_CONTROLLED_MODEL_ROUTER_REVIEWER_NOTE.md` — `DO_NOT_MOVE_YET`
- any current safety boundary, blocker, or current-state bridge document in `docs/audit/` — `DO_NOT_MOVE_YET`

## 10. Next Cleanup Action

FRAMEWORK-CLEANUP-3 should move or compress only clearly historical docs/audit materials after this index is reviewed.

This index creates the classification boundary only. It does not archive or remove anything now.
