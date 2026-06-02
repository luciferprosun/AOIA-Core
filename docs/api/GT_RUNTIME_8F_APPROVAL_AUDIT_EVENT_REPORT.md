# GT-RUNTIME-8F Approval Audit Event Report

## Starting branch and HEAD

- Starting branch: `dev/gt-runtime-8-bash-safety-planning`
- Starting HEAD: `8f8bde8 fix: harden GT-RUNTIME-8E approval gate`

## Purpose

GT-RUNTIME-8F adds an inert approval audit event schema that records the relationship between a `CommandProposal`, an `ApprovalDecision`, and caller-supplied timestamp/context metadata.

This milestone improves auditability and provenance shape without adding persistence, logging, shell execution, terminal integration, ledger integration, provider changes, or routing changes.

## Files added/updated

Added:

- `runtime/schemas/approval_audit_event.py`
- `tests/test_approval_audit_event.py`
- `docs/api/GT_RUNTIME_8F_APPROVAL_AUDIT_EVENT_REPORT.md`

Updated:

- `runtime/schemas/__init__.py`

## ApprovalAuditEvent shape

`ApprovalAuditEvent` is frozen/data-only.

Fields:

- `event_id`
- `event_type`
- `created_at_utc`
- `source`
- `raw_command`
- `normalized_command`
- `classification`
- `proposal_approval_state`
- `decision_approval_state`
- `decision_allowed`
- `execution_permitted`
- `dry_run`
- `requires_human_review`
- `proposal_reason`
- `decision_reason`

The only GT-RUNTIME-8F event type is `approval_decision_dry_run`.

## Deterministic helper constructor

`from_proposal_and_decision` copies fields only; it does not execute, persist, or log externally.

`event_id` and `created_at_utc` are passed in for deterministic testing. The helper does not generate timestamps or UUIDs internally.

## What the event records

The event records:

- proposal command text and classification
- proposal approval state and reason
- decision approval state and reason
- whether the decision was allowed as dry-run
- whether human review is required
- whether execution is permitted

`execution_permitted` is always `False`.

## What remains non-executing

GT-RUNTIME-8F does not execute shell commands.

No filesystem/network logging was added.

No subprocess/os.system/shell=True/eval/exec execution was added.

## Why event_ledger.py was not modified

`event_ledger.py` was intentionally not modified in GT-RUNTIME-8F.

This milestone defines an inert event shape only. It does not add persistence, append behavior, audit storage, or ledger integration.

## Validation performed

Planned validation:

- `python3 -m compileall runtime tests`
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`
- `grep -nR -E '(os\\.system|subprocess|shell\\s*=\\s*True|eval|exec)\\s*\\(' runtime/schemas/approval_audit_event.py || true`
- `grep -nR -E '(open|pathlib|os\\.path|urllib|requests|http|socket|importlib|import)\\s*\\(|import (os|subprocess|shutil|sys|importlib)' runtime/schemas/approval_audit_event.py || true`
- `grep -RIn "event_ledger" runtime/schemas/approval_audit_event.py tests/test_approval_audit_event.py docs/api/GT_RUNTIME_8F_APPROVAL_AUDIT_EVENT_REPORT.md 2>/dev/null || true`

## Limitations

The schema is a provenance shape, not an audit log implementation.

It does not verify timestamps beyond requiring a non-empty string, does not persist records, and does not integrate with runtime ledger code.

## Recommended next step

Recommended next step is human review of the audit event shape before a separate explicit phase gate considers any ledger schema or persistence integration.

`shell_tools.py`, `executor.py`, `event_ledger.py`, providers, routing, and Cloudflare were not modified.
