# Contradiction Taxonomy

Phase: 3 - governance preparation
Status: taxonomy only

## Source Contradictions

Different source artifacts disagree.

Example classes:

- provider audit conflict
- report vs source mismatch
- raw vs normalized mismatch

## Temporal Contradictions

A later artifact conflicts with an earlier artifact.

Review question:

- did the system change, or did interpretation change?

## Logical Contradictions

Two claims cannot both be true under the same assumptions.

Review question:

- are assumptions explicit and shared?

## Confidence Contradictions

Confidence labels conflict with evidence strength.

Example:

- high-confidence claim with weak provenance
- low-confidence claim with strong source grounding

## Provenance Contradictions

Artifact source, provider, timestamp, or derivation chain conflicts.

These should be treated as high-risk because provenance is the safety boundary.

## Runtime Contradictions

Observed runtime behavior conflicts with documented architecture or policy.

Runtime contradictions require code-level verification in a future phase.

## Severity Concepts

- low: documentation inconsistency with no authority effect
- medium: ambiguity affecting classification or interpretation
- high: contradiction affecting provenance, evidence, or domain separation
- critical: contradiction allowing cross-domain contamination or evidence promotion

## Review Concepts

Contradiction review should record:

- affected artifacts
- contradiction type
- severity
- case-study scope
- reviewer
- status

## Quarantine Concepts

Quarantine is required when a contradiction could cross:

- LSC/AOIA boundary
- evidence/reasoning boundary
- runtime/archive boundary
- source/derived boundary

## No Auto-Resolution

No contradiction is resolved by:

- model agreement
- majority vote
- runtime state
- cleanup preference
- naming convention
