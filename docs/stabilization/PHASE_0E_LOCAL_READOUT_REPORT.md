# AOIA Phase 0E - Local Provenance Readout Report

## Summary

Phase 0E adds a small local CLI/readout utility for provenance verification.

The utility reuses the existing `verify_provenance_chain(...)` read path and prints a concise operator-facing integrity report. It is deterministic and read-only.

## Files changed

- `runtime/tools/provenance_readout.py`
- `tests/test_provenance_readout.py`
- `docs/stabilization/PHASE_0E_LOCAL_READOUT_REPORT.md`

## Human command

```bash
PYTHONPATH=runtime:. python3 -m tools.provenance_readout provenance/provenance_log.jsonl
```

Use the actual path to the provenance log when it differs from the example.

## Report fields

- `status`: PASS or FAIL
- `total_records`: number of provenance entries read
- `prev_hash_continuity`: PASS or FAIL
- `payload_hash_verification`: PASS or FAIL
- `deterministic_verification`: PASS or FAIL
- `terminal_hash`: final computed chain hash
- `first_failure`: first detected issue, or `none`

## Tests run

```bash
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_append_only_provenance tests.test_provenance_verification tests.test_provenance_readout
```

## Deliberately not implemented

- replay engine
- provider authenticity verification
- distributed provenance
- filesystem immutability
- databases
- routing changes
- provider changes
- orchestration changes
- GUI changes
