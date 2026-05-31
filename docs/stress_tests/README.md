# Stress-Test Documentation for GT8 Reviewer Credibility Pass

This directory contains formalized documentation for the GT8 reviewer credibility pass.

## Purpose

AOIA-Core GT8 includes additional documentation to support reviewer validation and credibility assessment. These documents clarify that stress-test contexts and scientific case studies are not part of the AOIA-Core deliverable itself, but are documented for transparency and review.

## Files in This Directory

- **[AOIA_NMS_STRESS_TEST_PROTOCOL.md](AOIA_NMS_STRESS_TEST_PROTOCOL.md)**  
  Stress-test protocol for AOIA network management simulation under adverse conditions.

- **[FAILURE_MODES.md](FAILURE_MODES.md)**  
  Documented failure modes and recovery pathways for AOIA-Core runtime systems.

- **[LSC_CASE_STUDY_PROTOCOL.md](LSC_CASE_STUDY_PROTOCOL.md)**  
  Protocol for the LSC neutrino archive stress-test corpus: a high-claim-density
  research archive used only as stress-test material, not validated physics, not
  AOIA-Core scientific output, and not runtime authority.

- **[MODEL_AUDIT_MATRIX.md](MODEL_AUDIT_MATRIX.md)**  
  Audit matrix for model behavior validation against AOIA-Core governance contracts.

## Scope Clarification

### In Scope (AOIA-Core Deliverable)
- Local-first epistemic control runtime
- Evidence boundaries and provenance verification
- Contradiction tracking and governance contracts
- Deterministic operator workflows
- Runtime architecture and design

### Out of Scope (Stress-Test / Research Context)
- Stress-test execution results
- LSC case study outcomes
- NMS simulation data
- External model output validation results
- Long-term stress scenarios

## Validation Context

These documents formalize how reviewers can assess:
1. Governance contract adherence
2. Provenance integrity
3. Evidence memory boundaries
4. Contradiction registry correctness
5. Operator workflow determinism

They are not part of the runtime deliverable and should not affect AOIA-Core functionality.

## External Model Output Policy

See [docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md](../governance/EXTERNAL_MODEL_OUTPUT_POLICY.md) for policy on model-assisted documentation and audit packets.
