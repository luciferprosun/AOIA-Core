# Macrostep 5F - Gated Durable Artifact Flow Report

## What Changed

Macrostep 5F adds a new explicit gated durable artifact flow. The flow requires a review packet, explicit human decision capture, ApprovalDecision conversion, durable ApprovalDecision audit handoff, and a passing pre-artifact approval gate before artifact writing. It does not add shell execution, provider calls, browser automation, git automation, cloud execution, DB/SQLite/ORM, UI, web endpoints, workspace registry, generalized file writer, or autonomous behavior.

Added:

- `runtime/safety/gated_durable_artifact_flow.py`
- `tests/test_macrostep_5f_gated_durable_artifact_flow.py`
- `tests/adversarial/test_gated_durable_artifact_flow_policy.py`

Updated:

- `runtime/safety/dry_run_artifact_integration.py`

The update is a narrow compatibility addition that lets the existing durable artifact helper use an already recorded audit event as chain context while appending only the new dry-run artifact events.

## What Did Not Change

Old compatibility paths remain. The existing non-durable artifact integration and durable local entrypoint were not removed or silently changed.

No provider/client modules, browser modules, shell/executor modules, web UI files, GCP/cloud/deploy files, workspace registry, SafeFileWriter, DB layer, UI, CLI, or background loop were added.

## New Explicit Gated Flow API

The new helper is:

```python
run_gated_durable_artifact_flow(
    *,
    review_packet: HumanApprovalReviewPacket,
    decision_capture: HumanDecisionCapture,
    workspace_root: str | Path,
    audit_dir: str | Path,
    relative_output_path: str = "aoia_agent_v0_result.md",
) -> GatedDurableArtifactFlowResult
```

The result records:

- `completed`
- `approval_decision_id`
- `approval_decision_type`
- `approval_audit_event_id`
- `approval_audit_event_hash`
- `gate_allowed`
- `artifact_write_completed`
- `artifact_path`
- `audit_log_path`
- `reason`

## Approval Sequence

The flow requires:

1. a valid `HumanApprovalReviewPacket`;
2. a valid `HumanDecisionCapture`;
3. explicit conversion through `create_approval_decision_from_human_capture(...)`;
4. a durable ApprovalDecision audit handoff through `record_approval_decision_to_durable_audit(...)`;
5. a passing `evaluate_pre_artifact_approval_gate(...)`;
6. the existing durable artifact helper after the gate passes.

## Audit Handoff Sequence

The ApprovalDecision is recorded first as `APPROVAL_DECISION_RECORDED` in durable `events.jsonl`. The existing durable artifact helper then appends its dry-run artifact audit events after that approval handoff event in the same hash chain.

If the approval handoff fails or produces mismatched data, no artifact path is invoked.

## 5E Gate Behavior

The 5E gate must allow before artifact writing. `APPROVE` can pass only with a completed matching durable approval audit handoff. `REJECT` does not pass. Missing, failed, mismatched, or forged handoff data fails closed.

## Artifact Write Behavior

Artifact writing uses the existing durable dry-run artifact helper after the gate passes. The flow does not call the old non-durable artifact path.

The flow also requires the output path to match the path shown in the review packet.

## Reject/Failure Behavior

The flow writes no artifact when:

- the review packet is missing or malformed;
- the decision capture is missing or malformed;
- packet/capture binding is mismatched;
- ApprovalDecision conversion fails;
- approval audit handoff fails;
- the pre-artifact approval gate denies;
- the decision is `REJECT`;
- the durable artifact helper fails before artifact write.

## Compatibility Paths

Old compatibility paths remain available and unchanged. They are outside the new gated production path.

## Policy Tests

Policy tests cover:

- packet alone cannot write artifacts;
- decision capture alone cannot write artifacts;
- ApprovalDecision alone cannot write artifacts;
- approval audit handoff alone cannot write artifacts;
- forged packet/capture binding fails closed;
- forged approval handoff fails closed;
- `REJECT` cannot be treated as `APPROVE`;
- provider/model text cannot satisfy the gate;
- audit append failure prevents artifact creation;
- artifact writer is not called when the gate denies;
- no forbidden runtime capability is introduced.

## Validation Summary

Validation was run for compile checks, targeted regression suites, Macrostep 5A through 5F suites, adversarial policy suites, the full unittest suite, Node syntax check, whitespace diff check, git status, and static forbidden capability scan.

## Known Residual Risks

This is still not an interactive approval surface. Old compatibility paths remain but are outside the new gated production path. Durable audit remains local durability, not tamper-proof storage. A future UI/TUI/CLI must display the review packet and use this gated flow or an equivalent audited path.

## Next Recommended Step

Add a future UI/TUI/CLI approval surface that displays the review packet, captures the human decision, and calls this gated durable artifact flow for production-style artifact writes.
