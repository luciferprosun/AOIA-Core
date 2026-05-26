# AOIA Governance Implementation Status

| Invariant | Status | Runtime enforced? | Test coverage | Notes |
| --- | --- | --- | --- | --- |
| Evidence writes require explicit kind/source/fingerprint | ENFORCED | Yes | `tests.test_evidence_boundary`, `tests.test_evidence_write_contract` | Centralized in `MemoryStore.append_evidence()` / `_validate_evidence_payload()`. |
| Runtime action results blocked from evidence channel | ENFORCED | Yes | `tests.test_executor_containment`, `tests.test_memory_layer_isolation_smoke`, `tests.test_evidence_write_contract` | Action results remain operational history, not canonical evidence. |
| Provider outputs blocked from direct evidence promotion | ENFORCED | Yes | `tests.test_evidence_write_contract` | Direct provider output cannot enter evidence unless explicitly reclassified under allowed external evidence source. |
| Browser captures blocked from direct evidence promotion | ENFORCED | Yes | `tests.test_evidence_write_contract` | Generic browser source is rejected by the allowlist. |
| Append-only provenance skeleton | PARTIAL | Yes | `tests.test_append_only_provenance` | New append-only provenance store is deterministic and hash-linked, but not yet a full replay or trust system. |
| Hash-chained provenance | PARTIAL | Yes | `tests.test_append_only_provenance` | SHA-256 prev-hash chain is implemented for the new provenance append skeleton only. |
| Physical L3/L4 storage isolation | NOT_STARTED | No | None | Documented doctrine only. |
| Replay verification | NOT_STARTED | No | None | No replay verifier or signed provenance chain exists. |
| Epistemic approval gate | DOCUMENTED_ONLY | No | None | Conceptually present in doctrine, not runtime enforced. |
| Contradiction blocking | PARTIAL | Limited | Indirect coverage in existing contradiction-related tests only | Contradictions are tracked, but no formal runtime block policy is enforced here. |

## Notes

- The current enforcement boundary is intentionally narrow.
- This phase formalizes evidence writes, but it does not redesign memory architecture.
- Only the public `MemoryStore` evidence path is being hardened here.
