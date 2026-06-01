# GT-RUNTIME-5 Single Event Ledger Prototype Report

Date: 2026-06-01

## Starting Point

- Starting commit: `92309e1 docs: close runtime hardening round`
- Latest runtime closure tag: `gt-runtime-hardening-closure-2026-06-01`
- Working branch: `dev/gt-runtime-5-single-event-ledger`
- Push performed: no
- Main branch touched: no

## Files Inspected

- `runtime/runtime_paths.py`
- `runtime/tools/provenance.py`
- `runtime/tools/provenance_readout.py`
- `runtime/tools/validator.py`
- `runtime/main.py`
- `tests/test_append_only_provenance.py`
- `tests/test_provenance_verification.py`
- `tests/test_provenance_readout.py`

## Files Changed

- `runtime/tools/event_ledger.py`
- `tests/test_event_ledger.py`
- `docs/audit/GT_RUNTIME_5_SINGLE_EVENT_LEDGER_PROTOTYPE_REPORT_01_JUNE_2026.md`

## Ledger Path Behavior

The prototype ledger path is produced by `event_ledger_path(project_dir)`.

By default it uses the existing GT-RUNTIME-2 runtime state helper:

```text
runtime_state_dir(project_dir) / "state" / "event_ledger.jsonl"
```

With `AOIA_HOME` unset, this resolves under the local user runtime state home:

```text
~/.local/state/aoia/<project-name>-<digest>/runtime/state/event_ledger.jsonl
```

With `AOIA_HOME` set, tests verify the ledger writes under that temp state home and not inside the source tree.

## Event Schema

Each ledger record is one JSON object per JSONL line with these required fields:

- `event_id`
- `timestamp_utc`
- `event_type`
- `source`
- `payload`
- `prev_hash`
- `event_hash`

`event_id` is the first 16 hex characters of `event_hash`.

## Supported Event Types

- `request_received`
- `route_decision`
- `retrieval_hit`
- `retrieval_miss`
- `action_proposed`
- `action_result`
- `provider_response`
- `shell_safety_warning`
- `high_risk_shell_advice`
- `runtime_note`

## Hash And Append-Only Behavior

- `append_event(...)` opens the ledger in append mode only.
- JSON serialization uses sorted keys and compact separators.
- The first event uses a genesis `prev_hash` of 64 zeroes.
- Later events set `prev_hash` to the previous event's `event_hash`.
- `verify_event_chain(...)` validates:
  - event shape
  - allowed event types
  - genesis hash for the first event
  - previous-hash continuity
  - event hash recomputation
  - event ID consistency
  - corrupt JSONL lines

This prototype is intentionally separate from `runtime/tools/provenance.py` and does not change the existing provenance hash format.

## Secret Redaction Behavior

`redact_payload_secrets(...)` recursively redacts obvious secret key names before hashing or writing an event.

Redacted key names include:

- `api_key`
- `secret`
- `token`
- `password`
- `private_key`
- `access_key`
- `client_secret`

Values are replaced with:

```text
[REDACTED]
```

The helper redacts nested dictionaries and list items. Non-secret payload fields are preserved.

## Validation Results

Baseline before GT-RUNTIME-5 implementation:

- `python3 -m compileall runtime tests`: PASS
- Targeted runtime/provenance/respond tests: PASS, 60 tests, 2 skipped
- Full unittest discovery: PASS, 348 tests, 4 skipped

After GT-RUNTIME-5 implementation:

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest -v tests.test_event_ledger tests.test_append_only_provenance tests.test_provenance_verification tests.test_provenance_readout tests.test_respond_shell_safety`: PASS, 42 tests
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 360 tests, 4 skipped

## Tests Added

`tests/test_event_ledger.py` verifies:

- ledger path uses `AOIA_HOME` temp runtime state and not the source tree
- `append_event` writes one JSONL line
- `read_events` returns events in append order
- two-event `prev_hash` and `event_hash` chain verification passes
- invalid event types are rejected
- obvious secret keys are redacted before write
- `shell_safety_warning` and `high_risk_shell_advice` event types are accepted
- source-tree runtime state is not created
- tampered payloads fail verification
- corrupt JSONL lines fail verification

## Intentionally Not Done

- No full replay engine was implemented.
- No OpenLineage implementation was added.
- No W3C PROV implementation was added.
- No Sigstore or Rekor integration was added.
- No AOIA-Nano extraction was started.
- No GUI, TUI, or web work was performed.
- No provider rewrite was performed.
- No executor rewrite was performed.
- No provenance hash format was changed.
- No Bash/Shell Safety Library work was started.
- No RHCSA corpus expansion was performed.
- No runtime loop integration was added in `runtime/main.py`.

## Remaining Risks

- The ledger is a standalone prototype and is not yet wired into runtime event emission.
- Redaction is key-name based and does not detect every possible secret value.
- There is no file locking for concurrent writers.
- There is no replay engine or query API.
- There is no external transparency log, signature, or attestation layer.

## Rollback Instructions

Before commit:

```bash
rm runtime/tools/event_ledger.py
rm tests/test_event_ledger.py
rm docs/audit/GT_RUNTIME_5_SINGLE_EVENT_LEDGER_PROTOTYPE_REPORT_01_JUNE_2026.md
```

After commit:

```bash
git revert <GT-RUNTIME-5-commit>
```

## Next Recommended Task

GT-RUNTIME-5 commit/tag, then Bash/Shell Safety Library.
