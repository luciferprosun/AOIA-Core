# AOIA-Core Boundary Statement

## Status

- Current checkpoint: post GT-RUNTIME-8G.
- Branch: `dev/gt-runtime-8-bash-safety-planning`.
- HEAD at start: `ab63ea6`.
- This is a reviewer-facing boundary document.
- It describes current behavior only.
- It is not a roadmap.
- It is not a security certification.

## 1. What AOIA-Core currently is

AOIA-Core currently contains a local-first pre-execution command inspection mini-stack. It turns command text into inert data objects, classifies proposals, evaluates dry-run approval decisions, and creates inert audit-event objects.

In the current Bash Safety path, AOIA-Core is a data-only inspection and decision-record layer. It is designed to make command proposals explicit before any execution system exists.

## 2. What AOIA-Core currently is not

AOIA-Core is currently:

- Not an executing agent.
- Not a terminal agent.
- Not a secure sandbox.
- Not OS-level containment.
- Not a compliance-grade audit trail.
- Not a human approval UI.
- Not an API server.
- Not a GUI.
- Not a command runner.
- Not production-ready shell safety.
- Not a replacement for ShellCheck, seccomp, firejail, nsjail, bubblewrap, containers, or OS security controls.

## 3. Current inert mini-stack

Current mini-stack:

```text
CommandProposal
-> parse_bash_command / Bash parser-classifier
-> ApprovalDecision / evaluate_approval
-> ApprovalAuditEvent / from_proposal_and_decision
```

GT-RUNTIME-8G tests this chain end-to-end.

- The chain is in-memory.
- It does not execute.
- It does not write audit events to disk.
- It does not integrate `event_ledger.py`.
- It does not call providers, routing, or Cloudflare.

## 4. Precise term glossary

`safe`

Means no known-dangerous pattern matched under the current parser/corpus. It does not mean safe to execute.

`ambiguous`

Means the command shape needs review because it contains markers such as command substitution, chaining, pipes, recursive removal, ownership changes, or other patterns the current parser does not treat as read-only safe.

`dangerous`

Means the current parser matched a known-dangerous pattern such as root recursive removal, privilege escalation prefix, runner mode, pipe-to-runner, destructive filesystem operation, or similar explicit marker.

`unknown`

Means the current parser could not recognize the command shape or could not tokenize it. Unknown is not safe.

`allowed`

In `ApprovalDecision`, `allowed=True` means the dry-run gate allowed the proposal as a decision object. It does not authorize execution.

`denied`

In schema vocabulary, denied means a decision/status value can represent refusal. It is not currently a full human approval workflow result.

`approved`

Approved is a schema/status vocabulary value, not proof that a human approved execution.

`not_required`

Means the current dry-run approval decision does not require human review for the scoped inert proposal. It does not authorize execution.

`requires_human_review`

Means the proposal must remain blocked from dry-run approval and requires human review before any future workflow could consider it further.

`dry_run`

Means the object is part of a non-executing path. Dry-run does not execute, schedule, or authorize a command.

`approval gate`

The approval gate is a dry-run classification/decision gate, not an execution gate.

`audit event`

An audit event is an inert data object, not a persisted, signed, tamper-evident compliance record.

`execution_permitted`

This field is hard-locked to `False` in the current `ApprovalDecision` and `ApprovalAuditEvent` path.

`pre-execution`

Means before execution. It does not imply execution is implemented.

`human review`

Means a conservative status requiring external human inspection. It is not currently a UI, workflow engine, or approval capture system.

`no-execution boundary`

Means the current Bash Safety mini-stack represents, classifies, decides, and records command proposals as inert data without executing shell commands.

## 5. What the no-execution boundary is

The boundary is currently maintained by:

- no subprocess/os.system/shell=True/Popen/eval/exec in the runtime safety/schema path
- `ApprovalDecision.execution_permitted` hard-locked `False`
- `ApprovalAuditEvent.execution_permitted` hard-locked `False`
- `evaluate_approval` accepts `CommandProposal`, not raw strings
- GT-RUNTIME-8G integration test verifies `execution_permitted=False` end-to-end
- validation greps and unittest runs

## 6. What the no-execution boundary is not

The no-execution boundary is:

- Not OS isolation.
- Not cryptographic enforcement.
- Not a sandbox.
- Not a guarantee that a command string is safe.
- Not a permission system for executing commands.
- Not a substitute for human review.

## 7. Known limitations

- Parser is heuristic/string-pattern based.
- Corpus v0.2 has 30 cases.
- Classification is not exhaustive.
- Bash has many obfuscation and indirection patterns.
- Known future corpus-hardening areas include `/bin/rm`, `\rm`, IFS substitution, env wrappers, xargs wrappers, alias/function definitions, base64 payloads, heredocs, pipe-to-shell variants, nested command substitutions, and Unicode/encoding tricks.
- These are future hardening targets, not current guarantees.

## 8. Approved uses as of GT-RUNTIME-8G

Allowed uses:

- inert command proposal generation
- static classification experiments
- dry-run approval decision tests
- inert audit-event construction
- corpus tests
- integration tests
- reviewer documentation

Disallowed uses:

- live execution
- autonomous command running
- terminal automation
- sudo actions
- disk logging as compliance record
- API/GUI approval flows
- source registry runtime
- NiFe runtime

## 9. What is not yet built

- shell execution
- safe execution
- human approval interface
- persistent audit log
- event ledger integration
- command rollback
- sandboxing
- OS containment
- model-to-command live pipeline
- API endpoint
- CLI/TUI approval workflow
- source registry runtime
- tag resolver
- public LLM link ingestion
- model verification engine

## 10. Reviewer checklist

Recommended commands:

```text
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
grep -rn "subprocess\|os\.system\|shell=True\|Popen\|eval(\|exec(" runtime/safety runtime/schemas || true
grep -rn "execution_permitted=True" runtime/safety runtime/schemas tests || true
git status --short
git log --oneline -12
```
