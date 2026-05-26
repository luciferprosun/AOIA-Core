# Phase 0E Closure Report - Local Provenance Integrity Readout

## Current Repository State

- Branch: `main`
- HEAD: `b059fcc`
- Commit name: `feat: add provenance integrity readout`

Known untracked recovery artifacts remain outside this phase:

- `AOIA_RECOVERY_AUDIT.md`
- `reports/master_library_recovery/`
- `scripts/build_master_library_staged.py`

These files were not reviewed as Phase 0E implementation inputs and must remain untouched unless a separate recovery/audit task explicitly scopes them.

## Phase 0E Scope

Phase 0E added a small local provenance integrity readout.

The scope was limited to:

- local provenance integrity readout
- read-only verification
- deterministic double-check of verification results
- concise operator-facing PASS/FAIL reporting
- no mutation of provenance data

The phase deliberately did not change:

- routing logic
- provider logic
- orchestration
- GUI/TUI implementation
- LSC/MHLM theory
- replay engine
- database or SQLite storage
- distributed provenance
- provider authenticity verification

## Files Added By Phase 0E

- `runtime/tools/provenance_readout.py`
- `tests/test_provenance_readout.py`
- `docs/stabilization/PHASE_0E_LOCAL_READOUT_REPORT.md`

## Provenance Readout Behavior

The readout utility reuses the existing `verify_provenance_chain(...)` read path.

It verifies a provenance log twice and compares both results to confirm deterministic behavior. It prints a concise integrity report with:

- `status`
- `total_records`
- `prev_hash_continuity`
- `payload_hash_verification`
- `deterministic_verification`
- `terminal_hash`
- `first_failure`
- issue details when present

The readout path is read-only. It does not append provenance events, rewrite provenance records, or mutate the input log.

## Focused Test Result

Focused command:

```bash
PYTHONPATH=runtime:. python3 -m unittest -v \
  tests.test_append_only_provenance \
  tests.test_provenance_verification \
  tests.test_provenance_readout
```

Observed result:

```text
Ran 18 tests in 0.053s
OK
```

Conclusion: Phase 0C-0E provenance/readout tests pass.

## Full Test Discovery Result

Full command:

```bash
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -v
```

Observed result:

```text
Ran 145 tests in 3.274s
FAILED (errors=2, skipped=2)
```

The failures were import errors in TUI tests caused by the missing optional dependency `textual`:

```text
ModuleNotFoundError: No module named 'textual'
```

The skipped tests were browser/Playwright-related and were skipped because Playwright is not installed.

This is a test-environment dependency gap, not a Phase 0E provenance/readout failure.

## Runtime Blocker Checks

The following import smoke check passed under the repository's expected runtime path convention:

```bash
PYTHONPATH=runtime:. python3 -c "import memory.rhcsa_context; import memory.gemma_worker_memory; import main; print('IMPORT_OK')"
```

Observed result:

```text
IMPORT_OK
```

No runtime import blocker was observed for:

- `memory.rhcsa_context`
- `memory.gemma_worker_memory`

## L1/L4 Evidence Boundary Check

Current executor path records action results as operational events and history, not canonical evidence.

Observed current flow:

```text
self.memory_store.record_result(result)
self.memory_store.append_history("action_result", payload)
```

The previous direct promotion path into evidence was not observed in the current executor implementation.

Current `MemoryStore.append_evidence(...)` remains guarded by the Phase 0B evidence contract:

- required kind: `aoia_kernel_evidence`
- required non-empty `source`
- required non-empty `fingerprint`
- allowed sources:
  - `aoia_kernel`
  - `knowledge_router`
  - `external_evidence_source`

Conclusion: active L1 action-result to L4 evidence promotion was not observed in the current executor path.

## Closure Decision

Phase 0E is closed from the provenance/readout perspective.

Closure basis:

- implementation is minimal
- readout is read-only
- verification is deterministic
- focused provenance tests pass
- no routing/provider/orchestration/GUI/LSC/MHLM behavior changed by the phase
- current runtime import blocker was not observed under `PYTHONPATH=runtime:.`
- active action-result evidence promotion was not observed in current executor path

Full-suite verification still requires an environment decision for optional TUI/browser dependencies.

## Smallest Safe Next Action

Do not refactor runtime code for this finding.

The smallest safe next action is to formalize the test environment policy:

- provenance stabilization can be verified with focused provenance/readout tests
- full repository verification requires optional TUI dependency `textual`
- browser tests require Playwright
- missing optional UI/browser dependencies must be reported as environment gaps, not silently interpreted as provenance failures

Only after that policy is accepted should the project decide whether to install optional test dependencies or mark optional test groups explicitly.

