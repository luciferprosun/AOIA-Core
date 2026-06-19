# Macrostep 2B-1 Durable Audit Trail Report

## Summary

Macrostep 2B-1 adds a minimal isolated durable JSONL audit writer. It does not yet make the full controlled-agent artifact flow depend on durable approval binding. It does not add shell execution, provider calls, browser automation, git automation, cloud execution, DB/SQLite/ORM, workspace registry, generalized file writer, or new agent capability.

## What Changed

- Added `runtime/safety/audit_event_logger.py`.
- Added `append_audit_event_jsonl(...)` for purpose-specific durable `AuditEvent` logging.
- Added `AuditLogWriteResult` for local write outcome metadata.
- Added adversarial tests in `tests/adversarial/test_audit_persistence_boundary.py`.
- Added this audit report.

## Audit Log File Format

- The logger writes JSON Lines.
- The filename is fixed: `events.jsonl`.
- Each call appends exactly one serialized `AuditEvent` object followed by one newline.
- The serialized object uses the existing `AuditEvent.to_dict()` shape, including:
  - `event_id`;
  - `event_hash`;
  - `previous_event_hash`;
  - `payload_hash`;
  - event type, severity, trust state, subject, actor, action, result, reason, and safety flags.

## Append-Only Behavior

- The caller provides only an explicit audit directory, not a filename.
- Existing log content is preserved.
- The log is opened with append flags.
- Existing log entries are not overwritten or truncated.
- If a durable log already exists, the new event must chain to the last recorded `event_hash`.
- If `expected_previous_hash` is provided, it must match the event `previous_event_hash`.

## Fsync Behavior

- The logger flushes through `fsync` after writing the JSONL line.
- The result records `fsync_completed=True` only after the fsync path completes.
- Tests exercise the fsync call path with a safe monkeypatch.

## Size Limits

- Maximum serialized audit event line size: `64 KiB`.
- Oversized serialized events are rejected before opening or writing the log.

## Boundary Checks

- Audit directory must be explicit and absolute.
- Missing audit directory is created for this purpose-specific logger.
- Audit directory symlinks are rejected.
- Audit log symlinks are rejected.
- Log path is fixed to `events.jsonl`; no caller-controlled filename is accepted.
- Invalid event objects are rejected.
- Existing invalid/mismatched chain state blocks append.

## Adversarial Test Summary

The new adversarial audit persistence tests cover:

- log creation in an explicit temporary audit directory;
- exactly one JSONL line per event;
- second event appends without overwrite;
- existing log content preservation;
- fixed filename behavior;
- relative audit directory rejection;
- symlink audit directory rejection where supported;
- symlink log escape rejection where supported;
- oversized event rejection before write;
- fsync path exercise;
- invalid event object rejection;
- expected previous hash mismatch rejection;
- existing log previous hash mismatch rejection;
- no new forbidden runtime capability imports.

## What Did Not Change

- No full controlled-agent flow integration was added.
- No artifact writer dependency on durable audit was added.
- No shell execution was added.
- No subprocess, `Popen`, or `os.system` was added.
- No provider/API/network calls were added.
- No API key or secrets handling was added.
- No browser, git, GCP, or cloud capability was added.
- No DB, SQLite, or ORM was added.
- No workspace registry was added.
- No generalized SafeFileWriter was added.
- No cryptographic approval token or key management was added.
- No UI or web endpoint was added.

## Known Residual Risks

Durable approval binding is not fully closed until the controlled artifact flow requires a successful durable audit write before artifact write. This logger is local durability, not tamper-proof storage.

The logger validates local hash-chain continuity for appended events, but it does not prevent offline file tampering by a process with filesystem access. It is a narrow durable JSONL primitive, not a cryptographic audit ledger.

## Next Recommended Step

Macrostep 2B-2: approval-bound integration.

2B-2 should keep scope narrow and make the controlled artifact flow require successful durable audit logging before artifact write, without adding UI, browser, provider, shell, cloud, database, workspace registry, or generalized file-writing capability.
