# Macrostep 5C Human Decision To Approval Bridge Report

## Status

Macrostep 5C is implemented as a narrow non-UI adapter from human decision capture into the existing `ApprovalDecision` flow.

## What Changed

- Added `runtime/safety/human_decision_to_approval_policy.py`.
- Added normal coverage in `tests/test_macrostep_5c_human_decision_to_approval_bridge.py`.
- Added adversarial coverage in `tests/adversarial/test_human_decision_to_approval_policy.py`.

The adapter creates an `ApprovalDecision` only from an explicit `HumanApprovalReviewPacket` plus an explicit `HumanDecisionCapture`.

## What Did Not Change

- No `ApprovalDecision` schema replacement was made.
- No `HumanApprovalReviewPacket` schema change was made.
- No `HumanDecisionCapture` schema change was made.
- No shell execution was added.
- No subprocess, `Popen`, or `os.system` was added.
- No provider, model, API, or network call was added.
- No API key or secrets handling was added.
- No browser, git, or cloud capability was added.
- No DB, SQLite, or ORM was added.
- No UI, web endpoint, CLI, or interactive prompt was added.
- No workspace registry or generalized SafeFileWriter was added.
- No audit logger or artifact writer call was added.

## Bridge Helper API

The bridge exposes:

`create_approval_decision_from_human_capture(review_packet=..., decision_capture=...)`

It returns an `ApprovalDecision` and fails closed on missing, malformed, mismatched, or tampered inputs.

## Validation Rules

The bridge requires:

- a valid `HumanApprovalReviewPacket`;
- a valid `HumanDecisionCapture`;
- review packet status `pending`;
- decision capture status-before `pending`;
- decision capture value exactly `approve` or `deny`;
- decision capture packet id matching the review packet id;
- decision capture packet hash matching the deterministic review packet hash;
- decision capture id and hash valid under Macrostep 5B rules.

## Review Packet Binding

The returned `ApprovalDecision` binds to the review packet by:

- using the review packet proposal id when present;
- using the deterministic review packet hash as `reviewed_exact_payload_hash`;
- storing the review packet id and hash in `notes`.

The current `ApprovalDecision` schema does not have dedicated packet metadata fields, so packet provenance is carried through existing non-executing text/hash fields.

## Decision Capture Binding

The returned `ApprovalDecision` binds to the human decision capture by:

- deriving deterministic approval decision id material from capture id and hash;
- preserving reviewer id as the human actor id;
- preserving capture timestamp as `created_at`;
- preserving capture reason when present;
- storing capture id and hash in `notes`.

## Approve And Deny Handling

- `approve` becomes `ApprovalDecisionType.APPROVE`.
- `deny` becomes `ApprovalDecisionType.REJECT`.
- Deny cannot become approve through the bridge tests.
- All resulting approval decisions keep `execution_permitted=False` and `execution_triggered=False`.

## Why This Is Still Not Execution

Macrostep 5C adds a narrow non-UI adapter from a validated HumanDecisionCapture into the existing ApprovalDecision flow. It requires an explicit review packet and explicit human decision capture. It does not execute anything, write artifacts, append audit logs, call providers, open browsers, access networks, create UI/web endpoints, use DB/SQLite/ORM, or add autonomous behavior.

An `ApprovalDecision` remains review data under the existing M4-A policy and does not dispatch work.

## Why This Does Not Write Audit Or Artifact

The bridge only constructs an in-memory `ApprovalDecision`. It does not call durable audit logger helpers, sandbox artifact writers, local agent entrypoints, old non-durable paths, or filesystem persistence helpers.

## Policy Tests

The new tests prove:

- missing or malformed review packets are rejected;
- non-pending review packets are rejected;
- missing or malformed decision captures are rejected;
- packet id mismatch is rejected;
- packet hash mismatch is rejected;
- decision id/hash tampering is rejected;
- decisions outside `approve` or `deny` are rejected;
- automatic approval from packet alone is impossible;
- provider/model/untrusted packet text cannot become an `ApprovalDecision` without capture;
- deny is converted to reject, not approve;
- writer and entrypoint functions are not called;
- no forbidden runtime imports or capability calls are introduced.

## Validation Summary

Focused validation for this step:

- Macrostep 5C bridge tests: 11 OK.
- Human decision to approval policy tests: 14 OK.

Full requested validation was run after implementation and is recorded in the final handoff for this commit.

## Known Residual Risks

- This is not yet an interactive approval surface.
- A future UI/TUI/CLI must display the review packet before accepting human decision capture.
- Conversion to ApprovalDecision is explicit but still not execution.
- Durable audit remains local durability, not tamper-proof storage.
- The current `ApprovalDecision` schema has no dedicated review packet or capture metadata fields, so bridge provenance is carried through existing hash, summary, id, actor, reason, and notes fields.

## Recommended Next Step

Macrostep 5D should add a narrow local audit handoff for the explicit approval decision, if needed, while preserving the separation between review packet creation, human decision capture, approval decision conversion, durable audit, artifact write, and execution.
