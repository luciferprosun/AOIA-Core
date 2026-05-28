# Evidence Policy

## Purpose

Define the minimum evidence boundaries for MHLM/MHSR Phase 1.

## Evidence Classes

- Raw evidence: source material preserved without interpretation.
- Normalized evidence: source material reformatted for review while preserving source meaning.
- Derived evidence: framework outputs based on raw or normalized evidence.
- Non-evidence: reasoning traces, assistant drafts, runtime state, temporary logs, and unverified summaries.

## Evidence Rules

- Raw evidence has priority over normalized or derived artifacts.
- Normalized artifacts must point back to raw artifacts.
- Derived artifacts must identify their input materials.
- Runtime state is operational context, not authority.
- Provider output is not automatically evidence unless its source and purpose are recorded.

## Reasoning Trace Boundary

Reasoning traces may support lineage review, but they are non-authoritative. They must not be promoted to evidence without an external source artifact.

## Future Requirements

Future phases should define content-addressed storage, append-only provenance records, and contradiction tracking before any large migration.
