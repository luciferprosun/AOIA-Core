# M8-A Workspace-bound Sandbox Artifact Runner Report

Date: 2026-06-13

Repository: `/home/l/Desktop/AOIA-Core`

Branch: `feature/m2-b0-provider-critic-inert-core`

## Summary

M8-A implements a workspace-bound sandbox artifact runner.

The only allowed execution-like behavior is writing safe text, JSON, or Markdown artifacts inside an explicit sandbox workspace.

No shell execution was added.

No subprocess was added.

No provider/API/network/GCP/secrets handling was added.

No browser/git/cloud capability was added.

No arbitrary filesystem capability was added.

## Safety Boundary

Artifact writes require an explicit workspace root.

Artifact output paths must be relative.

Absolute paths are blocked.

Path traversal is blocked.

`.git` paths are blocked.

Unsafe extensions are blocked.

Symlink escape is blocked.

Overwrite is blocked by default and only allowed inside the already validated workspace when explicitly requested.

Human approval alone does not enable arbitrary execution.

`AuditEvent`, the proposal-decision-audit bridge, and the sandbox contract still do not authorize arbitrary execution.

## Out Of Scope

- No shell runner.
- No command runner.
- No sandbox command execution.
- No provider/model call.
- No browser automation.
- No git automation.
- No cloud operation.
- No arbitrary filesystem write.
- No background loop.
- No retries, polling, cron, timers, or auto-send.

## Existing Boundaries Preserved

Existing M2-B0, M2-B1, M2-B2, M2-B3, Evidence-1, M3-A, M4-A, M5-A, M5-B, M6-A, and M7-A boundaries remain intact.

Provider output remains untrusted.

Approval records review state only.

Audit events remain non-authorizing records.

The dry-run agent loop remains non-executing.

The sandbox artifact runner does not authorize any further action.

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
python3 -m unittest discover -s tests
node --check web/app.js
git diff --check
```

## Next Step

M9-A Workspace Guard integration with dry-run agent loop, or M8-B demo artifact task flow.
