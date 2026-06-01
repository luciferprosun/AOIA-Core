# H15 Python Master Library Schema Hardening Report

## Branch

- `dev/rhcsa-command-grammar-layer`

## HEAD Before Changes

- `2c88c0c docs: add Python master library source intake`

## Files Created/Changed

- `docs/audit/external_reviews/python_master_library/DEEPSEEK_TECHNICAL_AUDIT_PYTHON_MASTER_LIBRARY_01_JUNE_2026.md`
- `docs/audit/H15_PYTHON_MASTER_LIBRARY_SCHEMA_HARDENING_REPORT.md`
- `knowledge/languages/python/SCHEMA.md`
- `knowledge/languages/python/schema_enums.json`
- `knowledge/languages/python/examples.jsonl`
- `knowledge/languages/python/reference/keywords_index.jsonl`
- `knowledge/languages/python/reference/builtins_index.jsonl`
- `knowledge/languages/python/reference/dangerous_python_apis.md`
- `tests/test_python_schema_hardening.py`
- `tests/test_python_dangerous_patterns.py`
- `tests/test_python_reference_indexes.py`
- `tests/test_python_knowledge_scaffold.py`

## DeepSeek Review Archived

- yes
- status: `external_model_review_unverified`
- use: `advisory_only`
- canonical: false
- runtime integration: false

## Schema Docs Added

- yes
- file: `knowledge/languages/python/SCHEMA.md`

## Enum File Added

- yes
- file: `knowledge/languages/python/schema_enums.json`
- enum groups:
  - `difficulty`
  - `review_status`
  - `risk_level`
  - `execution_policy`
  - `promotion_status`
  - `confidence_level`

## Dangerous API Index Added

- yes
- file: `knowledge/languages/python/reference/dangerous_python_apis.md`
- high/critical examples include:
  - `eval`
  - `exec`
  - `compile`
  - dynamic `import`
  - `subprocess.run`
  - `os.system`
  - `os.popen`
  - `pickle.load`
  - `pickle.loads`
  - `shutil.rmtree`
  - `tempfile.mktemp`
  - unsafe pip invocation from scripts

## Schema Validation Tests Added

- yes
- file: `tests/test_python_schema_hardening.py`
- coverage:
  - JSONL parseability
  - required policy fields
  - enum validity
  - duplicate ID rejection
  - promotion gate checks
  - sandbox execution policy gate checks
  - `eval`/`exec` risk checks
  - no promoted records during H15
  - no test execution of example records

## Dangerous Pattern Tests Added

- yes
- file: `tests/test_python_dangerous_patterns.py`
- coverage:
  - forbidden patterns in `corrected_pattern`
  - pickle warning requirements
  - destructive file operation dry-run/confirmation requirements
  - request timeout requirements
  - simple secret-looking pattern detection

## JSONL Records Normalized

- yes, for H14 imported reference index records
- H13 scaffold examples were inspected and kept in their original scaffold schema to preserve existing scaffold tests
- existing records only
- no new corpus expansion
- normalized files:
  - `knowledge/languages/python/reference/keywords_index.jsonl`
  - `knowledge/languages/python/reference/builtins_index.jsonl`
- conservative fields added or normalized in reference indexes:
  - `promotion_status: not_promoted`
  - `confidence_level: low`
  - `last_reviewed: 2026-06-01`
  - `official_docs_refs: []`
  - `negative_tests`
  - `source_ref`
  - `risk_level`
- dangerous built-ins:
  - `eval`: `risk_level: critical`, `execution_policy: reference_only_no_execution`
  - `exec`: `risk_level: critical`, `execution_policy: reference_only_no_execution`
  - `input`: `risk_level: high`
  - `open`: `risk_level: medium`

## Validation Results

- JSONL parse validation: PASS
  - `examples.jsonl`: 3 records
  - `keywords_index.jsonl`: 37 records
  - `builtins_index.jsonl`: 61 records
- focused H15 unittest: PASS
  - 24 tests OK
- `python3 -m compileall runtime tests`: PASS
- full unittest discovery: PASS
  - Ran 308 tests
  - OK
  - skipped=4
- optional pytest: unavailable
  - `/usr/bin/python3: No module named pytest`
  - no package was installed

## Known Limitations

- The Python source library remains unverified and reference-only.
- No official Python documentation cross-check has been completed in H15.
- The DeepSeek review is archived as external model review, not canonical project truth.
- Dangerous-pattern tests are static heuristics and do not prove semantic safety.
- No record was promoted to advisory use.

## Safety Confirmations

- No examples were executed.
- No runtime code was modified.
- No provider code was modified.
- No router code was modified.
- No executor code was modified.
- No Memory Hats runtime code was modified.
- Python library remains disconnected from runtime.

## Frozen Tags

- `post-nlnet-stable-2026-06-01`: untouched
- `aioa-whitehat-stable-2026-06-01`: untouched

## Next Suggested Task

- H16 — Python Master Library Official Docs Cross-Check Plan
