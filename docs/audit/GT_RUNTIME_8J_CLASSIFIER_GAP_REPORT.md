# GT-RUNTIME-8J Classifier Gap Report

## Scope

GT-RUNTIME-8J reviews the GT-RUNTIME-8I Bash Safety corpus v0.3 and the current static classifier output. It adds documentation and an inert coverage test only.

No runtime execution capability was added.

## What the Classifier Handles Better After 8I

- Absolute executable paths such as `/bin/rm` are normalized enough to classify known destructive shapes.
- Escaped command names such as `\rm` are covered.
- `${IFS}` separator obfuscation is recognized at the reviewed root-removal boundary.
- Simple `env` wrappers no longer hide destructive commands.
- `xargs rm -rf` wrapper shapes are treated as dangerous.
- Heredoc-to-shell and pipe-to-shell shapes are blocked as dangerous.
- Redirection to sensitive system paths is classified for review.
- Read-only `systemctl status <unit>` is recognized as safe under the dry-run vocabulary.

## What Remains Weak

- The parser is a static heuristic classifier, not a Bash interpreter.
- It does not implement a full Bash AST.
- It does not model shell expansion, aliases, functions, environment mutation, globbing, process substitution, arithmetic expansion, or here-string variants.
- It does not decode payloads or normalize all Unicode lookalikes.
- It does not reason about filesystem state, permissions, mounted devices, symlinks, or OS policy.
- It does not classify risk based on user identity or execution environment.

## Likely Future Parser-Hardening Categories

- More shell quoting and escaping variants.
- Process substitution and here-string variants.
- Unicode normalization and homoglyph handling.
- More wrapper commands around interpreters and package managers.
- Function and alias definition tracking as inert metadata.
- Safer distinction between output-only command text and executable shell syntax.
- Sensitive redirection beyond the current system-path prefix list.
- Additional read-only admin command contracts with explicit narrow shapes.

## Possible False Positives

- Quoted command-like text can remain `ambiguous` even when it is intended only as output.
- Sensitive-path redirection is conservatively reviewed even though the current mini-stack never executes it.
- Some safe administrative read-only commands may remain `unknown` until a narrow safe contract is added.

## Possible False Negatives

- Obfuscated dangerous commands outside the v0.3 patterns may still classify as `unknown` or `ambiguous` instead of `dangerous`.
- Unicode and encoding tricks are not exhaustively normalized.
- Payload content behind encodings is not decoded.
- More complex shell function, alias, variable, and expansion patterns are not fully understood.

## Static Heuristic Limits

Regex and token heuristics are useful for regression coverage, but they cannot replace a shell parser, shell-aware linter, sandbox, or OS containment boundary. They also cannot prove that a command string is safe to execute.

This work does not replace ShellCheck, sandboxing, seccomp, firejail, nsjail, bubblewrap, containers, or OS-level containment.

## What Was Not Added

- No shell execution.
- No subprocess usage.
- No `os.system`.
- No `shell=True`.
- No `Popen`.
- No `eval` or `exec`.
- No `runtime/safety/pipeline.py`.
- No `evaluate_command_text`.
- No `evaluate_and_audit_command`.
- No `HumanApprovalRequest`.
- No API approval endpoint.
- No GUI.
- No terminal agent.
- No event ledger integration.

## Recommended Next Safe Step

Close GT-RUNTIME-8J with validation, commit, and push only the coverage test and the two audit documents. A later milestone can decide whether to add a generated coverage script, but it should remain inert and must not introduce runtime capability.
