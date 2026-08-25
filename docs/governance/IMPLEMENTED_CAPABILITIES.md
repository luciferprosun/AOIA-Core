# AOIA-Core — Implemented Capabilities

This document separates implemented, partial, planned, and documentation-only capabilities for external reviewers. It is a status register, not a runtime authority source. For authority boundaries, see `AUTHORITY_SCOPE.md` and `docs/governance/`.

| Capability | Status | Evidence / location | Safe public wording | Notes |
|---|---|---|---|---|
| Evidence write boundary | Partial | docs/governance/EVIDENCE_WRITE_CONTRACT.md | Evidence writes are subject to boundary rules and not automatically treated as canonical. | Implemented as a controlled write path and audit-support mechanism, not a complete immutable CAS evidence store. |
| Append-only provenance | Implemented | docs/governance/APPEND_ONLY_PROVENANCE_CONTRACT.md | Provenance records are intended to be append-only. | Implementation is documented; runtime enforcement may be partial. |
| Provenance verifier | Partial | docs/governance/PROVENANCE_VERIFICATION_CONTRACT.md | Provenance can be verified against recorded trail metadata. | Verifies local lineage/integrity only; it does not validate truth, scientific claims, source authenticity, or model output. |
| Contradiction registry | Partial | docs/governance/CONTRADICTION_REGISTRY.md? | Contradictions are tracked and recorded. | Registry concept documented; resolution is not automatic. |
| Deterministic / rule-based local retrieval | Partial | README.md and docs/ | Local Linux/RHCSA retrieval and epistemic gating are designed to be deterministic where practical. | External model providers, including optional xAI/Grok, are non-deterministic and non-authoritative. |
| Provider switching | Implemented | README.md and runtime config | Provider selection is supported in the runtime. | Switching is an optional convenience/demo capability; provider behavior is external and not runtime authority. |
| Dated evidence review | Implemented (bounded) | `runtime/evidence_review/`, `docs/modules/DATED_EVIDENCE_REVIEW.md`, and focused tests | AOIA-Core can deterministically compare one bounded time-sensitive claim with a dated official-source registry. | Always requires human review; no provider call, approval, legal conclusion, or general reasoning claim. |
| Human approval gates | Partial | README.md and runtime docs | Risky actions require explicit human approval where gates are implemented. | Approval flow exists; not all actions may be gated. |
| Evidence Memory Phase 1A | Planned | README.md and governance notes | Phase 1A is not active unless explicitly approved later by ADR/operator decision. | This is intentionally marked as planned. |
| Replay verification | Partial | README.md and docs | Replay verification is a design goal. | compileall validates Python syntax/import compilation only. It is not proof of runtime correctness, security, or production readiness. |
| Runtime safety contracts | Partial | docs/governance/ and docs/architecture/ | Safety contracts are strong design/governance contracts with partial runtime enforcement today. | Full production safety enforcement is roadmap work, not a current certification claim. |
| Runtime web UI | Implemented | `runtime/webapp.py`, `web/`, and API tests | One loopback-only web console exposes the assistant and dated-evidence module. | The UI does not change runtime authority. |
| Runtime TUI | Optional / partial | `tui/` and TUI tests | A Textual operator surface is available when the optional dependency is installed. | It delegates to the existing runtime and does not create a second authority path. |
| Stress-test documentation | Implemented | docs/stress_tests/README.md | Stress-test docs are reviewer/research context only. | Execution is not part of this patch. |
| External model output policy | Implemented | docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md | External model outputs are historical/reviewer context, not evidence. | See policy docs. |
| RHCSA/static knowledge pipeline | Partial | README.md and docs/ | Static knowledge pipeline is present for engineering context. | It is documented; it is not a claim of validated knowledge. |

## Notes

- compileall validates Python syntax/import compilation only. It is not proof of runtime correctness, security, or production readiness.
- Status values are conservative. If there is uncertainty, the capability is marked Partial or Planned.
- This document is a documentation status register, not a proof of correctness.
- `AOIAEpistemicKernel` is the canonical epistemic gate. `KnowledgeRouter` is a legacy/compatibility transition surface, not a second canonical authority.
- Generated `state/`, `memory/`, `logs/`, and `obsidian_vault/` artifacts are runtime artifacts, not canonical source authority.
