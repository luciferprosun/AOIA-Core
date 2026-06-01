# DeepSeek Technical Audit — Python Master Library Safety and Implementation Plan for AIOA Whitehat

Metadata:
- reviewer: DeepSeek
- date: 2026-06-01
- status: external_model_review_unverified
- use: advisory_only
- canonical: false
- runtime_integration: false

## 1. Executive Verdict

The Python Master Library direction is technically sound only with strict caveats. The imported PDF must remain `imported_reference_unverified`, and runtime must remain frozen. A reference-only knowledge library is the correct architectural sequence, but the primary risk is overconfidence: treating plausible content as safe before official documentation review and negative tests exist.

Biggest implementation risk: premature promotion of unverified records into advisory or executable status, especially around `eval`, `exec`, `subprocess.run(..., shell=True)`, `pickle.load`, destructive file APIs, and package installation workflows.

Recommended next step: schema hardening, strict enum validation, dangerous-pattern tests, and high-risk Python API classification. Do not integrate with Memory Hats, runtime executor, command router, or provider logic. Do not expand the corpus beyond current source intake until schema/tests are frozen.

## 2. Current Source Intake Assessment

The imported PDF is a reasonable reference draft for keywords, built-ins, built-in type methods, dunder methods, and exceptions. It is not canonical truth. All behavior descriptions, return value details, and version-specific claims require cross-checking against official Python documentation before promotion.

Risk categories requiring special handling:
- arbitrary code execution: `eval`, `exec`, `compile`, dynamic `import`
- shell/process execution: `subprocess.run`, `os.system`, `os.popen`
- filesystem mutation or data loss: `open(..., "w")`, `os.remove`, `os.unlink`, `pathlib.Path.unlink`, `shutil.rmtree`
- unsafe deserialization: `pickle.load`, `pickle.loads`
- insecure temporary files: `tempfile.mktemp`
- dependency pollution: `sudo pip install`, global `pip install` on externally managed Python

Recommendation: keep all imported records as `imported_unverified` until they pass official documentation comparison and negative tests.

## 3. Threat Model

Threats before runtime integration:
- model-generated unsafe corrections
- unsafe examples stored as corrected patterns
- accidental execution of examples by tests
- command injection through subprocess examples
- `eval`/`exec` misuse
- untrusted pickle deserialization
- destructive file operations without dry-run or confirmation
- global pip pollution
- hardcoded secrets in examples
- path traversal and symlink/race issues
- hallucinated verification steps
- overconfident review statuses
- premature runtime integration

Mitigations:
- examples stored as inert strings only
- no example execution in tests
- strict `execution_policy`
- enum validation
- dangerous-pattern scanning
- promotion gate requiring human review and official docs cross-check
- no runtime integration before a future explicit gate

## 4. Required Repository Boundaries

Allowed now:
- `knowledge/languages/python/`
- `docs/audit/`
- tests validating JSONL, enums, schema consistency, and dangerous patterns

Forbidden now:
- runtime execution logic
- provider/router/command executor logic
- Memory Hats runtime code
- cloud provider configuration
- automatic promotion rules beyond schema enforcement

## 5. Proposed Schema Hardening

Required fields:
- `id`
- `title`
- `domain`
- `subdomain`
- `difficulty`
- `tags`
- `python_version_scope`
- `unsafe_or_wrong_pattern`
- `corrected_pattern`
- `explanation`
- `safety_notes`
- `verification_steps`
- `negative_tests`
- `related_linux_rhcsa_links`
- `official_docs_refs`
- `evidence_refs`
- `review_status`
- `reviewer`
- `confidence_level`
- `risk_level`
- `execution_policy`
- `promotion_status`
- `last_reviewed`
- `known_limitations`
- `source_ref`

Validation rules:
- IDs must be unique across the Python library.
- Enum fields must use strict allowed values.
- `promoted_to_advisory` requires `review_status: promoted`.
- `safe_to_execute_in_test_sandbox` is forbidden unless review status is reviewed or better.
- `official_docs_checked` or `promoted` requires official documentation references.
- high/critical risk records require concrete safety notes.
- no record may be promoted during source intake or schema hardening.

## 6. Allowed Enum Values

`difficulty`:
- `beginner`
- `intermediate`
- `advanced`
- `expert`

`review_status`:
- `imported_unverified`
- `candidate`
- `human_reviewed`
- `official_docs_checked`
- `promoted`
- `deprecated`
- `rejected`

`risk_level`:
- `low`
- `medium`
- `high`
- `critical`

`execution_policy`:
- `reference_only_no_execution`
- `advisory_only_no_execution`
- `safe_to_execute_in_test_sandbox`
- `requires_human_confirmation`
- `never_execute`

