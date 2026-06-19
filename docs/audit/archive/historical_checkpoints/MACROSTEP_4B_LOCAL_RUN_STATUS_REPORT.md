# Macrostep 4B Local Run Status Report

## Status

Macrostep 4B implemented a read-only local run status layer for the Macrostep 4A workspace/run layout.

## What Changed

Added `runtime/safety/local_run_status.py`.

The new status reader inspects a local run under the fixed workspace layout:

```text
<base_workspace_root>/
  runs/
    <run_id>/
      artifacts/
      audit/
        events.jsonl
```

It reports:

- run ID;
- run root;
- artifacts directory path and artifact count;
- audit directory path;
- `events.jsonl` path and existence;
- durable audit event count;
- audit hash-chain status;
- optional expected artifact filename status;
- completion status;
- reason/message.

## Status API

The public API is:

```text
read_local_run_status(
    *,
    base_workspace_root,
    run_id,
    expected_artifact_filename=None,
)
```

It returns a `LocalRunStatus` dataclass with plain-data serialization through `local_run_status_to_dict(...)`.

## Read-Only Guarantees

Macrostep 4B does not create, modify, repair, or delete local run files.

The status reader does not:

- create missing run directories;
- create missing artifact directories;
- create missing audit directories;
- create `events.jsonl`;
- append audit events;
- write artifacts;
- repair malformed audit logs;
- rewrite partial or invalid data.

Missing or malformed state is reported as incomplete or invalid.

## Layout Inspected

The status reader uses the same fixed directory names as Macrostep 4A:

- `runs`
- `artifacts`
- `audit`
- `events.jsonl`

The base workspace root must be explicit and absolute.

The run ID must match the same strict pattern used by Macrostep 4A:

- lowercase letters;
- digits;
- dash;
- underscore;
- maximum length: 64 characters.

Dots, slashes, backslashes, whitespace, control characters, uppercase letters, and shell-like characters are rejected.

## Directory Containment and Symlink Checks

Macrostep 4B:

- canonicalizes inspected paths with `os.path.realpath`;
- checks containment with `os.path.commonpath`;
- rejects symlink run roots where feasible;
- rejects symlink artifact directories where feasible;
- rejects symlink audit directories where feasible;
- rejects symlink audit logs where feasible;
- does not scan outside the run directory.

## Audit Read Behavior

The status reader inspects `events.jsonl` only when it already exists and resolves inside the run audit directory.

It applies a conservative audit log read limit:

```text
1 MiB
```

The reader parses JSONL with `json.loads` and validates the local hash-chain relationship:

```text
current.previous_event_hash == previous.event_hash
```

Malformed JSONL, missing `event_hash`, invalid `previous_event_hash`, empty logs, and hash-chain mismatch are reported as invalid or incomplete. The reader does not attempt repair.

## Artifact Status Behavior

The status reader counts direct regular files inside the run artifacts directory.

It can optionally check one expected artifact filename. The expected artifact value must be a single relative filename, not a path.

The status reader does not write or open artifacts for modification.

## What Did Not Change

Macrostep 4B does not add:

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

Macrostep 4B does not modify provider/client modules, browser modules, shell/executor modules, web UI files, or GCP/cloud/deploy files.

## Tests Added

Added normal status tests:

- import safety;
- absolute base workspace and run ID handling;
- missing/empty run ID rejection;
- expected layout reporting;
- missing run reported incomplete without creation;
- missing audit log reported incomplete without creation;
- missing artifacts directory reported incomplete without creation;
- event count reporting;
- artifact count reporting;
- audit hash-chain validation;
- result serialization;
- filesystem non-mutation.

Added adversarial policy tests:

- relative base path rejection;
- unsafe run ID rejection;
- symlink run root escape rejection where feasible;
- symlink audit log escape rejection where feasible;
- symlink artifact directory escape rejection where feasible;
- malformed JSONL reported invalid without repair;
- oversized audit log reported too large;
- read-only status does not create missing files or directories;
- audit/artifact write functions are not called;
- no shell/provider/network/DB/browser/git/cloud capability introduction.

## Validation Summary

Validation for this report should include:

- `python3 -m compileall -q runtime tests`;
- focused M5-A/M5-B/M8/M9/M10 tests;
- Macrostep 2A adversarial path/resource/state-bypass tests;
- Macrostep 2B adversarial audit persistence and durable approval binding tests;
- Macrostep 3A entrypoint and policy tests;
- Macrostep 4A workspace context and policy tests;
- Macrostep 4B run status and policy tests;
- full unittest discovery;
- `node --check web/app.js`;
- `git diff --check`;
- static forbidden scan.

## Known Residual Risks

This is read-only local status reporting, not a UI.

Durable audit remains local durability, not tamper-proof storage.

Malformed logs are reported, not repaired.

Provider, browser, tool, shell, git, and cloud execution remain out of scope.

## Honest Status

Macrostep 4B adds a read-only local run status layer for the workspace/run layout. It can inspect local run audit and artifact status without creating, modifying, repairing, or executing anything. It does not add shell execution, provider calls, browser automation, git automation, cloud execution, DB/SQLite/ORM, UI, web endpoints, workspace registry, generalized file writer, or autonomous background behavior.

## Recommended Next Step

Recommended next normal AOIA-Core production step: define the next narrow local-control macrostep, likely a non-UI human approval surface design or a read-only run status consumer, while keeping provider/browser/shell/cloud execution out of scope.
