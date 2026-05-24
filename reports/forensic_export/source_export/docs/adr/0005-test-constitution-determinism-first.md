# ADR 0005: Test Constitution, Determinism First

Status: accepted

Date: 2026-05-21

## Context

AOIA will later influence routing decisions. Before integration, its core must
be deterministic, easy to test, and fail-fast on invalid input.

## Decision

Add a dedicated AOIA test module:

- `tests/test_aoia_determinism.py`

AOIA tests prioritize:

- same input -> same output
- explicit boundary checks
- invalid input raises
- readonly config checks
- no network or provider requirements

## Consequences

Positive:
- Future routing changes have a stable safety net.
- Runtime integration can be gated by tests.
- Failures happen early and locally.

Negative:
- Current tests are narrow by design.
- No behavioral runtime coverage exists yet because AOIA is not integrated.

## Validation

Validation command:

```bash
python3 -m unittest tests.test_aoia_determinism
```

