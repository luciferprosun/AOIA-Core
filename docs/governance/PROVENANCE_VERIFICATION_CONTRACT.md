# AOIA Provenance Verification Contract

## Current guarantees

- append-only chain structure
- local chain continuity verification
- deterministic integrity verification

## NOT guaranteed yet

- replay fidelity
- provider authenticity
- immutable filesystem
- cryptographic signatures
- distributed trust
- anti-operator guarantees

## Threats currently detectable

- accidental local corruption
- silent chain mutation
- broken linkage

## Future phases

- replay verification
- signed provenance
- immutable evidence storage
- L3/L4 physical separation

## Scope

This contract only describes a local read-path verifier for the minimal provenance chain introduced in Phase 0C.

It is not a replay engine and it does not claim external authenticity.
