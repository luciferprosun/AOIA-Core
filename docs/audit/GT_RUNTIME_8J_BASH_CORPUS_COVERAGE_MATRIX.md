# GT-RUNTIME-8J Bash Corpus Coverage Matrix

## Milestone

GT-RUNTIME-8J - Bash Safety Corpus Coverage Matrix + Classifier Gap Report

## Branch and Starting HEAD

- Branch: `dev/gt-runtime-8-bash-safety-planning`
- Starting HEAD: `a39b8e5 test: add GT-RUNTIME-8I Bash Safety corpus v0.3`

## Corpus

- Corpus path: `tests/corpus/bash_safety_v0_3.jsonl`
- Corpus case count: 30

The v0.3 corpus uses the current 8I field names `case_id`, `expected_label`, and `risk_reason`. The 8J coverage test treats these as the semantic equivalents of reviewer-facing `id`, `expected_classification`, and `reason`.

## Matrix by Category

| Category | Cases | Actual classifications |
|---|---:|---|
| `absolute_path_invocation` | 1 | `dangerous=1` |
| `alias_function_definition` | 2 | `ambiguous=2` |
| `base64_payload_indicator` | 2 | `dangerous=2` |
| `chmod_chown_recursive` | 2 | `dangerous=2` |
| `env_wrapper` | 2 | `dangerous=2` |
| `escaped_command_name` | 1 | `dangerous=1` |
| `false_positive_output_only` | 2 | `ambiguous=1`, `unknown=1` |
| `heredoc_indicator` | 2 | `dangerous=2` |
| `ifs_substitution` | 1 | `dangerous=1` |
| `nested_command_substitution` | 1 | `ambiguous=1` |
| `obfuscated_root_delete` | 1 | `dangerous=1` |
| `pipe_to_shell_variant` | 2 | `dangerous=2` |
| `redirection_to_sensitive_path` | 2 | `ambiguous=2` |
| `safe_admin_read_only` | 2 | `safe=2` |
| `sudo_privilege_variant` | 1 | `dangerous=1` |
| `unicode_or_encoding_trick` | 2 | `ambiguous=1`, `dangerous=1` |
| `unknown_unbalanced_quote` | 2 | `unknown=2` |
| `xargs_wrapper` | 2 | `dangerous=2` |

## Matrix by Expected Classification

| Expected classification | Cases |
|---|---:|
| `ambiguous` | 7 |
| `dangerous` | 18 |
| `safe` | 2 |
| `unknown` | 3 |

## Expected vs Actual Classification

| Expected | Actual | Cases |
|---|---|---:|
| `ambiguous` | `ambiguous` | 7 |
| `dangerous` | `dangerous` | 18 |
| `safe` | `safe` | 2 |
| `unknown` | `unknown` | 3 |

Current v0.3 coverage has no expected-vs-actual mismatch.

## Conservative Classifications

- `false_positive_output_only` keeps dangerous-looking quoted text out of direct `dangerous` classification unless there is an execution wrapper. One case remains `ambiguous`; one remains `unknown` because `printf` has no broad safe contract.
- `unicode_or_encoding_trick` includes a fullwidth slash variant as `ambiguous`, not `dangerous`, because the parser does not implement Unicode normalization or shell expansion.
- `redirection_to_sensitive_path` is `ambiguous`, not `dangerous`, because it indicates a sensitive write target but remains a static command string in this milestone.

## Known Weak Areas

- The parser is still heuristic and not a full Bash grammar.
- It does not perform shell expansion, alias expansion, function execution modeling, command substitution evaluation, Unicode normalization, or taint tracking.
- It does not decode base64 or escaped byte strings.
- It does not prove that every unsafe Bash shape is detected.

## No-Execution Boundary

GT-RUNTIME-8J does not execute shell commands. The coverage test reads inert JSONL records and calls the existing static `parse_bash_command` classifier only.

GT-RUNTIME-8J adds no shell execution, no subprocess usage, no API, no GUI, no terminal agent, no event ledger integration, no pipeline facade, and no approval workflow.

## Not a Safety Proof

This matrix is a coverage and regression aid. It is not a security certification, not a sandbox, not OS-level containment, and not proof that a command is safe to execute.
