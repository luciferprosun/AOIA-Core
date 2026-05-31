# LSC Neutrino Archive Stress-Test Corpus Protocol

## Scope Declaration

This document describes use of the LSC neutrino archive as a high-claim-density
research archive used only as a stress-test corpus. It is **research context
documentation** and is **not** part of the AOIA-Core runtime deliverable,
validated physics, AOIA-Core scientific output, or runtime authority.

## LSC Definition

LSC is treated here as a neutrino archive stress-test corpus. It provides
complex, high-risk source material for checking whether AOIA-Core documentation
and review workflows keep claims, provenance, contradictions, and evidence status
separate.

## Case Study Objectives

1. Check that LSC remains framed as stress-test material only
2. Verify that model output is not treated as scientific validation
3. Confirm that provenance and evidence boundaries remain explicit
4. Surface unsupported or contradictory claims for human review
5. Prevent stress-test material from becoming runtime authority

## Test Environment

Case studies may be conducted in:
- Deterministic replay environments
- Local simulation with captured provider responses
- Isolated research environments
- NOT in production systems

## Validation Domains

### Domain 1: Scope Boundary
- LSC remains a stress-test corpus only
- LSC is not presented as validated physics
- LSC is not presented as AOIA-Core scientific output

### Domain 2: Governance Adherence
- All operations comply with governance contracts
- ADR decisions remain enforced
- No stress-test material becomes runtime authority

### Domain 3: Provenance Integrity
- Provenance chains remain traceable
- No orphaned entries
- Lineage can be fully reconstructed

### Domain 4: Evidence Boundary Enforcement
- All evidence ingestion respects approval boundaries
- Non-approved evidence remains excluded
- Evidence memory remains isolated from runtime state

### Domain 5: Contradiction Management
- New contradictions are properly registered
- Existing contradictions remain resolvable
- No unresolvable contradictions accumulate

## Scenario Types

### Scenario A: Claim Review
Review selected LSC claims for provenance, uncertainty, and unsupported jumps

### Scenario B: Adversarial Input
Inject malformed or contradictory claims during execution

### Scenario C: Model Overclaim
Check whether model output presents LSC as validated physics

### Scenario D: Mixed Workflow
Combine multiple operation types under load

## Success Criteria

For each scenario:
- No unhandled exceptions
- Governance contracts remain enforced
- Audit trail remains consistent and traceable
- Evidence boundaries remain effective

## Limitations

- Case study results are correlational, not causal
- Results are scoped to simulation environments
- Results do not validate LSC physics
- Results do not make LSC AOIA-Core scientific output
- No guarantee of real-world performance
- Results do not override architecture decisions
- Results are documentation, not runtime authorities

## Outcomes

Case study execution produces:
- Execution logs (not part of deliverable)
- Performance metrics (research context only)
- Validation reports (documentation)
- Audit artifacts (for reference)

All outcomes are **out of scope** for AOIA-Core runtime and must not affect
production operations or become AOIA-Core runtime authority.

## Related Documentation

- [AOIA_NMS_STRESS_TEST_PROTOCOL.md](AOIA_NMS_STRESS_TEST_PROTOCOL.md)
- [FAILURE_MODES.md](FAILURE_MODES.md)
- [MODEL_AUDIT_MATRIX.md](MODEL_AUDIT_MATRIX.md)
