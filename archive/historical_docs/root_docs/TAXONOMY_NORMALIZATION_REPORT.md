# Taxonomy Normalization Report

Date: 2026-05-24
Phase: 2 - AOIA forensic migration

## Objective

Normalize the active Phase 1 scientific case-study taxonomy:

- old transitional label: `lst` / `LST`
- new canonical label: `lsc_neutrino` / `LSC`

Historical report titles were not renamed.

## Changes Applied

Renamed active case-study folder:

- `MHLM_MHSR/case_studies/lst/`
- to `MHLM_MHSR/case_studies/lsc_neutrino/`

Updated active taxonomy/methodology files:

- `MHLM_MHSR/framework/taxonomy/case_studies.yml`
- `MHLM_MHSR/framework/taxonomy/model_aliases.yml`
- `MHLM_MHSR/framework/taxonomy/legacy_aliases.yml`
- `MHLM_MHSR/framework/methodology/inclusion_rules.md`
- `MHLM_MHSR/framework/methodology/lineage_policy.md`
- `MHLM_MHSR/framework/methodology/contradiction_policy.md`
- `MHLM_MHSR/case_studies/lsc_neutrino/README.md`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/README.md`

## Preserved Historical References

Phase 1 reports and earlier repository documentation may still mention `lst` or `LST` as historical state. Those files were not rewritten because they document what existed during Phase 1.

Preserved examples:

- `docs/PHASE1_STRUCTURE_REPORT.md`
- `docs/PHASE1_POSTCHECK.md`
- `docs/PHASE1_COMPLETE_REPORT.md`
- `docs/PRE_PHASE1_CONFLICT_SCAN.md`

## Canonical Active Taxonomy

Active scientific case-study ID:

- `lsc_neutrino`

Active scientific case-study label:

- `LSC`

Active AOIA engineering case-study ID:

- `anti_hallucination_epi_app`

## Separation Rule

`lsc_neutrino` and `anti_hallucination_epi_app` remain separate.

LSC scientific material must not be used as AOIA runtime/provenance evidence.

AOIA anti-hallucination engineering material must not be used as LSC scientific evidence.

## Notes

No runtime logic, provider configuration, routing logic, memory module, RHCSA corpus, or scientific report corpus was modified.
