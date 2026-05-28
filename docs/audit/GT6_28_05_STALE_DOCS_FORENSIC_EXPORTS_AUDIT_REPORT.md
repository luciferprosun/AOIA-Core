# GT6 28.05 Stale Docs / Forensic Exports Audit Report

Date: 2026-05-28
Repository: `/home/l/Desktop/AOIA-Core`
Canonical URL: `https://github.com/luciferprosun/AOIA-Core`
Audit mode: read-only

## Current Git State

- Current branch: `main`
- Current HEAD: `4ae93d67b0c467c00c1dd83e9db1b5842c172629`
- Latest commits:
  - `4ae93d6 fix: ignore generated runtime state`
  - `742555b checkpoint: deadline save1`
  - `ee6f64a docs: close Phase 0E provenance readout`
  - `b059fcc feat: add provenance integrity readout`
  - `4f2bffe feat: add provenance verification read-path`

Current `git status --short` during this audit:

```text
?? docs/audit/GT5_28_05_FINAL_COMMIT_PUSH_REPORT.md
```

This means the repository is not fully clean at audit time. The only pre-existing local drift observed in this audit is the untracked GT5 markdown report.

## Inventory Summary

The repository contains several distinct documentation and artifact classes:

- canonical doctrine and enforcement contracts
- historical stabilization and checkpoint reports
- stale or superseded planning documents
- forensic export bundles
- generated runtime state still present on disk
- duplicate authority sets under multiple documentation trees

Highest-risk zones for future Evidence Memory contamination:

- `runtime/logs/`
- `runtime/memory/*.jsonl`
- `runtime/obsidian_vault/`
- `runtime/state/*.json`
- `runtime/reports/`
- `reports/forensic_export/`

## Duplicate Authority Detection

Confirmed duplicate-authority patterns:

1. `docs/ADR/` versus `docs/adr/`
2. root-level AOIA architecture/planning markdowns versus `docs/` doctrine and stabilization reports
3. `runtime/reports/` versus `docs/stabilization/` and `docs/audit/`
4. `reports/forensic_export/source_export/*.md` versus root source markdowns

Risk consequence:

- the same topic appears in multiple places with different granularity, dates, and status assumptions
- future Evidence Memory or provenance consumers could misread historical or generated material as canonical authority

## docs/ADR vs docs/adr Analysis

This is the clearest documentation authority split in the repository.

Observed:

- `docs/ADR/ADR-001...ADR-005` defines a concise deterministic routing doctrine using `LOCAL`, `MID`, `PREMIUM` style concepts and current repository framing
- `docs/adr/0001...0005` is an older ADR line that includes isolation-era bootstrap decisions and at least one earlier router vocabulary using `shallow`, `mid`, `deep`

Assessment:

- `docs/ADR/` is the safer candidate for canonical status
- `docs/adr/` should be treated as historical or stale until a later archival phase explicitly resolves the split

Risk level: HIGH

## Stale-Doc Candidates

Strong stale candidates:

- `AOIA_CANONICAL_STRUCTURE_PLAN.md`
- `AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md`
- `AOIA_CONTAMINATION_REPORT.md`
- `AOIA_DEPENDENCY_GRAPH.md`
- `AOIA_ENVIRONMENT_AUDIT.md`
- `CURRENT_MEMORY_FLOW.md`
- `MEMORY_BOUNDARY_ANALYSIS.md`
- `MEMORY_LAYER_DECOMPOSITION.md`
- `MUTABLE_STATE_ISOLATION_PLAN.md`
- `ORCHESTRATION_REMNANT_AUDIT.md`
- `ROUTING_AUTHORITY_ANALYSIS.md`
- `docs/adr/*.md` where a newer equivalent exists under `docs/ADR/`

Reason:

- these documents are structural analysis/planning artifacts rather than current doctrine
- many predate GT2-GT5 stabilization and still describe pre-cleanup or transitional conditions
- several live at root level, which creates authority ambiguity

## Quarantine Candidates

Safe future quarantine/archive candidates if GT7 approves moves:

