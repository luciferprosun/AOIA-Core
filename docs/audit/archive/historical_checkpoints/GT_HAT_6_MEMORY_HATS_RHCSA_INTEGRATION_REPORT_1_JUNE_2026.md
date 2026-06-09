# GT-HAT-6 - Memory Hats RHCSA Grammar Advisory Lookup Integration Report - 1 June 2026

## 1. Starting branch and HEAD

- Branch: dev/rhcsa-command-grammar-layer
- Starting HEAD: 20fae9a feat(memory-hats): add advisory warning object [GT-HAT-5]
- Protected main: d7e3448
- Protected origin/main: d7e3448

## 2. Baseline validation

- compileall: PASS
- Memory Hats tag tests: PASS
- Memory Hats dedup tests: PASS
- Memory Hats leaf route tests: PASS
- Memory Hats storage tests: PASS
- Memory Hats advisory tests: PASS
- Full unittest before GT-HAT-6 changes: Ran 240 tests, OK (skipped=4)

## 3. Existing command grammar API inspected

- Inspected `runtime/tools/command_grammar.py`.
- Existing public classifier: `validate_command_shape(command)`.
- The classifier returns dictionary-shaped results with fields including status, danger, family, base, confidence, reasons, and matched_pattern_id.
- `command_grammar.py` was not modified.

## 4. Files created/changed

- Updated `runtime/memory_hats/__init__.py`
- Added `runtime/memory_hats/rhcsa_integration.py`
- Added `tests/test_memory_hats_rhcsa_integration.py`
- Added `docs/audit/GT_HAT_6_MEMORY_HATS_RHCSA_INTEGRATION_REPORT_1_JUNE_2026.md`

## 5. Functions implemented

- `command_to_memory_hat_path`
- `lookup_advisory_for_command`
- `lookup_advisory_for_grammar_result`
- `validate_and_lookup_advisory`

Constants added:

- `DEFAULT_RHCSA_HAT_ID`
- `DEFAULT_PRIMARY_VEIN`
- `DEFAULT_SECONDARY_VEIN`

## 6. Path convention used

The integration maps normalized command strings into the existing Leaf-Vein path format:

`linux_rhcsa/command_grammar/unsupported_linux_command/dnf_status_sshd`

For example, `DNF   status sshd` normalizes to `dnf status sshd` and maps to:

`linux_rhcsa/command_grammar/unsupported_linux_command/dnf_status_sshd`

## 7. Lookup behavior

- Confirmed matching tag: returns active high-confidence advisory.
- Candidate matching tag: returns active low-confidence advisory.
- Rejected matching tag: returns None.
- Missing tag: returns None.
- If confirmed and candidate tags both match the same command trigger, confirmed is preferred.
- Lookup does not create tags.
- Lookup does not increment seen_count.
- Lookup does not mutate stored records.

## 8. Grammar-result helper behavior

- Clearly read-only grammar results return None.
- Suspicious, rejected, unsupported, unknown, or non-read-only grammar results attempt local Memory Hat lookup.
- The helper remains conservative and does not execute or repair commands.
- A validator can be supplied explicitly to `validate_and_lookup_advisory`; no validator is imported or called implicitly.

## 9. Tests added

Added `tests/test_memory_hats_rhcsa_integration.py` covering:

- deterministic command-to-path mapping
- confirmed tag lookup
- candidate tag lookup
- rejected tag ignored
- missing tag returns None
- confirmed tag preference over candidate
- no seen_count mutation
- no store mutation
- grammar-result safe path returns None
- grammar-result suspicious path performs lookup
- fake pure validator support
- no subprocess, shell, executor, router, provider, knowledge, or command grammar imports

## 10. Validation result

- compileall: PASS
- `tests.test_memory_hats_tags`: PASS
- `tests.test_memory_hats_dedup`: PASS
- `tests.test_memory_hats_leaf_routes`: PASS
- `tests.test_memory_hats_storage`: PASS
- `tests.test_memory_hats_advisory`: PASS
- `tests.test_memory_hats_rhcsa_integration`: PASS
- `tests.test_command_grammar`: PASS
- `tests.test_command_grammar_cli`: PASS
- Full unittest: Ran 252 tests, OK (skipped=4)

## 11. Safety confirmations

- No command execution.
- No subprocess import.
- No shell execution.
- No executor changes.
- No router changes.
- No provider changes.
- No kernel changes.
- No provenance changes.
- No TUI/web changes.
- No `command_grammar.py` modification.
- No UI/CLI rendering.
- No prompt injection.
- No phi/Memory Garden code.
- No sync/global tags.
- No network code.
- No dependency added.

## 12. New HEAD if committed

- Pending at report creation time; final chat report records the committed HEAD.

## 13. Push result

- Pending at report creation time.

## 14. Tag status

- Pending at report creation time: `dev-memory-hats-gt-hat-6`

## 15. Recommended next step

GT-HAT-7 seed/example local tags or GT-HAT-8 JSONL export/import. Prefer GT-HAT-8 if the priority is safe local backup/import before deeper integration.
