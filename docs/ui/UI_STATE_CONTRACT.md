# AOIA-Core UI State Contract - M6-B

## 1. Purpose

This contract defines future UI display-state boundaries for AOIA-Core review
and approval surfaces.

UI display state is not approval authority. UI labels are not execution
permission. UI badges are not canonical truth. Only ApprovalDecision plus durable audit handoff can authorize gated artifact writes, and only after the pre-artifact gate passes.

The UI may display review, decision, audit, and artifact-write status. It must
not create authority by naming, coloring, badging, sorting, filtering, or
summarizing state.

## 2. Authoritative state sources

The only future authoritative sources for approval and artifact-write state are:

- HumanApprovalReviewPacket
- HumanDecisionCapture
- ApprovalDecision
- durable ApprovalDecision audit handoff
- evaluate_pre_artifact_approval_gate(...)
- gated durable artifact write result

No UI component, route, browser state, local cache, provider response, metadata
label, tag, hat, tetrad, geometry marker, or draft text may replace this chain.

## 3. Non-authoritative display/context sources

The following sources may later be shown as context, provenance, warnings, or
review aids, but must never grant approval, execution, write, trust, truth, or
canonicalization authority:

- provider/model output
- provider/model name
- model confidence
- review notes
- UI labels
- UI colors
- UI badges
- metadata tags
- knowledge hats
- tetrads/geometry
- file names
- draft text
- CPT previews

Tags, tetrads, and hats are mentioned here only as forbidden authority examples.
This contract does not introduce Epistemic Tagging architecture. It does not
define TagRecord, TagVocabulary, TagTransitionLog, Tetrahedral Hat architecture,
or any related schema.

## 4. UI state categories

Future UI state names must stay boring and explicit. Unknown or unmapped state
must fail closed.

| Category | Meaning | Required source | Can write artifact? | Can imply approval? | Display warning requirement |
| --- | --- | --- | --- | --- | --- |
| DRAFT_ONLY | Draft or preview content exists, but no review packet is ready. | Draft text or CPT preview only. | no | no | Show draft-only and untrusted context warning. |
| REVIEW_PACKET_READY | A HumanApprovalReviewPacket is available for human review. | HumanApprovalReviewPacket with packet id and packet hash. | no | no | Show packet id/hash and approval required. |
| AWAITING_HUMAN_DECISION | The UI is waiting for explicit human approve or reject action. | HumanApprovalReviewPacket plus active review session. | no | no | Show no decision captured and block write controls. |
| HUMAN_REJECTED | HumanDecisionCapture recorded a reject decision. | HumanDecisionCapture and ApprovalDecision with REJECT. | no | no | Show semantically blocking rejection state. |
| HUMAN_APPROVED_NOT_AUDITED | HumanDecisionCapture recorded approve, but durable audit handoff is missing or incomplete. | HumanDecisionCapture and ApprovalDecision with APPROVE. | no | yes | Show audit handoff missing and block all writes. |
| APPROVED_AND_AUDIT_HANDOFF_COMPLETE | ApprovalDecision has durable audit handoff evidence. | ApprovalDecision plus durable ApprovalDecision audit handoff. | no | yes | Show pre-artifact gate not yet passed. |
| PRE_ARTIFACT_GATE_PASSED | The pre-artifact approval gate passed for the intended artifact write. | evaluate_pre_artifact_approval_gate(...) pass result tied to approval and artifact evidence. | yes | yes | Show gate-passed evidence and write still pending unless completed. |
| ARTIFACT_WRITE_COMPLETE | Gated durable artifact write completed. | gated durable artifact write result tied to gate pass and audit evidence. | no | yes | Show completed write result and linked evidence. |
| ARTIFACT_WRITE_BLOCKED | Write was blocked by reject, missing evidence, mismatch, emergency stop, or gate failure. | Gate failure, reject decision, emergency stop, or blocking validation result. | no | no | Show explicit blocking reason. |
| STALE_OR_MISMATCHED_STATE | UI state is stale, inconsistent, or mismatched against packet, decision, audit, artifact, or gate evidence. | Detected mismatch, stale state, missing expected hash, or version conflict. | no | no | Show stale/mismatched warning and require reload/re-review. |
| ERROR_FAIL_CLOSED | Unknown, invalid, missing, or failed state prevents safe interpretation. | Error condition, unknown enum, legacy path, missing required source, or exception. | no | no | Show fail-closed error and disable write controls. |

