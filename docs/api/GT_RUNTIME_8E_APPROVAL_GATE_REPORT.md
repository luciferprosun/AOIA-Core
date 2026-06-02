# GT-RUNTIME-8E Approval Gate Report

## Starting branch and HEAD

- Starting branch: `dev/gt-runtime-8-bash-safety-planning`
- Starting HEAD: `b57d69b test: add inert Bash safety corpus`

## Purpose

GT-RUNTIME-8E adds a dry-run-only approval gate for `CommandProposal` objects.

The goal is to decide whether a proposal is allowed to pass as a dry-run decision, requires human review, or should be denied, without executing command text.

## Files added/updated

Added:

- `runtime/schemas/approval_decision.py`
- `runtime/safety/approval_gate.py`
- `tests/test_approval_gate_dry_run.py`
- `docs/api/GT_RUNTIME_8E_APPROVAL_GATE_REPORT.md`

Updated:

- `runtime/schemas/__init__.py`
- `runtime/safety/__init__.py`

## ApprovalDecision shape

`ApprovalDecision` now lives in `runtime/schemas/approval_decision.py`.

`ApprovalDecision` is a frozen, inert data object.

Fields:

- `allowed`
- `approval_state`
- `reason`
- `dry_run`
- `requires_human_review`
- `execution_permitted`

GT-RUNTIME-8E hard-locks `execution_permitted=False`.

## Approval behavior

`evaluate_approval` only evaluates a `CommandProposal`.

`approval_gate.py` accepts only `CommandProposal` objects.

`approval_gate.py` does not parse raw strings.

Behavior:

- `safe` proposals return `allowed=True` with `approval_state="not_required"`
- `ambiguous` proposals return `allowed=False` with `approval_state="requires_human_review"`
- `dangerous` proposals return `allowed=False` with `approval_state="requires_human_review"`
- `unknown` proposals return `allowed=False` with `approval_state="requires_human_review"`
- non-dry-run proposals are blocked even if their classification is `safe`
- invalid or unrecognized classifications return `allowed=False` with `approval_state="requires_human_review"`

`evaluate_command_text` is intentionally not included in GT-RUNTIME-8E.

## Dry-run boundary

GT-RUNTIME-8E does not execute shell commands.

Safe commands are allowed only as dry-run decisions, not executed.

`allowed=True` means only "allowed as a dry-run decision," not "allowed to execute."

Ambiguous, dangerous, unknown, and non-dry-run proposals require human review or denial.

## What remains non-executing

The approval gate:

- does not execute commands
- does not inspect the filesystem
- does not integrate with an executor
- does not create autonomous command execution
- does not imply that an approved dry-run decision should be executed

ApprovalDecision is a dry-run boundary result only.

## Validation performed

Planned validation:

- `python3 -m compileall runtime tests`
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`
- `git diff --stat`
- `git status --short`
- `git diff --name-status`
- `grep -RIn "subprocess\\|os.system\\|shell=True\\|eval(\\|exec(" runtime/safety runtime/schemas 2>/dev/null || true`

## Limitations

This is not a production approval system.

The gate only evaluates inert proposal data and parser output. It does not perform identity checks, policy storage, audit persistence, or runtime execution control.

## Recommended next step

Recommended next step is human review of the dry-run approval semantics before any future ledger or executor boundary work is considered.

No subprocess/os.system/shell=True/eval/exec execution was added.

`shell_tools.py`, `executor.py`, `event_ledger.py`, providers, routing, and Cloudflare were not modified.