`promotion_status`:
- `not_promoted`
- `eligible_for_review`
- `promoted_to_advisory`
- `blocked`

`confidence_level`:
- `low`
- `medium`
- `high`

## 7. Minimum Test Suite

Required tests:
- all JSONL files parse
- required keys exist
- enum fields are valid
- IDs are unique
- source reference or evidence is present
- execution policy is present
- dangerous functions are high or critical
- promoted records require official docs refs
- sandbox execution policy requires review
- tests do not execute examples
- dangerous patterns are detected
- unsafe patterns require corrected patterns and safety notes

Dangerous pattern tests:
- no `shell=True` in corrected patterns
- no `eval(input(` or `exec(input(`
- no `pickle.load` without untrusted-data warning
- no `shutil.rmtree` or delete operation without dry-run or confirmation
- no hardcoded secret-looking strings

## 8. High-Risk Python Items

Critical or high-risk APIs:
- `eval`
- `exec`
- `compile`
- dynamic `import`
- `os.system`
- `os.popen`
- `pickle.load`
- `pickle.loads`
- `shutil.rmtree`
- `tempfile.mktemp`
- `subprocess.run` when shell or untrusted input is involved
- `sudo pip install` / global pip invocation from scripts

Medium or context-dependent APIs:
- `input`
- `open`
- `getattr`
- `setattr`
- `delattr`
- `globals`
- `locals`
- `pathlib.Path.unlink`
- `os.remove`
- `os.unlink`
- `requests.get`
- `requests.post`
- `tempfile.NamedTemporaryFile`

## 9. Safe Python + Linux Automation Rules

1. Never use `shell=True` for untrusted input.
2. Never concatenate user input into shell commands.
3. Dry-run before destructive actions.
4. Require explicit confirmation for delete/overwrite.
5. Use `pathlib.Path` for path manipulation.
6. Avoid following symlinks unless explicitly intended.
7. Handle spaces and newlines in filenames safely.
8. Prefer machine-readable output over human-readable parsing.
9. Set timeouts for network and process calls.
10. Never run `sudo` automatically.
11. Avoid global pip install on externally managed environments.
12. Prefer `pipx` for user-facing CLI tools and `venv` for projects.
13. Do not store secrets in code examples.
14. Use context managers for resources.
15. Avoid fixed absolute temp paths; use `tempfile`.

## 10. Dangerous Pattern Detection Rules

Detection should scan JSONL string fields except intentional `unsafe_or_wrong_pattern` fields.

Patterns to flag:
- `shell=True`
- `eval(input(`
- `exec(input(`
- `pickle.load` / `pickle.loads` without untrusted-data warning
- `shutil.rmtree`, `os.remove`, `os.unlink`, `pathlib.Path.unlink` without dry-run or confirmation notes
- `requests.get` / `requests.post` without timeout guidance
- `sudo pip install`
- global pip installation outside a venv/pipx context
- `os.system` / `os.popen`
- `tempfile.mktemp`
- dynamic import with untrusted input
- hardcoded secret-looking strings

## 11. Implementation Sequence

Recommended sequence:
1. freeze current state with a checkpoint tag
2. add schema documentation
3. define strict enums
4. add JSONL structural tests
5. add enum validity tests
6. classify high-risk built-ins
7. test dangerous function classifications
8. add dangerous pattern tests
9. sanitize records that trigger safety tests
10. ensure every record has an execution policy
11. later add CI/pre-commit validation
12. later add Python safety documentation
13. later add promotion gate script
14. later create an integration gate checklist
15. tag a schema-hardened checkpoint only after tests pass

## 12. Integration Gate Checklist

Before Python records influence advisory suggestions:
- schema must be frozen and versioned
- structural and enum validation tests must pass
- high-risk functions must be classified
- negative pattern tests must pass
- rollback tag must exist
- runtime feature flag must remain off
- promotion gate must pass
- human safety review must sign off
- no automatic code execution of examples may be possible

## 13. Failure Modes If Rushed

- huge unreviewed corpus becomes a trust mirage
- execution policy exists but is not enforced later
- unsafe examples become advice
- docs/tests drift away from actual dangerous patterns
- hallucinated official references get accepted
- accidental runtime coupling
- broken review lifecycle
- Python library becomes a broad tutorial instead of safety-focused advisory corpus

## 14. Recommended H15 Direction

Implement schema hardening, enum validation, JSONL structure tests, dangerous-pattern tests, and record compliance. Do not add new Python records, do not integrate with runtime, and do not execute examples.

## 15. Final Technical Recommendation

Use Codex only as a careful editor, not as an authority. Schema and tests are acceptable model-assisted work because they are verifiable. Any promotion or official-docs claim requires human review. A successful next checkpoint has strict tests passing, dangerous APIs classified, no runtime code touched, and no record promoted.
