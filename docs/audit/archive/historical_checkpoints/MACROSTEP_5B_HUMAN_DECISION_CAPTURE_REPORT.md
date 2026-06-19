# Macrostep 5B Human Decision Capture Report

## Status

Macrostep 5B is implemented as a narrow non-UI decision capture layer.

## What Changed

- Added `runtime/schemas/human_decision_capture.py`.
- Added `runtime/safety/human_decision_capture_policy.py`.
- Added normal coverage in `tests/test_macrostep_5b_human_decision_capture.py`.
- Added adversarial coverage in `tests/adversarial/test_human_decision_capture_policy.py`.

The new `HumanDecisionCapture` record captures an explicit human `approve` or `deny` intent against a pending `HumanApprovalReviewPacket`.

## What Did Not Change

- No shell execution was added.
- No subprocess, `Popen`, or `os.system` was added.
- No provider, model, API, or network call was added.
- No API key or secrets handling was added.
- No browser, git, or cloud capability was added.
- No DB, SQLite, or ORM was added.
- No UI, web endpoint, CLI, or interactive prompt was added.
- No workspace registry or generalized SafeFileWriter was added.
- No durable nonce store, key management, or cryptographic approval token was added.
- Existing `ApprovalDecision` behavior was not replaced.

## Decision Capture Schema

`HumanDecisionCapture` records:

- decision version;
- stable decision id;
- stable decision hash;
- review packet id;
- review packet hash;
- explicit decision value: `approve` or `deny`;
- reviewer id;
- captured timestamp;
- original review packet decision status;
- non-execution flags.

The capture record keeps these flags false:

- `creates_approval_decision`;
- `writes_artifact`;
- `writes_audit`;
- `triggers_execution`.

## Decision Validation

The helper `capture_human_decision(...)` requires:

- a valid `HumanApprovalReviewPacket`;
- review packet status `pending`;
- explicit decision input;
- decision value exactly `approve` or `deny`;
- non-empty reviewer id;
- reviewer id no longer than 128 UTF-8 bytes;
- no blocked control characters in reviewer id or decision.

If `captured_at` is supplied, tests can assert deterministic ids and hashes. If omitted, a local UTC timestamp is recorded.

## Review Packet Binding

The capture object binds to:

- `review_packet_id`;
- deterministic `review_packet_hash`;
- decision;
- reviewer id;
- timestamp;
- reason.

Changing any bound field changes the decision hash and decision id.

## Why Capture Is Not Execution

Macrostep 5B adds a non-UI human decision capture object. It records explicit approve/deny intent against a pending HumanApprovalReviewPacket. It does not execute anything, write artifacts, append audit logs, call providers, open browsers, access networks, create UI/web endpoints, use DB/SQLite/ORM, or add autonomous behavior.

The capture object is not an `ApprovalDecision`, does not create one automatically, and does not call the durable local agent entrypoint.

## Policy Tests

The new tests prove:

- missing or malformed packets are rejected;
- non-pending review packets are rejected by the packet schema;
- invalid packet ids are rejected by the packet schema;
- automatic approval without explicit decision is impossible;
- only `approve` and `deny` are accepted;
- newline, tab, null, and control-character decision strings are rejected;
- empty, overlong, or control-character reviewer ids are rejected;
- write and entrypoint functions are not called;
- no forbidden runtime imports or capability calls are introduced.

## Validation Summary

Focused validation for this step:

- Macrostep 5B decision capture tests: 11 OK.
- Human decision capture policy tests: 12 OK.

Full requested validation was run after implementation and is recorded in the final handoff for this commit.

## Known Residual Risks

- This is not yet an interactive approval surface.
- Conversion into the existing `ApprovalDecision` flow remains separate.
- A future UI/TUI/CLI must display the review packet before accepting this decision capture.
- Durable audit remains local durability, not tamper-proof storage.
- Human identity is represented by a local reviewer id string, not a cryptographic identity.

## Recommended Next Step

Macrostep 5C should connect the review packet and decision capture to a narrow explicit approval-decision adapter, if needed, while preserving the current separation between review, decision capture, durable audit, and artifact write.
