# Macrostep 3A - Durable Local Agent Entrypoint Scaffold

## Status

Macrostep 3A is complete.

## What Changed

Macrostep 3A adds a local durable controlled-agent entrypoint scaffold:

- `runtime/safety/local_agent_entrypoint.py`
- `tests/test_macrostep_3a_durable_local_agent_entrypoint.py`
- `tests/adversarial/test_local_agent_entrypoint_policy.py`

The entrypoint accepts a human goal, validates it locally, builds a deterministic dry-run request, and routes it through the existing durable audit-bound artifact path.

## New Entrypoint API

```python
run_durable_local_agent_entrypoint(
    *,
    goal: str,
    workspace_root: str | Path,
    audit_dir: str | Path,
    relative_output_path: str = "aoia_agent_v0_result.md",
    approval_actor_id: str = "human-reviewer",
) -> LocalAgentEntrypointResult
```

Returned result:

- `completed`
- `durable_audit_required`
- `durable_audit_completed`
- `artifact_write_completed`
- `workspace_root`
- `audit_log_path`
- `artifact_path`
- `reason`

## Durable Path Requirement

The new entrypoint uses:

- `run_dry_run_agent_and_write_artifact_with_durable_audit(...)`

It does not call the old non-durable compatibility path:

- `run_dry_run_agent_and_write_artifact(...)`

The old function remains in the repository for compatibility, but Macrostep 3A does not use it.

## Local Validation

The entrypoint validates before calling the durable flow:

- goal must be non-empty after stripping whitespace
- goal length is limited to `4096` characters
- null/control characters are rejected, except tab and newline
- workspace root must be explicit
- audit directory must be explicit
- workspace root must be absolute
- audit directory must be absolute

The entrypoint creates a deterministic local `DryRunAgentRequest` with one inert plan step. It does not call a model or provider for planning.

## What Did Not Change

Macrostep 3A did not add:

- shell execution
- subprocess / Popen / os.system
- provider/API/network calls
- API key or secrets handling
- browser automation
- git automation
- cloud/GCP execution
- DB/SQLite/ORM
- autonomous background loop
- UI
- web endpoint
- workspace registry
- generalized SafeFileWriter
- `runtime/safety/safe_file_writer.py`
- `runtime/safety/workspace_registry.py`
- provider/model calls
- cryptographic approval token
- key management
- durable nonce store
- new autonomous capability

## Tests Added

Normal tests verify:

- entrypoint exists and is import-safe
- non-empty human goals are accepted
- explicit workspace root is required
- explicit audit directory is required
- absolute workspace/audit paths are required
- durable audit log is created
- workspace-bound artifact is created
- result object serializes to dict
- existing M9 behavior still passes
- existing M10 behavior still passes
- no forbidden runtime capability is added

Adversarial policy tests verify:

- empty goal rejection
- overlong goal rejection
- blocked control character rejection
- relative workspace path rejection
- relative audit directory rejection
- durable audit failure blocks artifact creation
- Macrostep 3A does not call the old non-durable function
- old non-durable compatibility function still exists
- no SafeFileWriter/workspace registry is introduced
- no shell/provider/network/DB/browser/git/cloud capability is introduced

## Safety State

Macrostep 3A adds a local durable controlled-agent entrypoint scaffold. It provides a narrow Python API that routes human goals through the existing durable audit-bound artifact path. It does not add shell execution, provider calls, browser automation, git automation, cloud execution, DB/SQLite/ORM, UI, web endpoints, workspace registry, generalized file writer, or new autonomous capability.

## Known Residual Risks

- This is still a local Python entrypoint, not a full user-facing UI.
- Human approval surface is still not interactive.
- Workspace/project mode is still not implemented.
- Durable audit is local durability, not tamper-proof storage.
- The old non-durable compatibility path still exists but is not used by the new entrypoint.

## Recommended Next Step

Recommended next normal AOIA-Core production step:

- Macrostep 3B: narrow entrypoint policy/readiness review, deciding how this local Python API should be exposed or invoked without adding shell, browser, provider, cloud, DB, UI, workspace registry, or autonomous background behavior.
