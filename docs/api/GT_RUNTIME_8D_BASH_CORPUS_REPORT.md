# GT-RUNTIME-8D Bash Safety Corpus Report

## Starting branch and HEAD

- Starting branch: `dev/gt-runtime-8-bash-safety-planning`
- Starting HEAD: `fd6d27f feat: add inert Bash command proposal parser`

## Purpose

GT-RUNTIME-8D adds an inert Bash Safety corpus and corpus-driven tests for `parse_bash_command` classification behavior.

The goal is to improve classification coverage without adding execution capability.

## Files added/updated

Added:

- `tests/corpus/bash_safety_v0_2.jsonl`
- `tests/test_bash_safety_corpus_v0_2.py`
- `docs/api/GT_RUNTIME_8D_BASH_CORPUS_REPORT.md`

Updated:

- `runtime/safety/bash_parser.py`

## Corpus scope

The corpus is inert JSONL data.

It contains command strings, expected classifications, expected approval states, categories, and notes.

The corpus contains no script files and no executable harness.

## Categories included

- `safe_basic`
- `dangerous_root_delete`
- `dangerous_privilege`
- `dangerous_pipe_to_shell`
- `dangerous_format_or_disk`
- `ambiguous_recursive_delete`
- `ambiguous_chaining`
- `ambiguous_command_substitution`
- `ambiguous_redirection`
- `ambiguous_permissions`
- `unknown_parse_error`
- `false_positive_trap`

## What the tests verify

The tests parse/classify command text only.

They verify:

- every corpus row has required fields
- ids are unique
- expected labels and approval states are allowed
- required categories are represented
- `parse_bash_command` returns `CommandProposal`
- actual classification matches expected classification
- actual approval state matches expected approval state
- `dry_run` remains true
- no execution method is exposed on the returned proposal

## What remains out of scope

GT-RUNTIME-8D does not:

- execute shell commands
- implement a full Bash parser
- implement sandboxing
- implement a terminal agent
- implement production approval
- prove shell safety

## Validation performed

Planned validation:

- `python3 -m compileall runtime tests`
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`
- `git diff --stat`
- `git status --short`
- `git diff --name-status`
- `grep -RIn "subprocess\\|os.system\\|shell=True\\|eval(\\|exec(" runtime/safety runtime/schemas tests docs/api 2>/dev/null || true`

## Limitations

The corpus is a regression guard, not a benchmark.

The parser remains a deterministic string/token inspection layer. It does not interpret shell expansion, resolve paths, or prove runtime safety.

False-positive traps are classified conservatively when command-like text appears in harmless contexts.

## Recommended next step

Recommended next step is human review of the corpus expectations and parser deltas before any commit.

No shell commands are executed.

No subprocess/os.system/shell=True/eval/exec execution was added.

`shell_tools.py`, `executor.py`, `event_ledger.py`, providers, routing, and Cloudflare were not modified.
