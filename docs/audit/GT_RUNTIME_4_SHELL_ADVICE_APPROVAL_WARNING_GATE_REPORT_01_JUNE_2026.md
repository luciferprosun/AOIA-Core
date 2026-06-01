# GT-RUNTIME-4 Shell Advice Approval / Warning Gate Report

Date: 2026-06-01

## Starting Point

- Starting commit: `5ef22a9 fix: warn on unsafe shell advice in responses`
- Starting tag: `gt-runtime-3-respond-shell-safety-2026-06-01`
- Working branch: `dev/gt-runtime-4-shell-advice-gate`

## Files Inspected

- `runtime/tools/validator.py`
- `runtime/main.py`
- `tests/test_respond_shell_safety.py`
- `tests/test_main.py`
- `tests/test_executor_containment.py`
- `tests/test_command_grammar.py`

## Files Changed

- `runtime/tools/validator.py`
- `tests/test_respond_shell_safety.py`
- `docs/audit/GT_RUNTIME_4_SHELL_ADVICE_APPROVAL_WARNING_GATE_REPORT_01_JUNE_2026.md`

## Changes Made

- Extended `RespondShellSafetyResult` with `severity`.
- Supported severity values:
  - `none`
  - `warning`
  - `high_risk`
- Kept the existing `inspect_respond_shell_safety(message)` helper as the single respond-message shell advice inspection point.
- Preserved normal text behavior: safe messages return unchanged with severity `none`.
- Preserved lower-risk warning behavior for risky file-listing command substitution.
- Classified these respond-message shell advice patterns as `high_risk`:
  - `rm -rf /`
  - `mkfs`
  - `dd if=... of=...`
  - `tar` with `$(find ... -print0)`
  - destructive command substitution
  - `sudo` combined with destructive commands
- Added the high-risk warning prefix:

```text
AOIA HIGH-RISK SHELL ADVICE WARNING: This response contains shell command text that may be unsafe to copy-paste. AOIA did not execute this command.
```

- Kept the `find -print0` remediation warning:

```text
Do not place NUL-delimited find -print0 output inside shell command substitution. Use a NUL-safe pipeline such as find ... -print0 | tar --null --files-from=-.
```

## Tests Added Or Updated

- Normal respond text stays unchanged.
- Harmless archive listing command is not overblocked.
- `rm -rf /` is high risk.
- `mkfs` is high risk.
- `dd if=... of=...` is high risk.
- `tar -czvf logs.tar.gz $(find . -type f -name "*.log" -print0)` is high risk.
- High-risk warning mentions:
  - `find -print0`
  - command substitution
  - `tar --null`
  - `--files-from=-`
  - AOIA did not execute the command
- Destructive command substitution is high risk.
- File-listing command substitution remains a warning, not a high-risk classification.

## Intentionally Not Changed

- No provider behavior was changed.
- No executor policy was changed.
- No command execution policy was changed.
- No runtime rewrite was performed.
- No RHCSA corpus content was changed.
- No dependencies were added.
- No package installation was performed.
- No push, merge, or main-branch work was performed.

## Validation Results

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest -v tests.test_main tests.test_respond_shell_safety tests.test_executor_containment tests.test_command_grammar`: PASS, 60 tests, 2 skipped
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 348 tests, 4 skipped

## Remaining Risks

- The respond-message filter remains heuristic and does not fully parse shell syntax.
- High-risk classification is advisory display behavior; it does not yet implement a separate interactive approval gate.
- Complex shell constructs outside the current pattern set may still need future coverage.

## Rollback Instructions

Before committing:

```bash
git restore runtime/tools/validator.py tests/test_respond_shell_safety.py
rm docs/audit/GT_RUNTIME_4_SHELL_ADVICE_APPROVAL_WARNING_GATE_REPORT_01_JUNE_2026.md
```

After committing:

```bash
git revert <GT-RUNTIME-4-commit>
```

## Commit Recommendation

Commit is recommended after review if the current diff remains limited to:

- `runtime/tools/validator.py`
- `tests/test_respond_shell_safety.py`
- `docs/audit/GT_RUNTIME_4_SHELL_ADVICE_APPROVAL_WARNING_GATE_REPORT_01_JUNE_2026.md`
