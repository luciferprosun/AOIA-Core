# ADR-002: Three Depth Model

## Context

AOIA needs a small vocabulary for routing depth without creating policy sprawl.

## Decision

AOIA uses exactly three routing depths: LOCAL, MID, and PREMIUM.

## Consequences

All routing logic, config, tests, and documentation must use these three names.
Adding a fourth depth requires a new ADR.
