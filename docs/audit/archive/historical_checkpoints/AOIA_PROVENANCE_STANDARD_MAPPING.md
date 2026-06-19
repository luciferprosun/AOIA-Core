# AOIA Provenance Standard Mapping

Date: 2026-05-28
Scope: conceptual alignment only; no standard implementation.

## References

- W3C PROV namespace and model family: https://www.w3.org/ns/prov
- OpenLineage spec/facets: https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md
- SLSA provenance: https://slsa.dev/spec/v0.2/provenance
- Sigstore Rekor overview: https://docs.sigstore.dev/logging/overview/

## Mapping

| Current object | Current file/path | Closest W3C PROV concept | Closest OpenLineage concept | Closest SLSA concept | AOIA-Nano naming recommendation |
| --- | --- | --- | --- | --- | --- |
| `event_type` in append-only provenance entry | `runtime/tools/provenance.py:74-93` | `activity` type | run event type | build/run step kind | `event_kind` |
| `payload` | `runtime/tools/provenance.py:83-90` | entity attributes or activity attributes | facet/metadata | invocation/build metadata | `event_payload` |
| `payload_hash` | `runtime/tools/provenance.py:80-87` | entity identifier/checksum adjunct | dataset/artifact metadata facet | subject digest or material digest | `payload_digest` |
| `entry_hash` | `runtime/tools/provenance.py:83-89` | provenance record identifier | run event identity metadata | attestation record digest | `entry_digest` |
| `prev_hash` | `runtime/tools/provenance.py:81-88` | derivation/order relation adjunct | run sequence metadata | verification chain metadata | `previous_entry_digest` |
| `GENESIS_PREV_HASH` | `runtime/tools/provenance.py:11` | start of provenance chain | run-log initialization | initial attestation chain marker | `genesis_digest` |
| `AppendOnlyProvenanceStore` | `runtime/tools/provenance.py:55-99` | provenance store for entities/activities/agents | run-event emitter | local attestation ledger | `ProvenanceLedger` |
| `verify_provenance_chain` | `runtime/tools/provenance.py:102-170` | validation of provenance graph consistency | run log verification | provenance verification | `verify_ledger` |
| `ProvenanceVerificationResult` | `runtime/tools/provenance.py:47-52` | validation report entity | run quality/check facet | verification result | `LedgerVerificationResult` |
| `render_integrity_report` | `runtime/tools/provenance_readout.py:19-46` | provenance audit report entity | run/test facet report | verification report | `render_ledger_report` |
| RHCSA retrieval result provenance | `runtime/retrieval/linux/provenance_attach.py` | `used` relation to knowledge entity | input dataset/artifact facet | material dependency | `retrieval_evidence_ref` |
| Evidence memory entry | `runtime/tools/memory.py:175-184` | entity attributed to agent/activity | output dataset/event facet | generated artifact subject | fold into `action_result` / `retrieval_hit` ledger event |
| Session log event | `runtime/main.py:1010-1017` | activity timeline | run event | invocation step | fold into single `provenance.log.jsonl` |

## Minimal Vocabulary Recommendation

AOIA-Nano should use local names while keeping easy export paths:

- `run_id`: OpenLineage-style run identity.
- `event_kind`: local event type.
- `actor`: W3C PROV agent / SLSA builder analogue.
- `activity`: deterministic operation performed.
- `artifact`: generated or read entity.
- `used_artifacts`: W3C `used` and SLSA `materials`.
- `generated_artifacts`: W3C `wasGeneratedBy` and SLSA `subject`.
- `entry_digest`, `previous_entry_digest`: Rekor-inspired append-only integrity chain.

Do not adopt full OpenLineage, SLSA, Sigstore, or W3C PROV schemas in Phase 1.
