# Memory Domain Split Plan

Phase: 3 - governance preparation
Status: conceptual target design only

## Purpose

Describe the future conceptual split for AOIA memory domains.

This does not refactor `memory.py`.

## L0 - Ephemeral Runtime

Purpose:

- current request state
- temporary routing state
- process-local execution state

Persistence:

- none by default

Forbidden:

- evidence writes
- provenance writes
- authority decisions

## L1 - Operational Logs

Purpose:

- replay support
- execution diagnostics
- tool and runtime event history

Persistence:

- append-only operational log storage

Forbidden:

- evidence promotion
- canonical authority

## L2 - Reasoning Traces

Purpose:

- non-authoritative reasoning context
- audit of model/planner reasoning surfaces where available

Persistence:

- quarantined trace storage

Forbidden:

- retrieval as evidence
- promotion to L4
- provenance source status

## L3 - Provenance Records

Purpose:

- source chains
- import events
- normalization events
- derivation records

Persistence:

- append-only provenance log

Forbidden:

- ungrounded provider claims
- reasoning trace as source

## L4 - Immutable Evidence

Purpose:

- externally grounded evidence artifacts
- source documents
- verified raw imports

Persistence:

- immutable or content-addressed storage in future implementation

Forbidden:

- operational logs
- runtime state
- model output without external provenance

## L5 - Contradiction Registry

Purpose:

- preserve contradictions
- record review status
- prevent false resolution

Persistence:

- append-only contradiction registry

Forbidden:

- automatic contradiction resolution
- deletion as cleanup

## Future Physical Split

Future implementation should separate modules and storage paths by layer.

`memory.py` must not remain the shared write surface for multiple authority layers.
