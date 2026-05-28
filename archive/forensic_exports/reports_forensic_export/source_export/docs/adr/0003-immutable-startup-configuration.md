# ADR 0003: Immutable Startup Configuration

Status: accepted

Date: 2026-05-21

## Context

AOIA needs configuration before runtime integration, but mutable runtime config
would make routing behavior harder to audit. The early system should load config
once, validate it, and expose it as read-only data.

## Decision

Add:

- `adaptive_routing/aoia_config.json`
- `adaptive_routing/config_loader.py`

The loader returns a frozen dataclass and wraps runtime policy in a read-only
mapping. The config defines:

- config version
- three depths
- pressure thresholds
- startup-only, no-network, readonly runtime policy

## Consequences

Positive:
- AOIA config has a clear contract.
- Later routing logic can use validated thresholds.
- Runtime mutation is blocked by type and structure.

Negative:
- Config changes require process restart in future integrations.
- No live tuning exists yet.

## Validation

Manual validation:

- JSON parses.
- Python compiles.
- `load_config()` returns expected values.
- mutation attempts fail for frozen dataclass fields and runtime policy mapping.

