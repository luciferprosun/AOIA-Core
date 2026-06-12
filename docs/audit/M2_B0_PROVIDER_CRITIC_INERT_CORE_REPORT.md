# M2-B0 Provider Critic Inert Core Report

Date: 2026-06-12

Branch: `feature/m2-b0-provider-critic-inert-core`

## Executive Summary

M2-B0 adds an inert local Controlled Provider Critic core.

The implementation creates local safety records, a local policy object, a local gateway, and audit helpers for attempted provider critique calls. The gateway blocks by default and does not perform network I/O.

No live provider calls were added. No secrets were added. No network path was added. No runtime action authority was added.

## What Was Added

Modules:

- `runtime/provider_critic/__init__.py`
- `runtime/provider_critic/records.py`
- `runtime/provider_critic/policy.py`
- `runtime/provider_critic/audit.py`
- `runtime/provider_critic/gateway.py`

Tests:

- `tests/test_m2_provider_critic_inert_core.py`

Report:

- `docs/audit/M2_B0_PROVIDER_CRITIC_INERT_CORE_REPORT.md`

## Safety Invariants

- Provider output is always `UNTRUSTED`.
- Provider output remains `NOT_CANONICAL`.
- Provider output has no action authority.
- Provider output has no execution permission.
- Provider calls are blocked by default.
- Auto-send is disabled by default.
- Attempted provider calls create local audit records.
- Audit records redact synthetic key-like strings.
- Call ceiling exists in code and defaults to zero calls.
- Metadata cannot override safety fields.
- Serialization preserves safety flags.

## What Was Not Added

- No live Gemini/GPT API call.
- No OpenAI, Anthropic, or Gemini SDK.
- No cloud integration.
- No Tika or document parsing pipeline.
- No ActionProposal execution.
- No sandbox execution.
- No agent loop.
- No shell, browser, filesystem, or git action path.

## Validation

Commands:

```bash
python3 -m compileall -q runtime tests
python3 -m unittest tests.test_m2_provider_critic_inert_core -v
python3 -m unittest discover -s tests
node --check web/app.js
git diff --check
git status -sb
python3 -m unittest tests.test_red1_shell_executor_freeze -v
python3 -m unittest tests.test_red1_provider_network_gateway_separation -v
python3 -m unittest tests.test_red1_browser_surface_freeze -v
python3 -m unittest tests.test_red1_filesystem_git_surface_freeze -v
python3 -m unittest tests.test_red1_boundary_negative -v
python3 -m unittest tests.test_red1_public_entrypoint_boundary_negative -v
python3 -m unittest tests.test_reviewer_safe_execution_lock -v
```

Results:

- `python3 -m compileall -q runtime tests`: PASS.
- `python3 -m unittest tests.test_m2_provider_critic_inert_core -v`: PASS, 15 tests OK.
- `python3 -m unittest discover -s tests`: PASS, 731 tests OK / 4 skipped.
- `node --check web/app.js`: PASS.
- `git diff --check`: PASS.
- RED-1 shell/executor freeze focused tests: PASS, 11 tests OK.
- RED-1 provider/network gateway separation focused tests: PASS, 5 tests OK.
- RED-1 browser surface freeze focused tests: PASS, 5 tests OK.
- RED-1 filesystem/git surface freeze focused tests: PASS, 5 tests OK.
- RED-1 boundary negative tests: PASS, 5 tests OK.
- RED-1 public entrypoint boundary negative tests: PASS, 11 tests OK.
- Reviewer safe execution lock tests: PASS, 2 tests OK.

## Remaining Blockers Before Live Provider Call

- Key management policy.
- Cost and call policy.
- Explicit enable-flag design.
- Provider adapter tests.
- UI `UNTRUSTED` labeling.
- Tests preventing provider-to-evidence contamination.
- Human review flow.
