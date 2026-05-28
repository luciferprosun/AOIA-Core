# ADR 0002: Minimal Deterministic Router Skeleton

Status: accepted

Date: 2026-05-21

## Context

AOIA needs a tiny deterministic routing skeleton before any adaptive runtime
integration. The goal is to define a stable shape for later routing work without
adding networking, provider selection, or backend changes.

## Decision

Add one pure function:

```python
select_depth(pressure: int) -> str
```

It returns exactly one of:

- `shallow`
- `mid`
- `deep`

The function is deterministic and uses fixed thresholds:

- `0..33` -> `shallow`
- `34..66` -> `mid`
- `67+` -> `deep`

Negative pressure is invalid and raises `ValueError`.

## Consequences

Positive:
- Simple contract for later tests and integration.
- No network behavior.
- No provider behavior.
- No runtime side effects.

Negative:
- The pressure score is not yet derived from real system conditions.
- The names are placeholders for future AOIA semantics.

## Validation

Manual validation:

- `select_depth(0)` returns `shallow`
- `select_depth(34)` returns `mid`
- `select_depth(67)` returns `deep`
- module compiles with Python

