# Macrostep 5G Approval Flow Readiness Checkpoint

## Status

Macrostep 5 non-UI approval foundation is complete.

AOIA-Core now has a non-UI controlled approval flow that can require human review, explicit human decision capture, ApprovalDecision conversion, durable approval audit handoff, a pre-artifact approval gate, and a gated durable artifact write. This is not yet an interactive UI and does not include provider calls, browser automation, shell execution, DB persistence, cloud execution, or autonomous tool use.

## Branch / HEAD / Repo State

- Branch: `feature/m2-b0-provider-critic-inert-core`
- HEAD: `b48e4af499150463355b1c1e54d90642ccef9550`
- HEAD title: `feat: add gated durable artifact flow`
- Push status: pushed to `origin/feature/m2-b0-provider-critic-inert-core`
- Repo state at baseline: clean and synced with origin

## Completed Flow

The completed non-UI approval flow is:

```text
ReviewPacket -> HumanDecisionCapture -> ApprovalDecision -> durable ApprovalDecision audit handoff -> pre-artifact approval gate -> gated durable artifact flow
```

The production-style path requires:

1. a valid `HumanApprovalReviewPacket`;
2. a valid `HumanDecisionCapture`;
3. explicit conversion into `ApprovalDecision`;
4. durable `APPROVAL_DECISION_RECORDED` audit handoff;
5. a passing 5E pre-artifact approval gate;
6. the 5F gated durable artifact flow before artifact writing.

## What 5A Closed

Macrostep 5A added `HumanApprovalReviewPacket`.

It closed the review packet gap by creating a deterministic non-UI object that records:

- goal;
- proposed action summary;
- proposed artifact path;
- run/audit context;
- required safety boundaries;
- allowed decisions: `approve`, `deny`;
- pending-only decision status.

The packet cannot approve itself, cannot execute, cannot write artifacts, and cannot append audit logs.

## What 5B Closed

Macrostep 5B added `HumanDecisionCapture`.

It closed the explicit human intent gap by recording a human `approve` or `deny` decision against a pending review packet. The capture binds to the review packet id/hash, reviewer id, timestamp, reason, and decision hash.

The capture object does not create an `ApprovalDecision` automatically, does not execute, and does not write artifacts or audit logs.

## What 5C Closed

Macrostep 5C added `create_approval_decision_from_human_capture(...)`.

It closed the conversion gap by adding a narrow explicit adapter from a valid review packet plus valid human decision capture into the existing `ApprovalDecision` flow.

Automatic approval from a packet alone remains impossible. `approve` maps to `ApprovalDecisionType.APPROVE`; `deny` maps to `ApprovalDecisionType.REJECT`.

## What 5D Closed

Macrostep 5D added `record_approval_decision_to_durable_audit(...)`.

It closed the durable approval provenance gap by recording explicit `ApprovalDecision` objects to the local durable `events.jsonl` audit log as `APPROVAL_DECISION_RECORDED`.

The handoff supports both `APPROVE` and `REJECT`, uses the existing durable audit logger, and does not write artifacts or run the local agent entrypoint.

## What 5E Closed

Macrostep 5E added `evaluate_pre_artifact_approval_gate(...)`.

It closed the pre-artifact gate gap by requiring an explicit `APPROVE` `ApprovalDecision` paired with a completed matching durable approval audit handoff.

`REJECT` cannot pass. Missing, failed, mismatched, malformed, or forged handoff data fails closed. The gate itself does not write artifacts, append audit logs, execute, or call providers.

## What 5F Closed

Macrostep 5F added `run_gated_durable_artifact_flow(...)`.

It closed the explicit gated production-style artifact path gap by requiring:

- review packet;
- human decision capture;
- ApprovalDecision bridge;
- durable ApprovalDecision audit handoff;
- passing 5E gate;
- existing durable artifact helper after the gate.

`APPROVE` writes only after completed matching durable handoff and passing gate. `REJECT` blocks artifact write. Audit handoff failure blocks artifact write. Forged or mismatched packet/capture/handoff data fails closed. The old non-durable path is not called by the new flow, and old compatibility paths remain unchanged.

## Current Validation Baseline

Latest known Macrostep 5F validation baseline:

- `python3 -m compileall -q runtime tests`: OK
- M4-A approval decision layer: 18 OK
- M5-A append-only audit event layer: 20 OK
- M5-B proposal decision audit bridge: 18 OK
- M8 workspace-bound sandbox artifact runner: 27 OK
- M9 dry-run artifact integration: 27 OK
- M10 controlled agent demo flow: 27 OK
- adversarial path safety: 16 OK
- adversarial resource limits: 8 OK
- adversarial state bypass: 10 OK
- adversarial audit persistence: 14 OK
- adversarial durable approval binding: 11 OK
- Macrostep 3A durable local agent entrypoint: 10 OK
- Macrostep 4A local workspace run context: 11 OK
- Macrostep 4B local run status: 12 OK
- Macrostep 5A review packet: 11 OK
- Macrostep 5B decision capture: 11 OK
- Macrostep 5C decision-to-approval bridge: 11 OK
- Macrostep 5D approval decision audit handoff: 11 OK
- Macrostep 5E pre-artifact approval gate: 10 OK
- Macrostep 5F gated durable artifact flow: 12 OK
- 5F gated durable artifact flow policy: 12 OK
- full suite: 1138 OK / 4 skipped
- `node --check web/app.js`: OK
- `git diff --check`: OK
- static forbidden scan: no real forbidden runtime capability added; literal docs/tests false positives may appear

## Current Safety State

- no shell/subprocess/Popen/os.system added;
- no provider/API/network added;
- no DB/SQLite/ORM added;
- no SafeFileWriter added;
- no workspace registry added;
- no UI/web endpoint added;
- no UI/TUI/CLI approval prompt added;
- no browser automation added;
- no cloud/GCP execution added;
- no autonomous background behavior added;
- old compatibility paths remain but are outside the new gated production path.

## UI Boundary

UI design and UI implementation are not approved yet.

Before UI/TUI/CLI/web approval surface work begins, AOIA-Core must pass a PRE-UI audit.

This checkpoint does not add UI, TUI, CLI, web endpoints, provider/model picker, browser automation, provider calls, shell execution, DB persistence, cloud execution, workspace registry, SafeFileWriter, or autonomous behavior.

## PRE-UI Audit Questions To Ask Next

1. Should UI be web, TUI, CLI, or staged TUI-first?
2. How should the UI display `HumanApprovalReviewPacket`?
3. How should approve/deny be captured without allowing auto-approval?
4. How should the UI call the 5F gated durable artifact flow?
5. How should old compatibility paths be hidden or blocked from UI?
6. How should provider/model picker be designed later?
7. How should connected providers/models be shown based on user API configuration?
8. How should provider/model output remain UNTRUSTED?
9. How should OpenRouter/Gemini/OpenAI-compatible/local providers remain manual-only?
10. What tests are required before any UI code exists?

## Known Residual Risks

- no interactive approval surface yet;
- durable audit is local durability, not tamper-proof storage;
- old compatibility paths remain;
- no provider/model picker yet;
- no UI exists yet;
- provider/browser/shell/tool execution remains out of scope;
- human identity is still a local reviewer id string, not cryptographic identity;
- PRE-UI architecture choices are not audited yet.

## Recommended Next Step

PRE-UI AUDIT: large external/model audit before any UI design or UI implementation.
