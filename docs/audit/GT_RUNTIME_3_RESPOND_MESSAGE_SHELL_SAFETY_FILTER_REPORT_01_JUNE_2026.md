# GT-RUNTIME-3 Respond-Message Shell Safety Filter Report

Date: 2026-06-01

## Starting Point

- Starting commit: `9600a3b fix: move generated runtime state out of repo`
- Starting tag: `gt-runtime-2-move-generated-state-2026-06-01`
- Working branch: `dev/gt-runtime-3-respond-shell-safety`
- Previous tags:
  - `gt-runtime-1-fix-boot-blockers-2026-06-01`
  - `gt-runtime-restart-safepoint-2026-06-01`

## Files Inspected

- `runtime/main.py`
- `runtime/tools/validator.py`
- `runtime/tools/command_grammar.py`
- `runtime/tools/executor.py`
- `tests/test_main.py`
- `tests/test_command_grammar.py`
- `tests/test_executor_containment.py`

## Files Changed

- `runtime/main.py`
- `runtime/tools/validator.py`
- `tests/test_respond_shell_safety.py`
- `docs/audit/GT_RUNTIME_3_RESPOND_MESSAGE_SHELL_SAFETY_FILTER_REPORT_01_JUNE_2026.md`

## Respond-Message Risk Found

The executor and shell command validator already guard actual `shell_execute` actions, but provider `respond` text can still contain unsafe shell command advice that is displayed to the user. That text does not execute in AOIA, but a human could copy-paste it into a shell.

The specific high-priority example is:

```bash
tar -czvf logs.tar.gz $(find . -type f -name "*.log" -print0)
```

This is unsafe advice because NUL-delimited `find -print0` output loses its filename-safety property inside shell command substitution.

## Dangerous Text Patterns Covered

- `$(find ... -print0 ...)`
- `tar` combined with `$(find ... -print0 ...)`
- `rm -rf /`
- `rm -rf *`
- `mkfs`
- `dd if=... of=...`
- `sudo` combined with destructive commands such as `rm -rf`, `mkfs`, or raw `dd` writes
- Command substitution around destructive or file-listing command text

## Changes Made

- Added `RespondShellSafetyResult` in `runtime/tools/validator.py`.
- Added pure helper `inspect_respond_shell_safety(message)` in `runtime/tools/validator.py`.
- The helper performs text-only inspection and never executes commands.
- The helper returns structured fields:
  - `safe`
  - `warnings`
  - `matched_patterns`
  - `sanitized_message`
- Unsafe respond text is prefixed with:

```text
AOIA shell-safety warning: this response contains command text that may be unsafe to copy-paste.
```

- The `find -print0` command-substitution case includes this specific remediation text:

```text
Do not place NUL-delimited find -print0 output inside shell command substitution. Use a NUL-safe pipeline such as find ... -print0 | tar --null --files-from=-.
```

- `runtime/main.py` now applies the filter only at the final displayed response message path for `stop_loop` results.
- Non-dangerous respond text remains unchanged.
- Added focused tests in `tests/test_respond_shell_safety.py`.

## Intentionally Not Changed

- No provider API behavior was changed.
- No executor policy was changed.
- No command execution policy was changed.
- No provenance hash format was changed.
- No RHCSA canonical data was changed.
- No Memory Hats semantics were changed.
- No runtime state directories were moved.
- No dependencies were added.
- No packages were installed.
- No GUI, TUI, web, NVIDIA, CUDA, NeMo, or NIM work was performed.
- No push, merge, or main-branch work was performed.

## Validation Results

Baseline before changes:

- `python3 -m compileall runtime tests`: PASS
- Targeted unittest set: PASS, 56 tests, 2 skipped
- Full unittest discovery: PASS, 336 tests, 4 skipped

After changes:

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest -v tests.test_respond_shell_safety`: PASS, 10 tests
- Targeted unittest set plus new safety tests: PASS, 66 tests, 2 skipped
- Full unittest discovery: PASS, 346 tests, 4 skipped

## Remaining Risks

- The filter is intentionally heuristic and does not parse full shell syntax.
- The filter warns and prefixes respond text; it is not a full interactive approval gate.
- Some unsafe shell advice patterns may remain outside this minimal pattern set.
- Some complex safe command substitutions may still be warned if they resemble risky file-listing or destructive forms.

## Rollback Instructions

To roll back this task before committing:

```bash
git restore runtime/main.py runtime/tools/validator.py
rm tests/test_respond_shell_safety.py
rm docs/audit/GT_RUNTIME_3_RESPOND_MESSAGE_SHELL_SAFETY_FILTER_REPORT_01_JUNE_2026.md
```

After commit, revert with:

```bash
git revert <GT-RUNTIME-3-commit>
```

## Next Recommended Task

GT-RUNTIME-4 - Shell advice approval / warning gate