- `reports/forensic_export/**`
- `runtime/reports/*.md`
- `docs/forensic-runtime-audit/*.md`
- root-level contamination/planning markdowns that are not active doctrine
- any generated Obsidian material under `runtime/obsidian_vault/`

This audit does not move anything. It only marks these as likely non-canonical.

## reports/ Analysis

`reports/` currently mixes at least two roles:

- forensic export bundles under `reports/forensic_export/`
- Linux engineering audit notes under `reports/linux-engineering/`

Findings:

- `reports/forensic_export/` is not canonical project doctrine
- it contains exported snapshots, rendered PDFs/HTML, chunked markdown, manifests, and a duplicate `source_export/` copy of root markdown authority files
- this directory is a strong contamination source if used by future retrieval, memory, or evidence indexing

Recommended classification:

- `reports/forensic_export/**`: `external-model-output`
- `reports/linux-engineering/**`: `historical`

## archive/ Analysis

Observed:

- `archive/quarantine/README.md`

Assessment:

- `archive/quarantine/` is structurally correct as a containment zone
- current README matches a quarantine purpose and should not be treated as live runtime authority

Recommended classification:

- `archive/quarantine/README.md`: `quarantine`

## docs/audit/ Analysis

`docs/audit/` contains a mix of:

- GT checkpoint reports
- cleanup classification/plans
- web-informed master audits
- future compatibility notes
- RHCSA separation planning
- event ledger planning

Assessment:

- GT2-GT5 reports are historical, not canonical
- some planning docs are useful but should not outrank governance contracts
- `AOIA_CLEANUP_PHASE1_WEB_INFORMED_MASTER_REPORT.md` should be treated as `external-model-output` because it explicitly packages web-informed/model-mediated analysis

Risk:

- if `docs/audit/` is ingested blindly, Evidence Memory could treat planning opinions as canonical implementation truth

## Runtime Contamination Analysis

The repository still contains generated runtime material on disk even though GT3 removed it from source control and `.gitignore` now excludes it.

Observed generated-runtime zones:

- `runtime/logs/`
- `runtime/memory/evidence_memory.jsonl`
- `runtime/memory/history.jsonl`
- `runtime/memory/reasoning_trace.jsonl`
- `runtime/memory/hats/*.json`
- `runtime/obsidian_vault/`
- `runtime/state/*.json`
- `runtime/project_scan.json`
- `runtime/contradiction_registry.json`

Risk:

- these artifacts are runtime outputs, not canonical evidence or doctrine
- several carry filenames such as `Evidence`, `Reasoning`, `Sessions`, `state`, and `report`, which makes accidental authority promotion likely

## runtime/obsidian_vault Analysis

`runtime/obsidian_vault/` is a high-risk derived-view zone.

Observed contents:

- `Evidence/`
- `Reasoning/`
- `Sessions/`
- `Daily/`
- `.obsidian/app.json`

Assessment:

- this is not canonical evidence storage
- it is a projection layer generated from runtime activity
- the naming strongly risks confusion with true evidence/provenance artifacts

Risk level: HIGH

Recommended classification:

- all of `runtime/obsidian_vault/**`: `generated-runtime`

## Generated-Runtime Analysis

Generated-runtime material identified in this audit:

- runtime logs
- runtime memory JSONL files
- runtime state JSON files
- runtime screenshots directory
- runtime Obsidian vault
- runtime scan outputs and registries generated during operations
- runtime-generated reports

These must stay outside any future canonical evidence or retrieval authority set.

## External-Model-Output Analysis

Likely `external-model-output` or equivalent derived-output zones:

- `reports/forensic_export/**`
- `docs/audit/AOIA_CLEANUP_PHASE1_WEB_INFORMED_MASTER_REPORT.md`
- rendered PDFs/HTML under `docs/reports/` where they summarize prior analysis rather than enforce doctrine

Why:

- these artifacts are audit/render/export products
- they are suitable for review, sharing, or reproducibility
- they should not be treated as first-class runtime authority

## Root-Level Markdown Authority Analysis

Root markdown authority is currently too broad.

Root-level markdown set includes:

