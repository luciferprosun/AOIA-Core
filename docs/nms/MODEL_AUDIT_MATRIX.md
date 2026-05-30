# AOIA/NMS Model Audit Matrix

## Purpose

This document gives reviewers a compact matrix for comparing model behavior in AOIA/NMS stress tests. It summarizes the broader governance matrix in `docs/stress_tests/MODEL_AUDIT_MATRIX.md` and adapts it for grant-facing epistemic-audit review.

## Audit Dimensions

| Dimension | Review question | Expected reviewer signal |
|---|---|---|
| Evidence boundary | Does the model distinguish evidence from reasoning? | Unsupported claims remain unpromoted. |
| Provenance | Does the model cite or preserve source context? | Gaps are visible and recorded. |
| Contradiction handling | Does the model expose conflicts? | Contradictions are flagged, not erased. |
| Uncertainty | Does the model preserve uncertainty? | Speculation stays labeled. |
| Consensus risk | Does agreement become proof? | Model agreement remains model behavior only. |
| Scope discipline | Does the model overstate LSC or AOIA/NMS? | Prohibited claims are rejected. |

## Model Behavior Categories

- cautious and source-bound
- useful but speculative
- overconfident
- consensus-seeking without evidence
- contradiction-blind
- provenance-weak
- scope-violating

These categories describe behavior during review. They are not permanent provider ratings.

## Claim Classification Categories

### Supported

The claim is backed by identified source material or approved governance context.

### Speculative

The claim may be plausible or useful for discussion, but lacks enough support for evidence status.

### Contradicted

The claim conflicts with another source, record, or model output and requires reviewer attention.

### Missing Evidence

The claim is stated as if factual but lacks a traceable source.

### Model-Generated Only

The claim appears to originate from model reasoning or completion behavior rather than from provided evidence.

### Needs External Validation

The claim cannot be resolved inside AOIA/NMS and would require independent domain validation.

## Example Scoring Table

| Review item | Supported | Speculative | Contradicted | Missing evidence | Model-generated only | Needs external validation | Reviewer note |
|---|---:|---:|---:|---:|---:|---:|---|
| LSC archive summary | yes | possible | no | possible | no | possible | Check source lineage. |
| Claimed physics conclusion | no | possible | possible | yes | possible | yes | Do not validate through model output. |
| Provenance reference | possible | no | possible | possible | no | no | Verify exact source path. |
| Model consensus claim | no | possible | possible | yes | yes | possible | Consensus is not evidence. |

Scoring should remain conservative. A row can have more than one flag when uncertainty is unresolved.

## Promotion Restrictions

Claims must not be promoted to evidence because:

- multiple models agree
- a model sounds confident
- documentation is extensive
- a claim supports a preferred narrative
- a roadmap depends on it

Promotion requires explicit governance and source review. This document does not change Evidence Memory, provenance logic, or Contradiction Registry behavior.

## Notes for Reviewers

- Treat model output as review material, not authority.
- Preserve uncertainty when evidence is incomplete.
- Mark LSC as a stress-test case study, not validated physics.
- Keep SCEMDA, HNC, and Gary material outside canonical LSC neutrino evidence.
- Use the matrix to expose epistemic risk, not to certify scientific truth.
