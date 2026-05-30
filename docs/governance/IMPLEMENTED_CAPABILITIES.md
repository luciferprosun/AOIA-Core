# AOIA-Core — Implemented Capabilities

[5/30/26 10:58 AM] Lukaszzz: This document separates implemented, partial, planned, and documentation-only capabilities for external reviewers. It is a documentation status register, not a runtime authority source. For authority boundaries, see AUTHORITY_SCOPE.md and docs/governance/.

| Capability | Status | Evidence / location | Safe public wording | Notes |
|---|---|---|---|---|
| Evidence write boundary | Implemented | docs/governance/EVIDENCE_WRITE_CONTRACT.md | Evidence writes are subject to boundary rules and not automatically treated as canonical. | Boundary language exists in governance docs. |
| Append-only provenance | Implemented | docs/governance/APPEND_ONLY_PROVENANCE_CONTRACT.md | Provenance records are intended to be append-only. | Implementation is documented; runtime enforcement may be partial. |
| Provenance verifier | Partial | docs/governance/PROVENANCE_VERIFICATION_CONTRACT.md | Provenance can be verified against recorded trail metadata. | Verification design exists; full runtime coverage may not be complete. |
| Contradiction registry | Partial | docs/governance/CONTRADICTION_REGISTRY.md? | Contradictions are tracked and recorded. | Registry concept documented; resolution is not automatic. |
| Deterministic / rule-based local retrieval | Partial | README.md and docs/ | Local retrieval is designed to be deterministic where practical. | External model outputs are not fully deterministic. |
| Provider switching | Implemented | README.md and runtime config | Provider selection is supported in the runtime. | Switching is documented but provider behavior is external. |
| Human approval gates | Partial | README.md and runtime docs | Risky actions require explicit human approval where gates are implemented. | Approval flow exists; not all actions may be gated. |
| Evidence Memory Phase 1A | Planned | README.md and governance notes | Phase 1A is not active unless explicitly approved later by ADR/operator decision. | This is intentionally marked as planned. |
| Replay verification | Partial | README.md and docs | Replay verification is a design goal. | compileall validates Python syntax/import compilation only. It is not proof of runtime correctness, security, or production readiness. |
| Runtime GUI/TUI | Documentation only | README.md | GUI/TUI is documented as postponed or optional. | TUI Phase 3 is postponed and not part of the current deliverable. |
| Stress-test documentation | Implemented | docs/stress_tests/README.md | Stress-test docs are reviewer/research context only. | Execution is not part of this patch. |
| External model output policy | Implemented | docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md | External model outputs are historical/reviewer context, not evidence. | See policy docs. |
| RHCSA/static knowledge pipeline | Partial | README.md and docs/ | Static knowledge pipeline is present for engineering context. | It is documented; it is not a claim of validated knowledge. |

## Notes

- compileall validates Python syntax/import compilation only. It is not proof of runtime correctness, security, or production readiness.
- Status values are conservative. If there is uncertainty, the capability is marked Partial or Planned.
- This document is a documentation status register, not a proof of correctness.
