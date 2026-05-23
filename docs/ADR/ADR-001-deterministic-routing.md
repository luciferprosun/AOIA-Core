# ADR-001: Deterministic Routing

## Context

AOIA needs routing decisions that can be reproduced during tests, debugging, and
review.

## Decision

Routing must be deterministic. The same input, same config, and same code
version must produce the same routing depth.

## Consequences

Runtime learning, random selection, hidden state, and live policy mutation are
excluded from the router.
