# Contradiction Policy

## Purpose

Define how contradictions should be preserved without forcing premature resolution.

## Contradiction Rules

- Contradictions must be recorded, not erased.
- Contradictions must not be auto-resolved by runtime state or model output.
- Contradiction records should identify affected artifacts and case study scope.
- LSC contradictions and AOIA contradictions must remain separated unless explicitly cross-referenced.

## Evidence Boundary

A contradiction record is a review object. It is not automatically evidence and does not replace the source artifacts it references.

## Resolution Status

Allowed status values for future contradiction records:

- open
- under_review
- resolved_with_evidence
- rejected
- superseded

Phase 1 does not implement contradiction resolution.
