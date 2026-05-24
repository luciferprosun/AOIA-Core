# Phase 1 Structure Report

Date: 2026-05-24
Repository: `/home/l/Desktop/AOIA-Core`
Phase: MHLM/MHSR Phase 1 framework skeleton initialization

## Scope

This phase initialized the MHLM/MHSR skeleton only.

No runtime refactor was performed.
No AOIA runtime files were moved.
No provider configs were modified.
No routing logic was modified.
No prompt/report migration was performed.

## Created Root

Created one isolated framework root:

- `MHLM_MHSR/`

This avoids creating parallel AOIA runtime folders, runtime copies, duplicate docs roots, or mixed LST/AOIA folders.

## Created Folders

Framework:

- `MHLM_MHSR/framework/`
- `MHLM_MHSR/framework/methodology/`
- `MHLM_MHSR/framework/schemas/`
- `MHLM_MHSR/framework/taxonomy/`
- `MHLM_MHSR/framework/governance/`

Case studies:

- `MHLM_MHSR/case_studies/lst/`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/`

Imports:

- `MHLM_MHSR/imports/provider_exports/raw/`
- `MHLM_MHSR/imports/provider_exports/normalized/`
- `MHLM_MHSR/imports/repo_snapshots/`
- `MHLM_MHSR/imports/git_bundles/`

Framework docs:

- `MHLM_MHSR/docs/`

Per-case migration targets were created for both `lst` and `anti_hallucination_epi_app`:

- `prompts/raw/`
- `prompts/normalized/`
- `reports/raw_provider/`
- `reports/normalized/`
- `reports/synthesis/`
- `lineage/sessions/`
- `lineage/events/`
- `lineage/decisions/`
- `provenance/`
- `contradictions/`
- `archive/`

## Created Files

Methodology:

- `MHLM_MHSR/framework/methodology/inclusion_rules.md`
- `MHLM_MHSR/framework/methodology/evidence_policy.md`
- `MHLM_MHSR/framework/methodology/lineage_policy.md`
- `MHLM_MHSR/framework/methodology/contradiction_policy.md`

Schemas:

- `MHLM_MHSR/framework/schemas/artifact.schema.json`
- `MHLM_MHSR/framework/schemas/lineage_event.schema.json`
- `MHLM_MHSR/framework/schemas/report.schema.json`
- `MHLM_MHSR/framework/schemas/provenance_record.schema.json`
- `MHLM_MHSR/framework/schemas/case_study_manifest.schema.json`

Taxonomy:

- `MHLM_MHSR/framework/taxonomy/case_studies.yml`
- `MHLM_MHSR/framework/taxonomy/model_aliases.yml`
- `MHLM_MHSR/framework/taxonomy/legacy_aliases.yml`

Case studies:

- `MHLM_MHSR/case_studies/lst/README.md`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/README.md`

Reports:

- `docs/PRE_PHASE1_CONFLICT_SCAN.md`
- `docs/PHASE1_STRUCTURE_REPORT.md`

## Naming Conventions

Canonical root:

- `MHLM_MHSR`

Canonical case study IDs:

- `lst`
- `anti_hallucination_epi_app`

Canonical framework subfolders:

- `framework`
- `case_studies`
- `imports`
- `docs`

Canonical artifact flow labels:

- `raw`
- `normalized`
- `derived`
- `synthesis`

## Canonical Case Study Separation Rules

LST/LSC case:

- reserved for scientific reasoning, neutrino anomaly material, LSC/LST lineage, and related research artifacts.
- not evidence for AOIA engineering claims.

AOIA case:

- reserved for anti-hallucination engineering, deterministic runtime, provenance, retrieval boundaries, and AOIA lineage.
- not evidence for LST/LSC scientific claims.

Cross-case references:

- may be documented in future phases only with explicit provenance and no evidential auto-promotion.

## Provenance Contamination Warnings

- Raw provider exports must remain separate from normalized and derived materials.
- Reasoning traces are non-authoritative unless tied to external evidence by future policy.
- Runtime state must not become canonical authority.
- AOIA runtime reports must not be migrated into LST by default.
- LST scientific artifacts must not be used as AOIA runtime validation by default.
- Contradictions must be preserved and not auto-resolved.

## Stop Condition

Phase 1 stopped after skeleton initialization and reports.

No migrations were started.
