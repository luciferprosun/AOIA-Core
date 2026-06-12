# RED-1-E Shell / Executor Freeze Report

Date: 2026-06-12

Branch: `feature/red1-e-shell-executor-freeze`

Purpose: apply the fourth targeted RED-1 freeze by marking legacy shell/executor surfaces as frozen, default-off, and not approved as AOIA production execution paths.

## Files changed

- `runtime/tools/shell_tools.py`
- `runtime/tools/executor.py`
- `runtime/commands/local_commands.py`
- `runtime/tools/validator.py`
- `runtime/prompts/system_prompt.txt`
- `tests/test_red1_shell_executor_freeze.py`
- `docs/audit/RED_1_E_SHELL_EXECUTOR_FREEZE_REPORT.md`

## Surface frozen

The phase freezes the legacy shell/executor surface:

- `runtime/tools/shell_tools.py`
- `runtime/tools/executor.py` shell action dispatch
- legacy `/rhcsa build` subprocess-capable path
- legacy `/scemda ...` subprocess-capable path
- runtime prompt wording that previously exposed `shell_execute` without a nearby freeze warning

## Freeze method used

Added explicit shell/executor markers:

- `LEGACY_SHELL_EXECUTOR_SURFACE = True`
- `APPROVED_RUNTIME_SHELL_EXECUTION_FLOW = False`
- `SHELL_EXECUTION_FROZEN = True`

Added default-off environment gate:

- `AOIA_SHELL_EXECUTION_ENABLED`

Added guard helpers:

- `_legacy_shell_execution_enabled()`
- `_require_legacy_shell_execution_enabled()`
- `shell_execution_blocked_result()`

The default behavior is blocked. `shell_execute` returns a reviewer-safe blocked result with empty stdout/stderr and no exit code. The executor registry marks `shell_execute` as a frozen legacy shell/executor surface. The executor shell path blocks before calling the shell backend when the gate is disabled.

## What remains allowed

The following remain allowed because they are non-executing:

- shell command text validation
- shell command classification
- command proposals
- dry-run inspection semantics
- CPT prompt transformation
- local config/catalog/proposal-only paths

## What tests prove

`tests/test_red1_shell_executor_freeze.py` proves:

- shell module markers are frozen and not approved;
- the default shell execution guard blocks;
- `shell_execute` does not reach `subprocess.run`, `subprocess.Popen`, or `os.system`;
- executor shell action blocks before calling the shell backend;
- executor registry marks `shell_execute` as frozen legacy;
- `allowed=True` and command classification do not execute anything;
- legacy SCEMDA subprocess path is blocked by default;
- legacy RHCSA build subprocess path is blocked before prompt/subprocess by default;
- CPT local transform does not reach shell primitives;
- live runtime code does not approve shell execution by default;
- runtime prompt states that shell execution is frozen legacy and not authorized by approval.

Previous RED-1 focused tests also pass for public entrypoints, browser freeze, filesystem/git freeze, provider/network freeze, RED-1 boundary negatives, and reviewer-safe execution lock.

## Explicit non-claims

- RED-1 is not closed.
- No shell execution capability was added.
- No autonomous shell execution was added.
- No new `subprocess` execution path was added.
- No `os.system` path was added.
- No sudo/package-install behavior was added.
- No terminal agent was created.
- No model/CPT/provider output was connected to shell execution.
- No browser automation was added.
- No provider/API/model call was added.
- No git automation was added.
- No file-write/delete automation was added.
- Browser, filesystem/git, and provider/network freezes were not loosened.

## Semantic boundary

`allowed=True` in inspection/classification means the command text passed the current inspection policy.

It does not mean execute.

Human approval does not automatically mean execution.

Provider/model output remains untrusted.

Shell execution remains not approved in AOIA production flow.

## Remaining blockers after RED-1-E

- RED-1 closure report / final surface reconciliation remains open.
- Proposal/action separation hardening remains open.
- Provider output remains untrusted and non-authoritative.
- Approved action execution architecture is still absent.
- Sandboxed execution is not implemented.
- Controlled agent loop is not implemented.
- Public entrypoint and legacy runtime framework cleanup still require final reconciliation.

## Validation

Validation performed during this phase:

- `python3 -m compileall -q runtime tests`: pass
- `python3 -m unittest tests.test_red1_shell_executor_freeze -v`: 11 OK
- `python3 -m unittest tests.test_red1_public_entrypoint_boundary_negative -v`: 11 OK
- `python3 -m unittest tests.test_red1_browser_surface_freeze -v`: 5 OK
- `python3 -m unittest tests.test_red1_filesystem_git_surface_freeze -v`: 5 OK
- `python3 -m unittest tests.test_red1_provider_network_gateway_separation -v`: 5 OK
- `python3 -m unittest tests.test_red1_boundary_negative -v`: 5 OK
- `python3 -m unittest tests.test_reviewer_safe_execution_lock -v`: 2 OK
- `python3 -m unittest discover -s tests`: 716 tests OK, 4 skipped
- `node --check web/app.js`: pass
- `git diff --check`: pass

Final pre-commit git status showed only the RED-1-E intended files modified or added.

## Recommended next targeted phase

RED-1 final closure report / proposal-action separation reconciliation.
