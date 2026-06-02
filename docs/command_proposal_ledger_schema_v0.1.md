# CommandProposal Ledger Schema v0.1

## A. Purpose

This schema documents a future audit-log shape for proposed shell-command actions represented by `CommandProposal`.

The goal is traceability, human approval boundaries, and post-hoc review of how a proposal moved through a future approval and audit path.

GT-RUNTIME-7E is documentation only. No ledger implementation is added here.

## B. Non-execution boundary

- This schema does not execute commands.
- This schema does not approve commands.
- This schema does not write to the ledger yet.
- This schema does not modify `event_ledger.py`.
- This schema is not a sandbox or security boundary by itself.

## C. Proposed event types

- `command_proposal.created`
- `command_proposal.classified`
- `command_proposal.approval_required`
- `command_proposal.approved`
- `command_proposal.rejected`
- `command_proposal.expired`
- `command_proposal.execution_skipped`
- `command_proposal.audit_note_added`

## D. Proposed fields

- `event_id`: unique event identifier
- `event_type`: one of the proposed event types
- `timestamp_utc`: timezone-aware UTC event timestamp
- `proposal_id`: stable proposal identifier
- `command`: original proposal command string
- `normalized_command_optional`: optional normalized form for comparison or review
- `risk_level`: `safe`, `ambiguous`, `dangerous`, or `unknown`
- `reason`: classifier or reviewer explanation
- `requires_human_approval`: explicit approval requirement flag
- `source`: where the proposal originated
- `created_by`: component or process that created the proposal record
- `reviewer_id_optional`: optional reviewer identifier
- `human_decision_optional`: optional reviewer decision state
- `decision_reason_optional`: optional explanation for the decision
- `should_execute`: explicit execution intent flag, defaulting to false
- `execution_status`: current execution-path state
- `policy_version`: future policy version identifier
- `classifier_version`: future classifier version identifier
- `corpus_reference_optional`: optional reference to a corpus record or fixture
- `parent_event_id_optional`: optional event-chain parent
- `metadata`: inert structured extensions
- `provenance`: provenance or evidence payload for audit review

## E. Human decision states

- `pending`
- `approved`
- `rejected`
- `expired`
- `not_required`

## F. Execution status states

- `not_executed`
- `skipped`
- `blocked`
- `approved_not_executed`
- `future_execution_out_of_scope`

## G. Invariants

- dangerous proposals require human approval
- ambiguous proposals require human approval
- unknown proposals require human approval
- `should_execute` must default to false
- no event implies actual execution
- audit record creation is separate from command execution
- human approval is separate from execution
- event ledger must not become an executor

## H. Example JSON events

Safe proposal created:

```json
{
  "event_id": "evt-001",
  "event_type": "command_proposal.created",
  "timestamp_utc": "2026-06-02T16:50:00+00:00",
  "proposal_id": "prop-001",
  "command": "git status",
  "normalized_command_optional": "git status",
  "risk_level": "safe",
  "reason": "Read-only repository inspection",
  "requires_human_approval": false,
  "source": "unit_test_fixture",
  "created_by": "schema_example",
  "human_decision_optional": "not_required",
  "should_execute": false,
  "execution_status": "not_executed",
  "policy_version": "future-v0.1",
  "classifier_version": "future-v0.1",
  "metadata": {},
  "provenance": {
    "kind": "example"
  }
}
```

Dangerous proposal approval required:

```json
{
  "event_id": "evt-002",
  "event_type": "command_proposal.approval_required",
  "timestamp_utc": "2026-06-02T16:51:00+00:00",
  "proposal_id": "prop-002",
  "command": "rm [redacted-target]",
  "risk_level": "dangerous",
  "reason": "Destructive target marker detected",
  "requires_human_approval": true,
  "source": "adversarial_stub",
  "created_by": "schema_example",
  "human_decision_optional": "pending",
  "should_execute": false,
  "execution_status": "blocked",
  "policy_version": "future-v0.1",
  "classifier_version": "future-v0.1",
  "corpus_reference_optional": "adv-001",
  "metadata": {},
  "provenance": {
    "kind": "example"
  }
}
```

Rejected proposal:

```json
{
  "event_id": "evt-003",
  "event_type": "command_proposal.rejected",
  "timestamp_utc": "2026-06-02T16:52:00+00:00",
  "proposal_id": "prop-003",
  "command": "systemctl restart example-service",
  "risk_level": "ambiguous",
  "reason": "Administrative action requires review",
  "requires_human_approval": true,
  "source": "review_fixture",
  "created_by": "schema_example",
  "reviewer_id_optional": "reviewer-01",
  "human_decision_optional": "rejected",
  "decision_reason_optional": "Out of scope for current session",
  "should_execute": false,
  "execution_status": "blocked",
  "policy_version": "future-v0.1",
  "classifier_version": "future-v0.1",
  "metadata": {},
  "provenance": {
    "kind": "example"
  }
}
```

Execution skipped:

```json
{
  "event_id": "evt-004",
  "event_type": "command_proposal.execution_skipped",
  "timestamp_utc": "2026-06-02T16:53:00+00:00",
  "proposal_id": "prop-004",
  "command": "echo 'review note only'",
  "risk_level": "safe",
  "reason": "Captured for audit without runtime execution",
  "requires_human_approval": false,
  "source": "schema_example",
  "created_by": "schema_example",
  "human_decision_optional": "not_required",
  "should_execute": false,
  "execution_status": "skipped",
  "policy_version": "future-v0.1",
  "classifier_version": "future-v0.1",
  "metadata": {},
  "provenance": {
    "kind": "example"
  }
}
```

## I. Relation to previous milestones

- GT-RUNTIME-7A threat model: established the boundary that proposed shell commands are untrusted until reviewed.
- GT-RUNTIME-7B CommandProposal schema: introduced the inert proposal object this future ledger would describe.
- GT-RUNTIME-7C mocked approval gate: demonstrated mocked control flow where approval-required proposals are blocked before any action sink.
- GT-RUNTIME-7D adversarial corpus stub: expanded inert review material that may later be referenced by `corpus_reference_optional`.

## J. Future implementation requirements

Before implementation:

- separate design review
- tests proving `event_ledger.py` remains non-executing
- no shell execution side effects
- schema validation tests
- migration plan if persistent storage changes
- reviewer approval before modifying `runtime/tools/event_ledger.py`
