# AOIA-Core — Implemented Capabilities

This document separates implemented, partial, planned, legacy/transitional, and
documentation-only capabilities for external reviewers. It is a documentation
status register, not a runtime authority source. For authority boundaries, see
`AUTHORITY_SCOPE.md` and `docs/governance/`.

Current public framing: AOIA-Core is a local-first, non-executing inspection and
audit layer for AI-proposed shell commands.

| Capability | Status | Evidence / location | Safe public wording | Notes |
|---|---|---|---|---|
| Bash command parsing/classification | Implemented | `runtime/tools/validator.py`, `runtime/commands/`, `tests/test_bash_parser_inert.py` | AOIA-Core can inspect proposed shell commands without executing them. | This is inert inspection only. |
| Dry-run safety decision | Implemented | `tests/test_respond_shell_safety.py`, `tests/test_bash_safety_corpus_v0_3.py` | AOIA-Core returns dry-run safety decisions for current corpus cases. | `allowed=True` does not authorize execution. |
| Command execution | Out of current public scope | historical/transitional `runtime/main.py`, `runtime/tools/executor.py` | AOIA-Core makes no current public claim to execute commands. | Historical executor code may exist; it is not the NLnet second-review claim. |
| Browser automation | Legacy/transitional | `runtime/run_web.sh`, `runtime/webapp.py`, web/TUI docs | Browser/UI surfaces are not part of the current safety claim. | No browser hardening claim is made. |
| Provider routing | Legacy/transitional | `state/providers.json`, provider docs/scripts | Provider selection is not part of the current safety claim. | Provider output is non-authoritative and non-deterministic. |
| Evidence write boundary | Partial | docs/governance/EVIDENCE_WRITE_CONTRACT.md | Evidence writes are subject to boundary rules and not automatically treated as canonical. | Implemented as a controlled write path and audit-support mechanism, not a complete immutable CAS evidence store. |
| Append-only provenance | Implemented | docs/governance/APPEND_ONLY_PROVENANCE_CONTRACT.md | Provenance records are intended to be append-only. | Implementation is documented; runtime enforcement may be partial. |
| Provenance verifier | Partial | docs/governance/PROVENANCE_VERIFICATION_CONTRACT.md | Provenance can be verified against recorded trail metadata. | Verifies local lineage/integrity only; it does not validate truth, scientific claims, source authenticity, or model output. |
| Contradiction registry | Partial | docs/governance/CONTRADICTION_REGISTRY.md? | Contradictions are tracked and recorded. | Registry concept documented; resolution is not automatic. |
| Deterministic / rule-based local retrieval | Partial | README.md and docs/ | Local Linux/RHCSA retrieval and epistemic gating are designed to be deterministic where practical. | Retrieval is not the core current safety claim. |
| Human approval gates | Partial | README.md and runtime docs | Approval metadata supports audit review of proposed actions. | Approval flow does not authorize execution in the current public scope. |
| Evidence Memory Phase 1A | Planned | README.md and governance notes | Phase 1A is not active unless explicitly approved later by ADR/operator decision. | This is intentionally marked as planned. |
| Replay verification | Partial | README.md and docs | Replay verification is a design goal. | compileall validates Python syntax/import compilation only. It is not proof of runtime correctness, security, or production readiness. |
| Runtime safety contracts | Partial | docs/governance/ and docs/architecture/ | Safety contracts are strong design/governance contracts with partial runtime enforcement today. | Full production safety enforcement is roadmap work, not a current certification claim. |
| Runtime GUI/TUI | Documentation only | README.md | GUI/TUI is documented as postponed or optional. | Web/TUI surfaces are visualization, debug, and operator interfaces, not the core deliverable. |
| Stress-test documentation | Implemented | docs/stress_tests/README.md | Stress-test docs are reviewer/research context only. | Execution is not part of this patch. |
| External model output policy | Implemented | docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md | External model outputs are historical/reviewer context, not evidence. | See policy docs. |
| RHCSA/static knowledge pipeline | Partial | README.md and docs/ | Static knowledge pipeline is present for engineering context. | It is documented; it is not a claim of validated knowledge. |

## Notes

- compileall validates Python syntax/import compilation only. It is not proof of runtime correctness, security, or production readiness.
- Historical execution, browser, provider, web, and TUI surfaces may remain in
  the repository. They are not the current NLnet second-review claim unless a
  current governance document explicitly promotes them.
- Status values are conservative. If there is uncertainty, the capability is marked Partial or Planned.
- This document is a documentation status register, not a proof of correctness.
- `AOIAEpistemicKernel` is the canonical epistemic gate. `KnowledgeRouter` is a legacy/compatibility transition surface, not a second canonical authority.
- Generated `state/`, `memory/`, `logs/`, and `obsidian_vault/` artifacts are runtime artifacts, not canonical source authority.
