# ADR-005: Fail-Fast Philosophy

## Context

Silent fallback behavior can hide invalid configuration and produce confusing
routing results.

## Decision

AOIA must fail immediately on invalid input, invalid configuration, or
unsupported routing states.

## Consequences

Error handling should be clear and early. The router should not guess a routing
depth when required data is missing or invalid.
