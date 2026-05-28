# ADR 0004: Stdout-Only Plain-Text Logging

Status: accepted

Date: 2026-05-21

## Context

AOIA will eventually make routing recommendations. Those recommendations need
to be explainable, but adding dashboards or telemetry now would create
unnecessary complexity and privacy risk.

## Decision

AOIA logging starts with:

- stdout only
- plain text
- correlation ids
- no dashboards
- no external services

Add a small helper:

- `adaptive_routing/stdout_logger.py`

## Consequences

Positive:
- Easy to inspect in terminal sessions.
- No storage or privacy expansion.
- No new dependencies.
- Suitable for early deterministic prototypes.

Negative:
- Logs are not persisted unless the parent process captures stdout.
- No search UI or dashboard exists.

## Validation

Manual validation:

- module compiles
- running module prints one plain-text log line
- runtime remains unmodified

