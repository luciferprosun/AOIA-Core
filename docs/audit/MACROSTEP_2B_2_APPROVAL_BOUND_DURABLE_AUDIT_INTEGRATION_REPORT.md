# Macrostep 2B-2 - Approval-Bound Durable Audit Integration

## Status

Macrostep 2B-2 is complete.

## What Changed

Macrostep 2B-2 adds an explicit durable-audit-bound artifact integration path:

- `run_dry_run_agent_and_write_artifact_with_durable_audit(...)`
- `DurableDryRunArtifactIntegrationResult`
- adversarial durable approval binding tests

The new path runs the existing local dry-run flow, appends the produced audit events to the durable JSONL audit log, and only then calls the workspace-bound sandbox artifact writer.

## Durable Approval Binding Rule

In the durable path:

1. The dry-run agent loop creates the in-memory audit chain.
2. Each audit event is appended to the explicit durable audit directory.
3. Durable append must complete with fsync.
4. The artifact request is bound to the latest durable audit event id.
5. The workspace-bound artifact writer is called only after durable audit append succeeds.

If durable audit append fails, artifact writing does not occur.

## Happens-Before Behavior

The durable path enforces:

```text
ApprovalDecision / AuditEvent exists
-> durable events.jsonl append succeeds
-> SandboxArtifactRequest is bound to durable audit event id
-> workspace-bound artifact write may proceed
```

Tests verify that the durable `events.jsonl` file exists before the artifact writer is entered.

## Audit Failure Behavior

The artifact write fails closed when durable audit logging fails.

Covered failure cases:

- durable append failure
- symlinked/invalid audit directory
- invalid existing durable audit hash chain
- expected previous hash mismatch

In these cases, no artifact file is created.

## Old Non-Durable Path

The existing M9 function remains available:

- `run_dry_run_agent_and_write_artifact(...)`

It is intentionally unchanged for compatibility and remains the non-durable local integration path. Durable approval binding is available through the new explicit durable function only.

## What Did Not Change

Macrostep 2B-2 did not add:

- shell execution
- subprocess / Popen / os.system
- provider/API/network calls
- API key or secrets handling
- browser automation
- git automation
- cloud/GCP execution
- DB/SQLite/ORM
- autonomous background loop
- new UI
- workspace registry
- generalized SafeFileWriter
- `runtime/safety/safe_file_writer.py`
- `runtime/safety/workspace_registry.py`
- cryptographic approval token
- key management
- durable nonce store
- new agent capability

The integration remains local, deterministic, and one-shot.

## Tests Added

Added:

- `tests/adversarial/test_durable_approval_binding.py`

The tests prove:

- controlled artifact integration can run with an explicit durable audit directory
- durable audit log is written before artifact file appears
- durable audit append failure blocks artifact write
- invalid/symlinked audit directory blocks artifact write
- invalid existing audit hash chain blocks artifact write
- expected previous hash mismatch blocks artifact write
- durable audit event id/hash matches the structural artifact contract binding where available
- artifact contract guard still rejects malformed state
- existing M9 non-durable path remains unchanged
- existing M10 controlled demo still passes
- no forbidden shell/provider/network/DB/browser/git/cloud/SafeFileWriter/workspace registry capability is introduced

## Safety State

AOIA-Core now has an explicit controlled artifact path where durable audit append happens before workspace-bound artifact write.

This improves local crash/restart evidence for the controlled artifact flow. It is still local durability, not tamper-proof storage and not cryptographic authorization.

## Known Residual Risks

- Durable audit integration is not tamper-proof against a local attacker with filesystem access.
- The structural artifact contract remains a code-review guardrail, not cryptographic authorization.
- The old non-durable M9 path remains available for compatibility and must be treated as non-durable.
- A future step may decide whether all product entrypoints should require the durable path.
- Workspace registry remains intentionally deferred.

## Recommended Next Step

Recommended next normal AOIA-Core production step:

- Macrostep 2B-3 or 2C: narrow entrypoint policy cleanup deciding where durable audit is mandatory, without adding UI, browser, provider, shell, cloud, DB, workspace registry, or generalized file writing.
