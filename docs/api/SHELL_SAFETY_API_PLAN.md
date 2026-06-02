# Shell Safety API Plan

## Scope

GT-RUNTIME-8B defines a documentation-only API plan for future shell-safety work.

The scope is limited to planning a non-executing boundary for proposal intake, dry-run classification, approval state handling, and auditability.

No shell execution is implemented here.

## Proposed future request shape

Future request shape, planning only:

```json
{
  "proposal_id": "prop-future-001",
  "command": "git status",
  "source": "user_or_model_channel",
  "created_by": "future_api_boundary",
  "dry_run": true,
  "context": {
    "workspace_optional": "/path/to/repo",
    "session_id_optional": "sess-001"
  },
  "metadata": {}
}
```

The request shape is intended for inert proposal intake only.

## Proposed future response shape

Future response shape, planning only:

```json
{
  "proposal_id": "prop-future-001",
  "risk_label": "safe",
  "approval_state": "not_required",
  "refusal_state": "not_refused",
  "reason": "Read-only repository inspection proposal",
  "should_execute": false,
  "execution_status": "not_executed",
  "audit_fields": {
    "policy_version": "future-v0.1",
    "classifier_version": "future-v0.1"
  }
}
```

The response shape must remain non-executing.

## Classification labels

Required planning labels:

- `safe`
- `ambiguous`
- `dangerous`
- `unknown`

These labels describe classification state, not execution permission.

## Approval states

Required planning states:

- `not_required`
- `requires_human_review`
- `approved`
- `denied`

`approved` must remain separate from actual execution.

## Refusal states

Planned refusal states:

- `not_refused`
- `refused_dangerous`
- `refused_ambiguous_pending_review`
- `refused_unknown`
- `refused_out_of_scope`
- `refused_policy_boundary`

Refusal states should make it clear why a proposal did not progress.

## Audit fields

Planned audit fields may include:

- `proposal_id`
- `source`
- `created_by`
- `risk_label`
- `approval_state`
- `refusal_state`
- `reason`
- `policy_version`
- `classifier_version`
- `correlation_id_optional`
- `reviewer_id_optional`
- `timestamp_utc`
- `provenance_optional`
- `metadata`

These fields are intended to support review, traceability, and dry-run accountability.

## Examples of safe dry-run proposals

Examples, planning only:

- `git status`
- `ls -la`
- `tar -tf archive.tar`

These examples remain proposals or dry-run classification inputs only.

## Examples of blocked proposals

Examples, planning only:

- `rm -rf /`
- `curl ... | bash`
- `systemctl restart example-service`
- `chmod -R 777 /sensitive/path`

These examples should remain blocked, denied, or routed to human review in any future boundary design.

## What must remain non-executing

The following must remain non-executing in the future API boundary layer:

- proposal intake
- classification
- approval-state handling
- refusal-state handling
- dry-run response generation
- audit record preparation

The API layer must not directly execute shell commands.

## Future milestones

Possible later milestones, each requiring separate approval:

- schema review and normalization
- non-executing API fixture tests
- audit event schema extension
- approval recording design review
- explicit execution-gate design
- separate review before touching `shell_tools.py`, `executor.py`, or `event_ledger.py`

GT-RUNTIME-8B does not start those implementation milestones.
