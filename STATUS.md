# AOIA-Core Status

## Implemented

- Local-first command inspection and audit artifacts.
- Bash safety parser and corpus work for pre-execution inspection.
- Inert schemas used to describe structure and review targets.
- Dry-run approval concepts and related tests.
- Reviewer evidence documentation for external review.
- No autonomous shell execution in the current reviewer claim.

## Partial / Transitional

- Legacy tools remain visible in the repository.
- Dev-tools are present for development support, not as the main reviewer claim.
- Provider switcher exists as repository tooling, not as current reviewer scope.
- Lab clone utility exists as developer support, not as current reviewer scope.
- Older executor and shell tooling may still be visible in the tree but are not part of the current reviewer claim.

## Planned / Out of Scope Now

- Real shell execution.
- Autonomous command execution.
- Provider orchestration.
- Cloudflare or live deployment.
- Browser automation.
- Gmail or other email sending.
- Android flashing workflows.
- GUI production application delivery.

## Reviewer Notes

AOIA-Core should be reviewed as a safety, audit, and pre-execution inspection layer. It should not be reviewed as an autonomous agent or as a production shell executor.

## CI / Import Layout Note

The current test suite imports several modules as top-level names from inside
`runtime/` (`main`, `tools`, `adaptive_routing`, `retrieval`, `orchestrator`).

For this reviewer-packaging phase, CI uses:

`PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`

This matches the empirically validated current validation command:
470 tests passed, 4 skipped.

This is a temporary compatibility measure, not the final packaging architecture.
Import-layout normalization / packaging refactor is deferred to a separate
audited phase before GT-RUNTIME-9.
