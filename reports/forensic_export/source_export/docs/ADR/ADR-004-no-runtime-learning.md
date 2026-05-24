# ADR-004: No Runtime Learning

## Context

Runtime learning would make routing decisions depend on previous requests and
mutable internal state.

## Decision

AOIA must not learn, tune, rank, or modify routing behavior during runtime.

## Consequences

All routing changes must come from reviewed code or configuration changes loaded
at startup.
