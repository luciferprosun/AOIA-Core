# M4-A ApprovalDecision Layer Report

M4-A implements the ApprovalDecision layer for ActionProposal review.

ApprovalDecision records human or system review decisions: approve, reject,
needs changes, defer, and blocked by policy. These records are audit/review
objects only.

Human approval does not execute. A human approval decision keeps
execution_permitted false and execution_triggered false.

Provider/model approval is blocked. Provider-generated decisions and
PROVIDER_MODEL actors cannot approve actions.

Timeout or missing decision cannot approve. Expired decisions are blocked.

Payload hash mismatch blocks execution classification. ApprovalDecision records
the exact ActionProposal payload hash reviewed by the actor.

All execution remains blocked in M4-A. M4-A does not add sandbox execution, an
agent loop, shell execution, browser automation, git automation, filesystem
write/delete/move action capability, cloud/deploy capability, provider/API
calls, network calls, GCP changes, or API key/secrets handling.

Existing M2, Evidence, and M3-A boundaries remain intact:

- Provider critique remains untrusted and cannot create executable actions.
- Evidence Memory records remain evidence data and cannot execute or approve actions.
- ActionProposal remains inert and cannot permit runtime execution.
- Human approval remains a review record, not an authorization to run anything.

Recommended next production step: M5-A append-only audit event layer or M4-B
approval-to-audit bridge, still no execution.
