# Inclusion Rules

## Purpose

Define what may enter the MHLM/MHSR framework during future migration phases.

## Inclusion Classes

- Raw artifacts: original provider exports, repository snapshots, session exports, source documents, logs, or datasets copied without semantic rewriting.
- Normalized artifacts: raw artifacts converted into a consistent format while preserving source meaning and provenance.
- Derived artifacts: summaries, synthesis reports, taxonomic mappings, analysis notes, or framework conclusions produced from raw or normalized artifacts.

## Required Metadata

Every migrated artifact should identify:

- source path or source system
- original filename when available
- import date
- case study target
- artifact class: raw, normalized, or derived
- provenance record reference when available

## Case Study Separation

LSC scientific anomaly material must enter only the `lsc_neutrino` case study.

AOIA anti-hallucination engineering material must enter only the `anti_hallucination_epi_app` case study.

Cross-case references may be documented later, but they must not imply evidential dependence.

## Prohibitions

- Do not treat reasoning traces as evidence.
- Do not promote normalized artifacts above raw sources.
- Do not mix LSC evidence with AOIA runtime evidence.
- Do not import unclear artifacts without a quarantine or review note.
