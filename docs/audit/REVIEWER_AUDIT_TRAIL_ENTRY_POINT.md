# Reviewer Audit Trail Entry Point

Date: 2026-06-05

Purpose: provide a single starting point for NLnet and external technical reviewers who need to inspect AOIA-Core audit history, reviewer-readiness evidence, MAHT methodology, and deferred decisions without reconstructing the trail from scattered repository documents.

## Review Scope

AOIA-Core should currently be reviewed as a local-first safety, audit, and pre-execution inspection layer.

It should not currently be reviewed as:

- an autonomous shell executor
- a production command runner
- a packaging-complete Python distribution
- GT-RUNTIME-9

## Read First

Start with these files:

1. `docs/audit/AOIA_CORE_BOUNDARY_STATEMENT.md`
2. `docs/audit/REVIEWER_QUICKSTART.md`
3. `docs/audit/GT_RUNTIME_8H_REVIEWER_READINESS_REPORT.md`
4. `docs/audit/NLNET_REVIEWER_EVIDENCE_PACK_STATUS_04_JUNE_2026.md`

These establish the current review boundary, the reviewer-facing quick path, the GT-RUNTIME-8H reviewer-readiness milestone, and the evidence-pack status immediately before the 05 June external audit archive.

## Audit History Path

For audit-history reconstruction, read in this order:

1. `docs/audit/AOIA_CORE_POST_GT_RUNTIME_6_EXTERNAL_AUDIT_BASELINE_02_JUNE_2026.md`
2. `docs/audit/H17_EXTERNAL_REVIEW_CONSOLIDATION_REPORT.md`
3. `docs/audit/AOIA_CORE_FULL_REPOSITORY_SNAPSHOT_EXTERNAL_MODEL_AUDIT_04_JUNE_2026.md`
4. `docs/audit/POST_FREEZE_51_COMMITS_SUMMARY_04_JUNE_2026.md`
5. `docs/audit/NLNET_FINAL_CLEANLINESS_CHECKPOINT_REPORT_04_JUNE_2026.md`

This path shows how the repository moved from external audit intake, through consolidation and repository-wide review, into freeze-era reviewer packaging and cleanliness decisions.

## External Audit Archive

The 05 June 2026 external audit archive is stored here:

- `docs/audit/external/2026-06-05/AOIA_Audit_Consensus_Report_05_June_2026.pdf`
- `docs/audit/external/2026-06-05/AOIA_Import_Layout_Repair_Audit_Series_v1_0_05_June_2026.pdf`
- `docs/audit/external/2026-06-05/AOIA_MAHT_v2_0_Methodology_Report.pdf`
- `docs/audit/external/2026-06-05/EXTERNAL_AUDIT_REGISTER.md`
- `docs/audit/external/2026-06-05/MAHT_OVERVIEW.md`

These files preserve how external-model hypotheses, convergence, disagreement, bounded experiments, and rejected or deferred implementation paths were handled during reviewer-readiness work.

## MAHT Interpretation

The MAHT-related materials should be interpreted as audit-process evidence, not as direct implementation authority.

Their role is to show:

- how external model outputs were treated as hypotheses
- how disagreement was preserved instead of hidden
- how bounded experiments were used to test disputed claims
- how failed or out-of-scope experiments were documented explicitly
- how commit decisions were gated by validation and scope control

## Deferred Decisions

The main deferred area visible in the 05 June archive is packaging and import-layout normalization.

Reviewers should treat this as:

- acknowledged technical debt
- explicitly audited rather than ignored
- not resolved by undocumented shortcuts
- deferred to a separate audited phase rather than mixed into reviewer-packaging claims

For the current deferred-decision framing, also see:

1. `docs/audit/GT_RUNTIME_9_RECOMMENDED_NEXT_STEPS.md`
2. `docs/audit/external/2026-06-05/AOIA_Import_Layout_Repair_Audit_Series_v1_0_05_June_2026.pdf`
3. `docs/audit/external/2026-06-05/MAHT_OVERVIEW.md`

## Evidence Anchors

If a reviewer wants the shortest evidence path for current claims, use:

1. `docs/audit/AOIA_CORE_BOUNDARY_STATEMENT.md`
2. `docs/audit/REVIEWER_QUICKSTART.md`
3. `docs/audit/GT_RUNTIME_8H_REVIEWER_READINESS_REPORT.md`
4. `docs/audit/NLNET_REVIEWER_EVIDENCE_PACK_STATUS_04_JUNE_2026.md`
5. `docs/audit/external/2026-06-05/EXTERNAL_AUDIT_REGISTER.md`

## Boundary Reminder

This entry point is documentation-only.

It does not change runtime behavior.
It does not implement packaging repair.
It does not start GT-RUNTIME-9.
