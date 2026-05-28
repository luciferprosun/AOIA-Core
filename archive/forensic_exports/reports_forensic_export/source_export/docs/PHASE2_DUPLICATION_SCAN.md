# Phase 2 Duplication Scan

Date: 2026-05-24
Phase: AOIA forensic migration

## Purpose

Check that Phase 2 did not create duplicate report trees, duplicate imported PDFs, runtime forks, or mixed case-study structures.

## PDF Duplication

Search result:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/archive/AOIA_MASTER_LIBRARY/AOIA_Master_Library.pdf`

Count:

- 1 copy inside `MHLM_MHSR/`

Decision:

- no duplicate PDF import detected.

## Report Duplication

No existing AOIA reports were copied into provider folders.

Provider folders contain `MANIFEST.md` files only. These are classification references, not duplicate report copies.

## Runtime Duplication

No runtime copy was created.

No new folders such as the following were created:

- `runtime_copy`
- `aoia_core_final_v2`
- `reports_final_v2`
- `archive_new`
- `prompts_new`
- `lineage_v2`

## Expected Mirrored Folders

Some repeated folder names are intentional because both case studies maintain separate structures:

- `prompts/`
- `reports/`
- `lineage/`
- `provenance/`
- `contradictions/`
- `archive/`

These are not duplicate structures because they exist under separate canonical case-study roots:

- `case_studies/lsc_neutrino/`
- `case_studies/anti_hallucination_epi_app/`

## Mixed-Case Legacy References

Active taxonomy uses:

- `lsc_neutrino`
- `LSC`

Remaining `LST` references inside `MHLM_MHSR/` are limited to:

- legacy alias mapping in taxonomy files
- unclassified manifest note about historical Phase 1 taxonomy

Historical Phase 1 reports outside `MHLM_MHSR/` were not rewritten.

## Reused Structures

Reused:

- `MHLM_MHSR/`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/`
- existing Phase 1 prompt/report/lineage/provenance/contradiction/archive folders

Created only missing provider and forensic subfolders.

## Result

No destructive duplication detected.

No abandoned temporary structures were left.
