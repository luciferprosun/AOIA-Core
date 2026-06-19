# H12 RHCSA Archive Pipeline Advisory Hardening Report

## Branch

- Branch: `dev/rhcsa-command-grammar-layer`
- HEAD before changes: `9efefb1`

## Files Changed

- `docs/audit/LINUX_CONFUSION_TEST_FAILURE_ANALYSIS_01_JUNE_2026.md`
- `docs/audit/H12_RHCSA_ARCHIVE_PIPELINE_ADVISORY_HARDENING_REPORT.md`
- `runtime/knowledge/memory_hats/linux_rhcsa_seed_tags.jsonl`
- `tests/test_memory_hats_seeds.py`

## What Correction Was Added

- Added one local candidate Memory Hats advisory record for the unsafe archive pattern:
  `tar archive from find print0 command substitution`
- The correction text warns that shell command substitution cannot preserve NUL-delimited filename safety.
- The correction text advises:
  - a dry-run or listing step first
  - `find ... -xdev ... -print0`
  - `tar --null --files-from=-`
  - no symlink following unless explicitly intended
  - verification with `tar -tzf`
  - avoiding `rm -rf $(find ...)`

## Diagnostic Report

- The existing diagnostic report `docs/audit/LINUX_CONFUSION_TEST_FAILURE_ANALYSIS_01_JUNE_2026.md` was preserved and is included in this H12 commit.

## Regression Test

- Added one non-executing regression test in `tests/test_memory_hats_seeds.py`.
- The test loads the seed corpus, imports it into in-memory `SQLiteTagStore`, and verifies that the new advisory record is discoverable through existing `lookup_advisory_for_command(...)` with explicit `TagType.COMMAND_SHAPE_SUSPICIOUS` and `secondary_vein="command_shape_suspicious"`.
- The test asserts presence of:
  - dry-run guidance
  - `find`
  - `-xdev`
  - `-print0`
  - `tar --null`
  - `--files-from=-`
  - `tar -tzf`
  - warning against `rm -rf $(find ...)`
- The test also asserts absence of:
  - `tar ... $(find ... -print0 ...)`
  - claims that an archive was created

## Validation Results

- Focused seed/advisory regression: PASS
- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS
- Full unittest summary: `Ran 284 tests`, `OK (skipped=4)`

## Known Limitations

- This hardening adds corpus/advisory coverage, not provider-side reasoning guarantees.
- The new advisory record is discoverable through a targeted advisory trigger and the existing local Memory Hats lookup path.
- This does not yet prove that arbitrary future provider outputs containing unsafe archive text will be normalized automatically into this advisory trigger.
- No provider logic, router logic, or executor behavior was changed in H12.

## Safety Confirmations

- No shell archive commands were executed.
- No shell delete commands were executed.
- No `find`, `tar`, or `rm` commands were run as part of the regression test.
- No provider code was modified.
- No router code was modified.
- No executor code was modified.
- Frozen tags `post-nlnet-stable-2026-06-01` and `aioa-whitehat-stable-2026-06-01` remain untouched.
