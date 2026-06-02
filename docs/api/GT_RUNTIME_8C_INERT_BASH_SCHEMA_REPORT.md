# GT-RUNTIME-8C Inert Bash Schema Report

## Starting branch and HEAD

- Starting branch: `dev/gt-runtime-8-bash-safety-planning`
- Starting HEAD: `133e637 docs: add GT-RUNTIME-8B API boundary planning`

## Purpose

GT-RUNTIME-8C adds the first safe code milestone for Bash Safety by introducing an inert command proposal schema extension and a non-executing parser/normalizer layer.

The purpose is to represent proposed shell commands as data only, classify obvious risk markers, and preserve the approval boundary defined in GT-RUNTIME-8B.

## Files added/updated

Added:

- `runtime/safety/__init__.py`
- `runtime/safety/bash_parser.py`
- `tests/test_bash_parser_inert.py`
- `docs/api/GT_RUNTIME_8C_INERT_BASH_SCHEMA_REPORT.md`

Updated:

- `runtime/schemas/command_proposal.py`
- `runtime/schemas/__init__.py`
- `tests/test_command_proposal_schema.py`

## What the parser does

`parse_bash_command` only parses/classifies/normalizes command text.

It:

- accepts a command string
- normalizes whitespace
- tokenizes using Python standard-library `shlex`
- returns a `CommandProposal` data object
- classifies simple safe, ambiguous, dangerous, and unknown command shapes
- marks ambiguous, dangerous, and unknown proposals as requiring human review
- keeps `dry_run` true

## What the parser does not do

GT-RUNTIME-8C does not execute shell commands.

The parser does not:

- run commands
- interpret variable expansion
- resolve paths
- access filesystem targets
- call runtime shell tools
- call the runtime executor
- write ledger events
- contact providers
- route requests

## Classification labels

Supported labels:

- `safe`
- `ambiguous`
- `dangerous`
- `unknown`

## Approval states

Supported approval states:

- `not_required`
- `requires_human_review`
- `approved`
- `denied`

The parser currently emits `not_required` for safe proposals and `requires_human_review` for ambiguous, dangerous, or unknown proposals.

## Safety boundary

CommandProposal is an inert data object.

GT-RUNTIME-8C does not execute shell commands.

No subprocess/os.system/shell=True/sudo execution was added.

`shell_tools.py`, `executor.py`, `event_ledger.py`, providers, routing, and Cloudflare were not modified.

## Validation performed

Planned validation for this working tree:

- `python3 -m compileall runtime tests`
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`
- `git diff --stat`
- `git status --short`
- `git diff --name-only`
- `git diff -- runtime/schemas runtime/safety tests docs/api`
- `grep -RIn "subprocess\\|os.system\\|shell=True\\|eval(\\|exec(" runtime/schemas runtime/safety tests docs/api 2>/dev/null || true`

## Limitations

This parser is a deterministic, dependency-light first layer.

It is not:

- a complete Bash parser
- a ShellCheck replacement
- a sandbox
- a production approval system
- proof of shell safety
- a terminal agent

String and token pattern checks are intentionally conservative and incomplete.

## Recommended next step

Recommended next step is human and external review of the inert schema/parser boundary before any commit.

After review, a later GT-RUNTIME task may expand non-executing tests or documentation before any runtime integration is considered.
