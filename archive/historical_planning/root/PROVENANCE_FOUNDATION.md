# Provenance Foundation

Date: 2026-05-23
Phase: Memory Ontology Foundation

## Purpose

Provenance is the identity layer that makes evidence replayable and contradictions meaningful.

Without provenance:
- evidence cannot be trusted structurally
- contradiction sources cannot be traced
- retrieval cannot be replayed deterministically

## Source Identity

A provenance object should identify:
- artifact path
- artifact type
- metadata
- internal references
- command count where relevant
- content fingerprint
- generation timestamp or version epoch

Current AOIA basis:
- `runtime/provenance_registry.json`

## Retrieval Metadata

Required metadata classes:
- retrieval path used
- topic filter used
- matching score
- confidence context
- result rank

Current AOIA gap:
- retrieval metadata is produced at runtime but not formalized as a dedicated provenance event layer

## Evidence Fingerprints

Every evidence object should carry:
- content hash or equivalent fingerprint
- source reference
- capture timestamp
- source type

Rule:
- no evidence without fingerprint or source linkage should be treated as canonical evidence

## Trust Versioning

Recommended trust versioning principles:
- provenance schema version
- source snapshot version
- retrieval logic version
- contradiction policy version when relevant

Purpose:
- allow replay to distinguish source change from retrieval change

## Append-Only Lineage

Provenance history should be append-only at the record level.

Allowed:
- new source snapshots
- new fingerprints
- supersession markers

Not allowed:
- silent replacement of prior source identity records

## Replay Compatibility

Replay should be able to answer:
- what artifact was used
- what exact fingerprint it had
- what references it exposed
- which evidence objects were derived from it
- which contradictions were associated with it

## Relationship to Other Layers

- L3 provenance constrains L4 evidence identity
- L3 provenance anchors L5 contradiction sources
- L3 provenance must outrank L2 reasoning in structural authority

## Current AOIA Judgment

AOIA already has a viable provenance seed:
- artifact identity
- metadata
- references
- content hashes

What is still missing:
- formal replay versioning
- explicit evidence object linkage
- append-only provenance evolution semantics across knowledge rebuilds
