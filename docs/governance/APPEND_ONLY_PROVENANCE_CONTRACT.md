# AOIA Append-Only Provenance Contract

## Purpose

Prevent silent mutation of provenance history through normal runtime APIs.

Provenance records are append-only operational lineage events. They are not a general-purpose mutable store.

## Current guarantees

- append-only write path
- SHA-256 hash chaining
- previous-entry linkage
- no overwrite through public append API

## NOT guaranteed yet

- cryptographic signatures
- immutable storage
- distributed verification
- replay fidelity
- filesystem immutability
- external provider authenticity
- cross-machine trust

## Threat model currently addressed

- accidental overwrite
- silent local mutation through runtime APIs
- missing provenance linkage

## Future phases

- replay verification
- SQLite/WAL migration
- signed provenance
- immutable evidence storage
- provenance verification CLI
