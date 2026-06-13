# M10-A Controlled Agent Demo Flow Report

Date: 2026-06-13

Repository: `/home/l/Desktop/AOIA-Core`

Branch: `feature/m2-b0-provider-critic-inert-core`

## Summary

M10-A implements the controlled agent demo task flow.

The flow accepts a human goal and builds a deterministic local plan.

The flow uses M9-A integration to produce one safe artifact inside an explicit sandbox workspace.

The flow is one-shot and not autonomous.

## Safety Boundary

No shell execution was added.

No subprocess, `Popen`, or `os.system` capability was added.

No provider/API/network/GCP/secrets handling was added.

No browser/git/cloud capability was added.

No arbitrary filesystem capability was added.

The deterministic plan is local and template-based only.

The only write path is the M9-A integration path through the M8-A workspace-bound artifact runner.

Absolute paths remain blocked.

Path traversal remains blocked.

`.git` writes remain blocked.

Unsafe extensions remain blocked.

Symlink escape remains blocked.

## Existing Boundaries Preserved

Existing M2-B0, M2-B1, M2-B2, M2-B3, Evidence-1, M3-A, M4-A, M5-A, M5-B, M6-A, M7-A, M8-A, and M9-A boundaries remain intact.

Provider output remains untrusted.

Approval records still do not execute.

Audit events and the proposal-decision-audit bridge remain non-authorizing.

The sandbox contract still does not authorize arbitrary execution.

The workspace-bound artifact runner remains limited to safe text, JSON, or Markdown artifacts inside an explicit sandbox workspace.

## Validation

Required validation for this phase:

```bash
python3 -m compileall -q runtime tests
python3 -m unittest tests.test_m2_b0_provider_critic_inert_core -v
python3 -m unittest tests.test_m2_b1_provider_gateway_redaction -v
python3 -m unittest tests.test_m2_b2_provider_call_limits_audit -v
python3 -m unittest tests.test_m2_b3_cpt_no_auto_send_boundary -v
python3 -m unittest tests.test_evidence_memory_intake_boundary -v
python3 -m unittest tests.test_m3_a_action_proposal_inert_layer -v
python3 -m unittest tests.test_m4_a_approval_decision_layer -v
python3 -m unittest tests.test_m5_a_append_only_audit_event_layer -v
python3 -m unittest tests.test_m5_b_proposal_decision_audit_bridge -v
python3 -m unittest tests.test_m6_a_sandbox_contract_no_execution -v
python3 -m unittest tests.test_m7_a_dry_run_agent_loop_no_execution -v
python3 -m unittest tests.test_m8_a_workspace_bound_sandbox_artifact_runner -v
python3 -m unittest tests.test_m9_a_dry_run_artifact_integration -v
python3 -m unittest tests.test_m10_a_controlled_agent_demo_flow -v
python3 -m unittest discover -s tests
node --check web/app.js
git diff --check
```

## Next Step

Product checkpoint, external technical review, or the next normal AOIA-Core production macrostep.
