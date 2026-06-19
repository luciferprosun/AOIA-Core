# GT-RUNTIME-8 Validation Summary

## Scope

This document summarizes the validation state at the end of GT-RUNTIME-8 after milestones 8G through 8K.

## Branch and HEAD

- Branch: `dev/gt-runtime-8-bash-safety-planning`
- HEAD: `9e351bd feat: add GT-RUNTIME-8K targeted parser hardening`

## Validation Commands Used

```text
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest tests/test_bash_safety_corpus_v0_3.py -v
PYTHONPATH=runtime:. python3 -m unittest tests/test_bash_safety_corpus_v0_3_coverage.py -v
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
grep -RInE "subprocess|os\.system|shell=True|Popen|eval\(|exec\(" runtime tests docs/audit scripts 2>/dev/null || true
grep -RInE "evaluate_command_text|evaluate_and_audit_command|HumanApprovalRequest|runtime/safety/pipeline|event_ledger" runtime tests docs/audit scripts 2>/dev/null || true
```

## Latest Validation Result

- `python3 -m compileall runtime tests`: PASS
- Targeted v0.3 tests: PASS
- Targeted 8J/8K coverage tests: PASS
- Full unittest: PASS
- Full unittest count: `470 run / 4 skipped`

## Static Forbidden Primitive Scan Result

The relevant GT-RUNTIME-8 Bash Safety runtime path does not add shell execution primitives.

The broader scan can report historical references in older tests, older audit documentation, and local environment paths. Those references are not GT-RUNTIME-8 execution capability. GT-RUNTIME-8K scoped scans against the changed parser/test/report files found no new executable use of forbidden primitives; report matches were boundary statements only.

Forbidden primitive boundary:

- no `subprocess` execution was added
- no `os.system` execution was added
- no `shell=True` execution path was added
- no `Popen` execution path was added
- no `eval(` or `exec(` path was added

Forbidden architecture boundary:

- no `runtime/safety/pipeline.py` was added
- no `evaluate_command_text` was added
- no `evaluate_and_audit_command` was added
- no `HumanApprovalRequest` was added
- no event ledger integration was added

## Current Corpus Status

- Corpus: `tests/corpus/bash_safety_v0_3.jsonl`
- Version: v0.3
- Records: 30 adversarial/edge-case records
- Mode: classification-only
- Commands: inert strings only
- Execution: no command execution

The corpus checks risky Bash patterns including direct binary deletion, escaped command names, `${IFS}` substitution, `env` wrappers, `xargs` wrappers, alias/function definitions, heredocs, encoded payload indicators, pipe-to-shell variants, sensitive redirection, sudo variants, recursive chmod/chown, output-only false-positive cases, read-only admin commands, unbalanced quotes, and Unicode/encoding tricks.

## What the Tests Validate

- The inert mini-stack composes from parser to dry-run approval decision to inert audit event.
- `ApprovalDecision.execution_permitted` remains `False`.
- `ApprovalAuditEvent.execution_permitted` remains `False`.
- Raw strings cannot directly enter the approval gate.
- Risky v0.3 corpus cases do not silently classify as `safe`.
- Known category coverage remains represented and deterministic.
- Targeted 8K hardening cases classify conservatively.

## Validation Limitations

- Regex/static heuristic parsing is incomplete.
- The corpus is not exhaustive.
- Passing tests do not prove shell safety.
- Passing tests do not mean any command is safe to execute.
- This validation is not a security certification.
- This validation is not OS isolation or sandbox enforcement.
- This work does not replace ShellCheck, sandboxing, containers, seccomp, firejail, nsjail, bubblewrap, or OS-level containment.

## No-Execution Statement

GT-RUNTIME-8 validation exercises inert parsing, classification, dry-run decision construction, and inert audit-event construction. It does not execute shell commands.
