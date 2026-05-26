# AOIA Evidence Write Contract

## Purpose

Evidence writes are privileged epistemic events. Runtime action results, model outputs, browser captures, and operator notes must not become canonical evidence unless they pass explicit validation.

This contract formalizes the current boundary around `MemoryStore.append_evidence()` and separates doctrine from runtime enforcement.

## Allowed evidence kind

- `aoia_kernel_evidence`

## Allowed source domains

- `aoia_kernel`
- `knowledge_router`
- `external_evidence_source`

## Required fields

- `kind`
- `source`
- `fingerprint`

## Rejected cases

- missing kind
- wrong kind
- missing source
- source outside allowlist
- missing fingerprint
- empty fingerprint
- runtime execution result promoted as evidence
- provider response promoted as evidence without explicit evidence source classification
- browser capture promoted as evidence through generic memory API

## Current enforcement status

Enforced now:
- `MemoryStore.append_evidence()` rejects any kind other than `aoia_kernel_evidence`.
- `MemoryStore.append_evidence()` rejects payloads without a non-empty `source`.
- `MemoryStore.append_evidence()` rejects payloads without a non-empty `fingerprint`.
- `MemoryStore.append_evidence()` rejects sources outside the allowlist.
- Invalid payloads are rejected before any evidence file write occurs.

Not yet enforced:
- append-only hash chaining
- cryptographic provenance record
- replay verification
- physical L3/L4 storage isolation
- epistemic approval gate

## Future work

- append-only hash chain
- cryptographic provenance record
- replay verification
- L3/L4 physical storage isolation
- epistemic approval gate

## Interpretation

This contract does not claim full provenance integrity.

It only states that canonical evidence writes are now explicit, typed, and gated through a narrow public API boundary.
