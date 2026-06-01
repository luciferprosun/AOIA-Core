# GT-HAT-9 — Memory Hats End-to-End Prototype Test Report — 1 June 2026

## 1. Starting Branch And HEAD

- Branch: `dev/rhcsa-command-grammar-layer`
- Starting HEAD: `300ff9c feat(memory-hats): add Linux RHCSA seed example tags [GT-HAT-7]`
- Protected main: `d7e3448`
- Protected origin/main: `d7e3448`

## 2. Baseline Validation

- `python3 -m compileall runtime tests`: PASS
- Focused Memory Hats tests before GT-HAT-9: PASS
- Baseline full unittest before GT-HAT-9: `Ran 276 tests, OK (skipped=4)`

## 3. Files Created/Changed

- `tests/test_memory_hats_end_to_end.py`
- `docs/audit/GT_HAT_9_MEMORY_HATS_END_TO_END_REPORT_1_JUNE_2026.md`

## 4. End-To-End Flow Tested

The new end-to-end test validates the minimal local Linux/RHCSA Memory Hats pipeline:

- Load seed tags from `runtime/knowledge/memory_hats/linux_rhcsa_seed_tags.jsonl`.
- Import the seed tags into an in-memory `SQLiteTagStore`.
- Look up `dnf status sshd` through `lookup_advisory_for_command`.
- Return an `AdvisoryWarning` from the confirmed seed tag.

## 5. Expected Advisory Output

The confirmed `dnf status sshd` seed produces:

- `active=True`
- `confidence="high"`
- `hat_id="linux_rhcsa"`
- `normalized_trigger="dnf status sshd"`
- correction text mentioning `systemctl status sshd`
- correction text mentioning `dnf`

## 6. Negative/Missing Command Behavior

- `dnf imaginary-subcommand sshd` returns `None` after the same seed import.
- No new candidate is created automatically.
- No store mutation is required for a missing command.

## 7. Idempotent Seed Import Behavior

- Repeated seed import returns the same processed count.
- The stored `linux_rhcsa` tag count does not double.
- The advisory lookup remains stable after repeated import.

## 8. Mutation Checks

- Advisory lookup does not mutate the stored `seen_count`.
- The test checks the stored `dnf status sshd` tag before and after lookup.

## 9. Tests Added

Added `TestMemoryHatsEndToEndPrototype` with coverage for:

- seed JSONL to in-memory SQLite store to advisory warning
- missing command returns `None`
- candidate seed returns low-confidence advisory if present
- repeated seed import is idempotent for lookup
- lookup does not mutate `seen_count`
- Memory Hats end-to-end modules avoid command-execution imports
- end-to-end modules avoid executor/router/provider/provenance/web/TUI runtime integration imports

## 10. Validation Result

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_end_to_end -v`: `Ran 7 tests, OK`
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_command_grammar -v`: `Ran 17 tests, OK`
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_command_grammar_cli -v`: `Ran 15 tests, OK`
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: `Ran 283 tests, OK (skipped=4)`

## 11. Safety Confirmations

- No command execution.
- No subprocess or shell integration.
- No `command_grammar.py` changes.
- No executor/router/provider/kernel/provenance/TUI/web changes.
- No automatic runtime seed loading.
- No UI/CLI rendering.
- No prompt injection.
- No Phi/Memory Garden code.
- No sync/global tags.
- No signed packs.
- No network code.
- No dependency added.

## 12. New HEAD If Committed

- Pending at report creation time; final commit hash is assigned by Git during commit.

## 13. Push Result

- Pending at report creation time.

## 14. Tag Status

- Pending dev-only tag: `dev-memory-hats-gt-hat-9`

## 15. Recommended Next Step

- GT-HAT-10 prototype closure report.