- doctrine-like documents such as `AUTHORITY_SCOPE.md`, `PROVENANCE_FOUNDATION.md`
- structural maps such as `AOIA_RUNTIME_MAP.md`
- planning docs such as `AOIA_CANONICAL_STRUCTURE_PLAN.md`
- contamination and decomposition audits such as `AOIA_CONTAMINATION_REPORT.md`, `MEMORY_LAYER_DECOMPOSITION.md`

Assessment:

- root contains both potentially canonical and clearly historical/planning material
- this creates a strong authority ambiguity for new reviewers and for any future automated document consumer

Highest-risk root conflicts:

- `README.md` versus multiple root maps/plans
- `AUTHORITY_SCOPE.md` versus broader historical analyses
- `PROVENANCE_FOUNDATION.md` versus later governance contracts under `docs/governance/`
- `AOIA_RUNTIME_MAP.md` versus later GT2-GT5 stabilization reports

## Recommended Canonical Docs

Safest current canonical documentation set:

- `README.md`
- `ROADMAP.md`
- `AUTHORITY_SCOPE.md`
- `docs/governance/EVIDENCE_WRITE_CONTRACT.md`
- `docs/governance/APPEND_ONLY_PROVENANCE_CONTRACT.md`
- `docs/governance/PROVENANCE_VERIFICATION_CONTRACT.md`
- `docs/governance/GOVERNANCE_IMPLEMENTATION_STATUS.md`
- `docs/governance/TEST_ENVIRONMENT_POLICY.md`
- `docs/ADR/ADR-001-deterministic-routing.md`
- `docs/ADR/ADR-002-three-depth-model.md`
- `docs/ADR/ADR-003-local-first-execution.md`
- `docs/ADR/ADR-004-no-runtime-learning.md`
- `docs/ADR/ADR-005-fail-fast-philosophy.md`
- `docs/stabilization/PHASE_0E_CLOSURE_REPORT.md`

These are the strongest candidates for authoritative review without mixing in forensic exports or planning drift.

## Files Requiring Manual Review

Priority manual-review set:

- `docs/adr/0001-keep-aoia-isolated.md`
- `docs/adr/0002-minimal-deterministic-router-skeleton.md`
- `docs/adr/0003-immutable-startup-configuration.md`
- `docs/adr/0004-stdout-only-plain-text-logging.md`
- `docs/adr/0005-test-constitution-determinism-first.md`
- `AOIA_RUNTIME_MAP.md`
- `AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md`
- `PROVENANCE_FOUNDATION.md`
- `reports/forensic_export/forensic_full_snapshot.md`
- `runtime/reports/current_checkpoint_report.md`
- `runtime/contradiction_registry.json`
- `runtime/provenance_registry.json`

Reason:

- each of these could be mistaken for active authority or canonical state without additional labeling or relocation

## Contamination Risks

Main contamination risks for future Evidence Memory:

1. runtime-derived artifacts with names suggesting evidence or session truth
2. forensic exports duplicating source markdowns under review-oriented paths
3. duplicate ADR trees with conflicting temporal assumptions
4. root-level planning documents sitting beside core doctrine
5. runtime reports and audit reports being confused with implementation contracts

## GT7 Readiness Assessment

GT7 appears ready only for controlled move/archive/quarantine work.

Conditions satisfied:

- enough duplicate-authority zones are now clearly identified
- the major generated-runtime contamination zones are explicit
- canonical candidates can be named without changing source logic

Conditions not yet satisfied:

- no move/delete/archive action should happen automatically without a precise canonical map
- root-level markdown authority still needs a human-approved keep/move decision set
- `docs/ADR` versus `docs/adr` must be resolved deliberately

Readiness verdict: CONDITIONAL YES

## Recommended Next Step

Proceed to a tightly scoped GT7 that does only file classification and relocation:

- move stale and historical docs out of root
- quarantine forensic exports and runtime reports
- resolve `docs/ADR` vs `docs/adr`
- keep governance contracts and stabilization closure docs in clearly canonical locations

Do not combine GT7 with Evidence Memory, provenance, contradiction registry, GUI, or runtime behavior changes.
