# AOIA Governance Implementation Status

| Invariant | Status | Runtime enforced? | Test coverage | Notes |
| --- | --- | --- | --- | --- |
| Evidence writes require explicit kind/source/fingerprint | ENFORCED | Yes | `tests.test_evidence_boundary`, `tests.test_evidence_write_contract` | Centralized in `MemoryStore.append_evidence()` / `_validate_evidence_payload()`. |
| Runtime action results blocked from evidence channel | ENFORCED | Yes | `tests.test_executor_containment`, `tests.test_memory_layer_isolation_smoke`, `tests.test_evidence_write_contract` | Action results remain operational history, not canonical evidence. |
| Provider outputs blocked from direct evidence promotion | ENFORCED | Yes | `tests.test_evidence_write_contract` | Direct provider output cannot enter evidence unless explicitly reclassified under allowed external evidence source. |
| Browser captures blocked from direct evidence promotion | ENFORCED | Yes | `tests.test_evidence_write_contract` | Generic browser source is rejected by the allowlist. |
| Append-only provenance skeleton | ENFORCED | Yes | `tests.test_append_only_provenance`, `tests.test_provenance_verification` | New provenance store appends only and is hash-linked. |
| Hash-chained provenance | ENFORCED | Yes | `tests.test_append_only_provenance`, `tests.test_provenance_verification` | SHA-256 prev-hash chain is implemented for the new provenance append skeleton. |
| Provenance verification | ENFORCED | Yes | `tests.test_provenance_verification` | Local read-path verifies continuity, payload hashes, and deterministic integrity. |
| Physical L3/L4 storage isolation | NOT_STARTED | No | None | Documented doctrine only. |
| Replay verification | NOT_STARTED | No | None | No replay verifier exists. |
| Epistemic approval gate | DOCUMENTED_ONLY | No | None | Conceptually present in doctrine, not runtime enforced. |
| Contradiction blocking | PARTIAL | Limited | Indirect coverage in existing contradiction-related tests only | Contradictions are tracked, but no formal runtime block policy is enforced here. |
| Immutable storage | NOT_STARTED | No | None | No filesystem immutability or WORM layer exists. |
| Provider authenticity verification | NOT_STARTED | No | None | No provider authenticity verification exists. |

## Notes

- The current enforcement boundary is intentionally narrow.
- This phase formalizes evidence writes, but it does not redesign memory architecture.
- Only the public `MemoryStore` evidence path is being hardened here.
