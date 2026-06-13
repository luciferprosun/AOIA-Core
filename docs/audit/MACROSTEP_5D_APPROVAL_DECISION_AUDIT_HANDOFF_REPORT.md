# Macrostep 5D Approval Decision Audit Handoff Report

## Status

Macrostep 5D is implemented as a narrow durable audit handoff for explicit `ApprovalDecision` objects.

## What Changed

- Added `runtime/safety/approval_decision_audit_handoff.py`.
- Added normal coverage in `tests/test_macrostep_5d_approval_decision_audit_handoff.py`.
- Added adversarial coverage in `tests/adversarial/test_approval_decision_audit_handoff_policy.py`.

The handoff records one approval decision audit event through the existing durable `events.jsonl` logger.

## What Did Not Change

- No artifact writer was added or called.
- No local agent entrypoint was added or called.
- No sandbox artifact writer was added or called.
- No provider, model, API, or network call was added.
- No browser, git, or cloud capability was added.
- No shell execution, subprocess, `Popen`, or `os.system` was added.
- No DB, SQLite, or ORM was added.
- No UI, web endpoint, CLI, or interactive prompt was added.
- No workspace registry or generalized SafeFileWriter was added.
- No new persistence abstraction was added.
- Existing `AuditEvent`, `ApprovalDecision`, and durable logger schemas were not changed.

## Handoff Helper API

The handoff exposes:

`record_approval_decision_to_durable_audit(approval_decision=..., audit_dir=..., expected_previous_hash=...)`

It returns `ApprovalDecisionAuditHandoffResult` with:

- `completed`;
- `approval_decision_id`;
- `approval_decision_type`;
- `audit_log_path`;
- `audit_event_id`;
- `audit_event_hash`;
- `approval_decision_payload_hash`;
- `reason`.

## Audit Event Behavior

The handoff:

- requires an explicit `ApprovalDecision`;
- requires an explicit absolute audit directory;
- validates that the decision is `APPROVE` or `REJECT`;
- validates that the decision is human reviewed;
- validates that provider-generated decisions are not accepted;
- creates one `APPROVAL_DECISION_RECORDED` audit event;
- uses the existing `create_approval_decision_audit_event(...)` helper;
- appends through the existing `append_audit_event_jsonl(...)` durable logger;
- inherits logger append-only, path, symlink, hash-chain, and fsync behavior.

If the durable logger fails, the handoff returns `completed=False` and does not claim success.

## Approve And Reject Handling

- `ApprovalDecisionType.APPROVE` is recorded as an audit event result of `APPROVE`.
- `ApprovalDecisionType.REJECT` is recorded as an audit event result of `REJECT`.
- Other approval decision types fail closed for this handoff.
- Tests verify that approve is not silently changed to reject and reject is not silently changed to approve.

## Why This Is Still Not Execution

Macrostep 5D adds a narrow non-executing durable audit handoff for explicit ApprovalDecision objects. It records approval/rejection provenance into the local durable audit trail. It does not execute anything, write artifacts, call providers, open browsers, access networks, create UI/web endpoints, use DB/SQLite/ORM, or add autonomous behavior.

An `ApprovalDecision` remains review data under the existing M4-A policy. Recording it to durable audit does not dispatch work.

## Why This Does Not Write Artifacts

The handoff writes only the durable audit `events.jsonl` line through the existing audit logger. It does not call sandbox artifact writing, local agent entrypoints, old non-durable artifact integration, or any artifact writer.

## Policy Tests

The new tests prove:

- missing or malformed approval decisions are rejected;
- relative audit directories are rejected;
- symlink audit directories and log escapes are blocked through existing logger behavior;
- existing hash-chain mismatch blocks handoff;
- logger failure returns a failed result and does not claim success;
- approve and reject are preserved correctly;
- ambiguous decision types are rejected;
- artifact writer and local agent entrypoint functions are not called;
- no forbidden runtime imports or capability calls are introduced.

## Validation Summary

Focused validation for this step:

- Macrostep 5D handoff tests: 11 OK.
- Approval decision audit handoff policy tests: 12 OK.

Full requested validation was run after implementation and is recorded in the final handoff for this commit.

## Known Residual Risks

- This is not an interactive approval surface.
- Durable audit remains local durability, not tamper-proof storage.
- A future UI/TUI/CLI must display the review packet, capture the human decision, bridge it to ApprovalDecision, and then record the ApprovalDecision audit handoff before any durable artifact run.
- The handoff records approval decision provenance but still does not authorize or trigger execution.

## Recommended Next Step

Macrostep 5E should add a narrow pre-artifact gate that requires the durable approval decision audit handoff before any durable artifact write path can proceed, while keeping execution and artifact writing separate.
