# Test Constitution

## Principle

AOIA tests must prove deterministic behavior before any runtime integration.

## Required Properties

- Same input returns same output.
- Boundary values are explicit.
- Invalid input fails fast.
- Configuration loads deterministically.
- Configuration is readonly after loading.
- Tests must not call external networks.
- Tests must not require provider keys.
- Tests must not depend on current time unless time is explicitly injected.

## Fail-Fast Rule

Invalid configuration or invalid pressure input should raise immediately. Silent
fallbacks are not allowed in AOIA core contracts.

## Test Layers

Unit tests:
- pure functions
- config loading
- validation behavior

Integration tests:
- allowed only after runtime integration is approved

External tests:
- forbidden in early AOIA steps

## Current AOIA Test File

- `tests/test_aoia_determinism.py`

## Current Validation Focus

- `select_depth()` determinism
- pressure threshold stability
- invalid pressure rejection
- `load_config()` deterministic loading
- readonly config behavior
- correlation id shape

