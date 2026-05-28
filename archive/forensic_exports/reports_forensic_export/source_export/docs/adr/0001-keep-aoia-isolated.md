# ADR 0001: Keep AOIA Isolated Until Explicit Integration

Status: accepted

Date: 2026-05-21

## Context

The terminal app already has a working runtime, provider configuration, local
knowledge routing, approval gates, logs, memory, CLI, and web UI.

AOIA introduces a new adaptive routing direction inspired by DVM and ecosystem
behavior. Integrating that too early would risk changing provider behavior,
token usage, or terminal workflows before the design is stable.

## Decision

AOIA files remain isolated under `adaptive_routing/` and documentation under
`docs/`.

No AOIA module may control runtime behavior, provider selection, shell
execution, browser automation, or memory writes until a later approved
integration step.

## Consequences

Positive:
- Existing terminal behavior remains stable.
- AOIA can evolve through small reviewable modules.
- Future integration points can be designed with clearer contracts.

Negative:
- AOIA will not affect runtime efficiency immediately.
- Some early modules may feel like scaffolding before they become useful.

## Validation

Validation for this ADR is structural:

- AOIA files are isolated.
- No imports from `adaptive_routing/` are added to `main.py`.
- No provider code is modified for AOIA.
- No shell/browser executor behavior is modified for AOIA.

