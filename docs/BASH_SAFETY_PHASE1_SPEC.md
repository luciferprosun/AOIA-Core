# Bash/Shell Safety Phase 1 Spec

## 1. Purpose and Scope

GT-RUNTIME-8A is a docs-only deliverable.

Bash/Shell Safety Phase 1 is limited to planning and pre-execution classification design only.

No shell execution is added in this phase.

## 2. Current State Reference

- Source branch before new branch: `dev/gt-runtime-5-single-event-ledger`
- Source HEAD: `e19dd40 docs: close GT-RUNTIME-7 phase gate`
- GT-RUNTIME-7A through GT-RUNTIME-7F completed
- Tests: 397 run, 4 skipped, PASS, based on latest known validation
- Bash/Shell Safety Phase 1 had not started before this branch
- Cloudflare stash remains untouched

## 3. What Phase 1 Is

Phase 1 is:

- Planning/specification only
- Pre-execution command inspection design
- Classification-boundary design
- Approval-boundary design
- Audit/ledger design notes only
- No execution

## 4. What Phase 1 Is NOT

Phase 1 is not:

- Shell execution
- Autonomous command execution
- A production approval system
- Sandboxing
- A ShellCheck replacement
- A seccomp/firejail/nsjail/bubblewrap replacement
- Validated production security
- External red-team validation
- Proof of shell safety

## 5. Absolute Read-Only Boundary

The following files and directories must not be modified during GT-RUNTIME-8A:

- `runtime/tools/executor.py`
- `runtime/tools/shell_tools.py`
- `runtime/tools/event_ledger.py`
- `runtime/tools/validator.py`
- `runtime/tools/command_grammar.py`
- `runtime/providers/`
- `runtime/main.py`
- `runtime/webapp.py`
- `runtime/run.sh`
- `runtime/run_web.sh`
- `corpus/shell_cases.jsonl`
- `corpus/adversarial_v0.2_stub.jsonl`
- `tools/validate_safety.py`
- `tests/`
- `runtime/adaptive_routing/`
- `runtime/orchestrator/`
- `runtime/memory/`
- `runtime/memory_hats/`
- `runtime/retrieval/`
- `runtime/router/`
- `.gitignore`

## 6. Threat Model Summary

- Prompt/model output can propose harmful commands.
- Command strings can be obfuscated.
- String-only classification is insufficient for many cases.
- Shell expansion can change meaning at runtime.
- Approval gates can be bypassed if integrated carelessly.
- Existing executor/shell tools are contamination risks.
- Current mitigations are documentation, inert schemas, mocks, and phase gates only.

## 7. Adversarial Corpus v0.2 Design Plan

This section is design only. No code is introduced here.

Planned categories:

- Whitespace obfuscation
- Quoting tricks
- Variable interpolation
- Command substitution
- Encoded payload indicators
- Heredoc indicators
- Chained commands
- Pipe-to-shell
- Redirection to sensitive path
- Recursive permission changes
- Privilege escalation indicators
- Safe-command false-positive traps
- Ambiguous admin commands
- Context-dependent danger
- Unknown/incomplete commands

The current v0.2 stub is not a benchmark and does not prove safety.

## 8. Approval Gate Design

This section is design only. No code is introduced here.

- The approval gate is currently mocked only.
- Future design must block dangerous, ambiguous, and unknown proposals.
- Human approval is separate from execution.
- Approval must not automatically imply execution.
- Executor integration is forbidden until a later explicit phase gate.

## 9. Ledger Schema Addendum

This section is docs only.

- `event_ledger.py` must not be modified in GT-RUNTIME-8A.
- Future ledger events may include `command_proposal.created`, `classified`, `approval_required`, `approved`, `rejected`, and `execution_skipped`.
- No ledger event implies execution.
- Audit record creation is separate from command execution.

## 10. Phase Gate Conditions for Phase 1 Exit

Minimum exit criteria:

- This spec reviewed by at least one external auditor/model
- No runtime files modified
- No tests modified in GT-RUNTIME-8A
- Claim language reviewed
- Adversarial corpus plan accepted
- Approval gate design accepted
- Separate approval before any schema/test/runtime expansion
- Separate approval before touching `executor.py`, `shell_tools.py`, `event_ledger.py`, `validator.py`, providers, corpus, or tests

## 11. Claim Language Guide

Safe phrases:

- "GT-RUNTIME-8 planning has started. The first deliverable is a specification document only."
- "AOIA-Core is currently a pre-execution command inspection and audit-boundary project."
- "Current tests exercise mocked and inert pathways; they do not prove production shell safety."
- "No shell execution has been added in GT-RUNTIME-8A."
- "The 12-case corpus is a regression guard, not a safety benchmark."

Forbidden phrases:

- validated safety
- benchmark proves
- 100% shell safety
- production-ready security
- secure shell execution
- shell-safe
- AI safety solved
- autonomous safe execution
- externally validated
- sandboxed execution
- GT-RUNTIME-8 implements Bash safety

## 12. Validation Confirmation

Validation commands:

```bash
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

This docs-only commit should not change validation behavior.
