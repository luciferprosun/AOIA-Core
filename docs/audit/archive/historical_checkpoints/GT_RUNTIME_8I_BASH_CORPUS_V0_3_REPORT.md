# GT-RUNTIME-8I Bash Safety Corpus v0.3 Report

## Starting Branch and HEAD

- Branch: `dev/gt-runtime-8-bash-safety-planning`
- Starting HEAD: `1526cb7 docs: add GT-RUNTIME-8H reviewer boundary statement`

## Purpose

GT-RUNTIME-8I expands the inert Bash Safety corpus with adversarial and edge-case command strings. The goal is to verify that risky Bash patterns are not silently classified as `safe`.

GT-RUNTIME-8I does not execute shell commands. Corpus commands are inert strings only.

## Files Added/Updated

- Added `tests/corpus/bash_safety_v0_3.jsonl`
- Added `tests/test_bash_safety_corpus_v0_3.py`
- Added `docs/audit/GT_RUNTIME_8I_BASH_CORPUS_V0_3_REPORT.md`
- Updated `runtime/safety/bash_parser.py`

## Corpus v0.3 Summary

Corpus v0.3 contains 30 new JSONL cases. Each case includes:

- `case_id`
- `category`
- `command`
- `expected_label`
- `expected_approval_state`
- `risk_reason`
- `notes`

The corpus uses the existing labels `safe`, `ambiguous`, `dangerous`, and `unknown`, and the existing approval states `not_required`, `requires_human_review`, `approved`, and `denied`.

## Category Coverage

Corpus v0.3 covers:

- `obfuscated_root_delete`
- `absolute_path_invocation`
- `escaped_command_name`
- `ifs_substitution`
- `env_wrapper`
- `xargs_wrapper`
- `alias_function_definition`
- `heredoc_indicator`
- `base64_payload_indicator`
- `nested_command_substitution`
- `pipe_to_shell_variant`
- `redirection_to_sensitive_path`
- `sudo_privilege_variant`
- `chmod_chown_recursive`
- `false_positive_output_only`
- `safe_admin_read_only`
- `unknown_unbalanced_quote`
- `unicode_or_encoding_trick`

## Classification Philosophy

The v0.3 corpus treats wrappers that execute or prepare execution as review boundaries. Shell runners, pipe-to-shell shapes, xargs recursive removal, env-wrapped destructive commands, heredoc-to-shell shapes, and encoded payload streams piped to a shell are not allowed to classify as `safe`.

Output-only commands containing dangerous-looking quoted text are not classified as `dangerous` solely because of the quoted text. They remain conservative under the current parser.

Unknown parse errors must not become `safe`. Safe classification does not mean safe to execute.

## Parser Changes, If Any

`runtime/safety/bash_parser.py` was updated with minimal static classification heuristics only:

- Normalize executable positions so absolute paths such as `/bin/rm` and `/usr/bin/env` are classified by command basename.
- Unwrap simple `env` command prefixes before applying existing destructive-command checks.
- Detect `${IFS}` separator obfuscation and classify destructive root/permission/ownership variants as `dangerous`.
- Detect pipe segments that feed into `sh` or `bash`.
- Detect `xargs rm -rf` wrapper shapes.
- Detect heredoc markers attached to `sh` or `bash`.
- Classify alias/function definitions as `ambiguous`.
- Detect redirection to sensitive paths such as `/etc` and `/root` before read-only command checks.
- Treat `systemctl status <unit>` as a read-only safe shape under the current dry-run parser vocabulary.

No execution, filesystem access, network access, process spawning, approval-gate behavior change, schema change, or external dependency was added.

## What Remains Non-Executing

- Bash corpus entries are inert strings.
- `parse_bash_command` remains a parser/classifier.
- `evaluate_approval` remains a dry-run decision function.
- `ApprovalDecision.execution_permitted` remains `False`.
- No audit event is written to disk.
- No runner, terminal agent, CLI, API, GUI, provider route, or Cloudflare integration is added.

## What Was Not Implemented

- No shell execution was implemented.
- No subprocess/os.system/shell=True/Popen/eval/exec was added.
- No `runtime/safety/pipeline.py` was created.
- No `evaluate_command_text` or `evaluate_and_audit_command` was created.
- No `HumanApprovalRequest` was implemented.
- No `event_ledger.py` integration was added.
- No NiFe runtime work was performed.
- `docs/future` was not modified.
- No GT-RUNTIME-8J work was started.

## Validation Performed

Targeted validation:

```text
PYTHONPATH=runtime:. python3 -m unittest tests/test_bash_safety_corpus_v0_3.py -v
```

Result: PASS, 8 tests run.

Full validation:

```text
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

Result: PASS, 460 tests run, 4 skipped.

Static safety checks:

- Runtime safety/schema paths and the new v0.3 test did not add forbidden execution primitives.
- Checks for `runtime/safety/pipeline.py`, `evaluate_command_text`, `evaluate_and_audit_command`, and `HumanApprovalRequest` found only existing test/doc boundary references.
- Forbidden areas including `event_ledger.py`, `shell_tools.py`, `executor.py`, providers, routing, and `docs/future` were not modified.

## Known Limitations

v0.3 is adversarial coverage, not a complete Bash security model.

The parser remains heuristic and string-pattern based. It does not implement a complete Bash grammar, shell expansion model, alias/function execution model, taint model, sandbox, OS containment, or ShellCheck replacement. Additional obfuscation and shell syntax variants remain future hardening targets.

## Recommended Next Step

Review the v0.3 corpus and parser heuristics, then run a separate GT-RUNTIME-8I closure prompt to stage, commit, and push only the approved 8I files. Do not start GT-RUNTIME-8J before 8I closure.
