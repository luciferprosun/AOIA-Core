# AOIA Test Environment Policy

## Purpose

This policy separates governance/provenance stabilization checks from optional UI and browser test requirements.

AOIA-Core contains tests for multiple surfaces:

- deterministic runtime and retrieval behavior
- evidence boundary enforcement
- append-only provenance
- provenance verification
- local provenance integrity readout
- TUI behavior
- browser/Playwright behavior

Not all surfaces require the same local dependencies.

## Baseline Governance Test Environment

The baseline governance/provenance environment must support Python `unittest` with the repository runtime path available.

Use:

```bash
PYTHONPATH=runtime:. python3 -m unittest -v \
  tests.test_evidence_boundary \
  tests.test_evidence_write_contract \
  tests.test_append_only_provenance \
  tests.test_provenance_verification \
  tests.test_provenance_readout
```

This environment is sufficient to verify:

- evidence write boundary enforcement
- invalid evidence write rejection
- append-only provenance skeleton
- local provenance verification
- local integrity readout

## Phase 0C-0E Focused Verification

For the Phase 0C-0E provenance foundation, use:

```bash
PYTHONPATH=runtime:. python3 -m unittest -v \
  tests.test_append_only_provenance \
  tests.test_provenance_verification \
  tests.test_provenance_readout
```

Current observed result for Phase 0E closure:

```text
Ran 18 tests in 0.053s
OK
```

## Full Suite Verification

Full repository discovery uses:

```bash
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -v
```

This command may require optional dependencies beyond the governance/provenance baseline.

Current observed full-suite result:

```text
Ran 145 tests in 3.274s
FAILED (errors=2, skipped=2)
```

The observed errors were caused by missing TUI dependency:

```text
ModuleNotFoundError: No module named 'textual'
```

The observed skips were browser tests skipped because Playwright is not installed.

## Optional Dependencies

TUI tests require:

- `textual`

Browser tests may require:

- Playwright
- browser runtime dependencies supported by Playwright

These dependencies are optional for provenance/readout stabilization but required for a fully green whole-repository test run.

## Interpretation Rules

Focused provenance/readout tests passing means Phase 0C-0E governance provenance behavior is verified for that scope.

Full test discovery failing only because `textual` is missing must be classified as a test-environment dependency gap, not a provenance/readout failure.

Browser tests skipped because Playwright is missing must be classified as an optional browser test gap, not a provenance/readout failure.

Runtime, routing, provider, orchestration, GUI/TUI, browser, replay, database, distributed provenance, and provider authenticity changes must not be made merely to satisfy Phase 0E closure.

## Required Reporting

Every stabilization checkpoint should report:

- command run
- exact test result summary
- whether failures are implementation failures or environment dependency gaps
- whether optional dependencies were intentionally absent
- whether focused governance tests passed
- whether full repository tests passed

## Current Policy Decision

Phase 0E is considered closed for provenance/readout when the focused Phase 0C-0E tests pass.

Full-suite closure remains conditional on either:

- provisioning optional dependencies such as `textual` and Playwright, or
- documenting optional test groups separately in a future test runner policy.

