# GT-HAT-5 — Memory Hats Advisory Warning Object Report — 1 June 2026

## 1. Starting Branch And HEAD

- Branch: `dev/rhcsa-command-grammar-layer`
- Starting HEAD: `3ba4dba`
- Protected main: `d7e3448`
- Protected origin/main: `d7e3448`

## 2. Baseline Validation

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_tags -v`: PASS, 10 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_dedup -v`: PASS, 15 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_leaf_routes -v`: PASS, 15 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_storage -v`: PASS, 14 tests
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 232 tests, skipped=4

## 3. Files Created/Changed

- `runtime/memory_hats/__init__.py`
- `runtime/memory_hats/advisory.py`
- `tests/test_memory_hats_advisory.py`
- `docs/audit/GT_HAT_5_MEMORY_HATS_ADVISORY_REPORT_1_JUNE_2026.md`

## 4. AdvisoryWarning Fields Implemented

- `tag_fingerprint`
- `hat_id`
- `tag_type`
- `normalized_trigger`
- `correction_text`
- `evidence_refs`
- `review_status`
- `confidence`
- `active`
- `reason`

`AdvisoryWarning.to_dict()` returns a JSON-serializable dictionary and copies `evidence_refs`.

## 5. advisory_from_tag Behavior

- `ReviewStatus.CONFIRMED` returns an active warning with `confidence="high"`.
- `ReviewStatus.CANDIDATE` returns an active warning with `confidence="low"`.
- `ReviewStatus.REJECTED` returns `None`.
- The source `PheromoneTag` is not mutated.
- Evidence references are copied into the warning.

## 6. Tests Added

- Advisory warning instantiation.
- `to_dict()` key coverage.
- Confirmed tag to high-confidence advisory.
- Candidate tag to low-confidence advisory.
- Rejected tag to `None`.
- Source tag immutability.
- Evidence refs copy behavior.
- Import guard confirming no storage, SQLite, RHCSA, process, router, provider, or knowledge integration imports.

## 7. Validation Result

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_tags -v`: PASS, 10 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_dedup -v`: PASS, 15 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_leaf_routes -v`: PASS, 15 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_storage -v`: PASS, 14 tests
- `PYTHONPATH=runtime:. python3 -m unittest tests.test_memory_hats_advisory -v`: PASS, 8 tests
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 240 tests, skipped=4

## 8. Safety Confirmations

- No RHCSA command grammar integration.
- No command execution.
- No executor/router/provider/kernel/provenance/TUI/web changes.
- No UI or CLI rendering.
- No prompt injection.
- No phi or Memory Garden code.
- No sync or global tags.
- No network code.
- No dependency added.

## 9. New HEAD If Committed

- Pending at report creation; recorded in final chat report after commit.

## 10. Push Result

- Pending at report creation; recorded in final chat report after push.

## 11. Tag Status

- Pending at report creation; recorded in final chat report after tag push.

## 12. Recommended Next Step

- GT-HAT-6: RHCSA grammar advisory lookup integration.