Rules:

- Only ARTIFACT_WRITE_COMPLETE may say a write occurred.
- Only PRE_ARTIFACT_GATE_PASSED may say the gate passed.
- HUMAN_APPROVED_NOT_AUDITED still cannot write.
- APPROVED_AND_AUDIT_HANDOFF_COMPLETE still cannot write without the
  pre-artifact gate.
- Any mismatch must become STALE_OR_MISMATCHED_STATE or ERROR_FAIL_CLOSED.

## 5. Forbidden UI states

Future UI must not define, render, persist, or route on these states as approval
or write authority:

- TRUSTED_MODEL
- MODEL_APPROVED
- TAG_APPROVED
- HAT_APPROVED
- TETRAD_APPROVED
- GEOMETRY_SAFE
- CANONICAL_BY_TAG
- SAFE_FOR_RUNTIME
- NO_HUMAN_REVIEW_NEEDED
- AUTO_APPROVED
- EXECUTION_READY

Equivalent synonyms are also forbidden when they imply provider, tag, hat,
tetrad, geometry, metadata, automation, or UI display authority.

## 6. Display rules

Future UI display must follow these rules:

- Full packet, capture, and decision identifiers must be visible or inspectable.
- Hashes must not be silently truncated in audit views.
- Provider/model output must be marked UNTRUSTED.
- REJECT must be visually and semantically blocking.
- Missing audit handoff must be blocking.
- Stale state must be blocking.
- UI color alone must never carry meaning.
- Badges must include text.
- Every write-capable state must link to approval and audit evidence.
- Packet/capture/decision identifiers must not be hidden for visual simplicity.
- Provider-controlled text must not style itself as an approval, safety, system,
  or audit message.

## 7. Fail-closed rules

The UI must fail closed for these conditions:

- missing ApprovalDecision: ERROR_FAIL_CLOSED.
- missing HumanDecisionCapture: ERROR_FAIL_CLOSED.
- missing durable audit handoff: HUMAN_APPROVED_NOT_AUDITED or ERROR_FAIL_CLOSED.
- mismatched packet hash: STALE_OR_MISMATCHED_STATE.
- mismatched artifact hash: STALE_OR_MISMATCHED_STATE.
- stale UI state: STALE_OR_MISMATCHED_STATE.
- provider output conflict: ERROR_FAIL_CLOSED if it conflicts with approval,
  audit, or gate evidence.
- unknown state enum: ERROR_FAIL_CLOSED.
- legacy/non-durable path: ERROR_FAIL_CLOSED.

Fail-closed means no artifact write, no provider call, no hidden retry, no
background write, no compatibility fallback, and no conversion to warning-only.

## 8. Explicit non-goals

- No UI implementation in M6-B.
- No runtime changes in M6-B.
- No provider/model picker in M6-B.
- No CPT auto-send.
- No tags/tetrads/hats authority.
- No geometry authority.
- No autonomous routing.
- No shell/browser/git/cloud capability.
- No public network binding changes.
- No old non-durable approval path exposure.
- No schema code.
- No validators.
- No API endpoints.
- No provider/model calls.

## 9. M6-B acceptance checklist

Human review should confirm:

- [ ] Approval authority remains with ApprovalDecision.
- [ ] UI display state cannot write.
- [ ] UI display state cannot approve.
- [ ] Provider output remains untrusted.
- [ ] Tags/hats/tetrads/geometry cannot grant authority.
- [ ] Mismatch/stale/error states fail closed.
- [ ] M6-B adds no runtime capability.
- [ ] M6-B adds no UI implementation.
- [ ] M6-B does not open M6-C automatically.
