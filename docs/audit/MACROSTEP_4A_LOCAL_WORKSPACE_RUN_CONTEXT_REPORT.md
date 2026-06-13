# Macrostep 4A Local Workspace Run Context Report

## Status

Macrostep 4A implemented a local workspace/run context for the durable local agent entrypoint.

## What Changed

Added `runtime/safety/local_workspace_run_context.py`.

The new layer prepares one deterministic local run context under an explicit absolute base workspace root:

```text
<base_workspace_root>/
  runs/
    <run_id>/
      artifacts/
      audit/
        events.jsonl
```

The workspace wrapper routes execution through the Macrostep 3A durable local entrypoint:

```text
run_durable_local_agent_entrypoint(...)
```

It does not call the old non-durable compatibility path.

## Workspace and Run Layout

Macrostep 4A creates or validates:

- `runs/`
- `runs/<run_id>/`
- `runs/<run_id>/artifacts/`
- `runs/<run_id>/audit/`

The default artifact output path remains:

```text
aoia_agent_v0_result.md
```

The durable audit log remains under the run audit directory:

```text
runs/<run_id>/audit/events.jsonl
```

## Run ID Validation

Caller-provided run IDs are accepted only when they match the local safe pattern:

- lowercase letters;
- digits;
- dash;
- underscore;
- maximum length: 64 characters.

Run IDs containing dots, slashes, backslashes, spaces, control characters, uppercase letters, or shell-like characters are rejected.

If no run ID is provided, Macrostep 4A generates a local `uuid.uuid4().hex` run ID.

Existing run directories are rejected by default to prevent accidental reuse.

## Directory Containment Strategy

The base workspace root must be explicit and absolute.

Macrostep 4A:

- rejects control/null characters in the base workspace path;
- rejects a symlink base workspace root where feasible;
- rejects a symlink `runs/` directory where feasible;
- canonicalizes paths with `os.path.realpath`;
- checks containment with `os.path.commonpath`;
- creates only the fixed local run directories;
- does not create a project database, index, or registry file.

The artifact directory and audit directory must remain inside the run root.

## Durable Entrypoint Integration

The convenience wrapper:

```text
run_durable_local_agent_in_workspace(...)
```

prepares the run context and then calls:

```text
run_durable_local_agent_entrypoint(...)
```

The durable audit-bound path remains mandatory for Macrostep 4A.

## What Did Not Change

Macrostep 4A does not add:

- shell execution;
- subprocess / Popen / os.system;
- provider/API/network calls;
- API key/secrets handling;
- browser automation;
- git automation;
- cloud/GCP execution;
- DB/SQLite/ORM;
- UI or web endpoints;
- workspace registry;
- generalized SafeFileWriter;
- autonomous background behavior;
- provider/model planning;
- cryptographic approval tokens;
- durable nonce storage.

Macrostep 4A does not modify provider/client modules, browser modules, shell/executor modules, web UI files, or GCP/cloud/deploy files.

## Tests Added

Added normal workspace-context tests:

- import safety;
- absolute base workspace requirement;
- fixed directory layout creation;
- generated safe run ID;
- strict caller run ID validation;
- duplicate run directory rejection;
- result serialization;
- durable local entrypoint execution through workspace context;
- durable audit log under run audit directory;
- artifact under run artifact directory;
- confirmation that the old non-durable path is not called.

Added adversarial policy tests:

- relative base path rejection;
- control/null path rejection;
- unsafe run ID rejection;
- overlong run ID rejection;
- symlink base/run escape rejection where feasible;
- audit/artifact directory containment;
- artifact output containment;
- duplicate run ID rejection;
- no workspace database/index/registry file creation;
- no SafeFileWriter introduction;
- no shell/provider/network/DB/browser/git/cloud capability introduction.

## Validation Summary

Validation for this report should include:

- `python3 -m compileall -q runtime tests`;
- focused M5-A/M5-B/M8/M9/M10 tests;
- Macrostep 2A adversarial path/resource/state-bypass tests;
- Macrostep 2B adversarial audit persistence and durable approval binding tests;
- Macrostep 3A entrypoint and policy tests;
- Macrostep 4A workspace context and policy tests;
- full unittest discovery;
- `node --check web/app.js`;
- `git diff --check`;
- static forbidden scan.

## Known Residual Risks

This is a local run-context layer, not a project registry.

There is still no interactive human approval UI.

Durable audit is local durability, not tamper-proof storage.

Provider, browser, tool, shell, git, and cloud execution remain out of scope.

## Honest Status

Macrostep 4A adds a local workspace/run context for the durable local agent entrypoint. It standardizes per-run artifact and audit directories and routes execution through the existing durable audit-bound local entrypoint. It does not add shell execution, provider calls, browser automation, git automation, cloud execution, DB/SQLite/ORM, UI, web endpoints, workspace registry, generalized file writer, or autonomous background behavior.

## Recommended Next Step

Recommended next normal AOIA-Core production step: define the next narrow local-control macrostep after reviewing whether the run-context API should gain a read-only status/report helper or whether interactive approval surface design should begin separately.
