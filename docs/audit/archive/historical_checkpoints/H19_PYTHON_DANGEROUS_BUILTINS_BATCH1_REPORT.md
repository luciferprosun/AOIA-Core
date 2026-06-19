# H19 Python Dangerous Built-ins Advisory Batch 1 Report

## Branch
- `dev/rhcsa-command-grammar-layer`

## HEAD Before Changes
- `98271ac`

## Files Created/Changed
- `knowledge/languages/python/advisory/README.md`
- `knowledge/languages/python/advisory/level_6_security_pitfalls/README.md`
- `knowledge/languages/python/advisory/level_6_security_pitfalls/dangerous_builtins_batch1.jsonl`
- `knowledge/languages/python/official_docs_crosscheck/FIRST_CROSSCHECK_TARGETS.md`
- `tests/test_python_advisory_records_batch1.py`
- `docs/audit/H19_PYTHON_DANGEROUS_BUILTINS_BATCH1_REPORT.md`

## Records Added
- `10`

## Topics
- eval on user input
- exec on model-generated code
- compile with dynamic source
- dynamic import with user-controlled module name
- open with user-controlled path and write mode
- input passed into eval/exec or shell command
- globals/locals used for dynamic namespace mutation
- getattr/setattr/delattr with user-controlled attribute name
- pickle.load / pickle.loads on untrusted data
- subprocess.run with shell=True and user/model input

## Status Of Records
- `review_status`: `candidate`
- `promotion_status`: `not_promoted`
- `confidence_level`: `low`
- `last_reviewed`: `null`
- no record is marked `human_reviewed`
- no record is marked `official_docs_checked`
- no record is marked `promoted`

## Risk And Policy Summary
- Critical records use `execution_policy: never_execute`.
- High-risk records use `advisory_only_no_execution`.
- No record uses `safe_to_execute_in_test_sandbox`.
- Official documentation targets are kept in verification steps; H19 did not claim live official-docs verification.

## Validation Results
- `dangerous_builtins_batch1.jsonl OK (10 records)`
- `python3 -m compileall runtime tests`: passed
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: passed, `321` tests OK, `4` skipped
- optional pytest check: skipped because `pytest` is not installed

## Known Limitations
- H19 creates draft advisory records only.
- Official Python documentation was not checked live.
- Records remain advisory and inert.
- No examples or corrected patterns were executed.
- No runtime integration was performed.

## Confirmations
- no web scraping was performed
- no examples were executed
- no records were promoted
- no `official_docs_checked` status was assigned
- no runtime/provider/router/executor/Memory Hats runtime code was modified
- frozen tags remain untouched:
  - `post-nlnet-stable-2026-06-01`
  - `aioa-whitehat-stable-2026-06-01`

## Next Suggested Task
- `H20 - Official Docs Cross-Check Batch 1 for Dangerous Built-ins`
