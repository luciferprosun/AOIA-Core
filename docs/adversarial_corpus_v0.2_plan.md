# Adversarial Corpus v0.2 Plan

## Purpose

The adversarial corpus v0.2 stub is a small inert JSONL dataset for future shell-command classification testing. It exists to broaden coverage beyond the GT-RUNTIME-6 controlled regression harness without introducing any execution path.

## Why This Is a Stub, Not a Benchmark

This file is intentionally small, curated, and documentation-driven. It is not an external benchmark, not a red-team dataset, and not evidence of real-world shell safety performance.

## Relation to the GT-RUNTIME-7A Threat Model

GT-RUNTIME-7A defined model output and proposed shell commands as untrusted until classified and reviewed. The v0.2 stub extends that threat-model framing by adding examples that stress ambiguous and adversarial-looking command strings.

## Relation to GT-RUNTIME-7B CommandProposal

GT-RUNTIME-7B introduced an inert `CommandProposal` schema for review-oriented data flow. Future work may map these corpus records into `CommandProposal` instances during non-executing tests, but GT-RUNTIME-7D does not add that integration.

## Relation to GT-RUNTIME-7C Mocked Approval Gate

GT-RUNTIME-7C proved mocked approval-gate control flow. The v0.2 stub provides future input material for mocked classification and approval-path tests without adding runtime logic.

## Labels

- `safe`
- `ambiguous`
- `dangerous`
- `unknown`

## Category Taxonomy

- `whitespace_obfuscation`
- `quoting_tricks`
- `variable_interpolation`
- `command_substitution`
- `encoded_payload_indicator`
- `heredoc_indicator`
- `chained_commands`
- `pipe_to_shell`
- `redirection_to_sensitive_path`
- `recursive_permission_change`
- `privilege_escalation_indicator`
- `safe_command_false_positive_trap`
- `ambiguous_admin_command`
- `context_dependent_danger`
- `unknown_or_incomplete_command`

## Non-Execution Boundary

Corpus entries are never executed.

GT-RUNTIME-7D does not execute shell commands.

This corpus does not prove shell safety.

## Future Work Before Any Production Use

- larger external corpus
- red-team review
- fuzzing
- AST/parser comparison
- shell expansion simulation
- sandbox/containment separation
- false-positive/false-negative tracking
