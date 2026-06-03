# GT-RUNTIME-8G Inert Mini-Stack Integration Report

## Starting branch and HEAD

- Branch: `dev/gt-runtime-8-bash-safety-planning`
- Starting HEAD: `dcfffdb docs: add NiFe source registry validation workflow`

## External audit consensus summary

DeepSeek, Meta, Grok, and partly Gemini converged on the same next-step constraint: do not add new runtime capability yet. The immediate milestone should prove the existing inert Bash Safety mini-stack end-to-end without introducing execution, facades, APIs, event ledger integration, NiFe runtime, or human approval request objects.

## Purpose

GT-RUNTIME-8G proves that the current inert mini-stack composes safely:

```text
raw command text
-> CommandProposal
-> Bash parser/classifier
-> ApprovalDecision
-> dry-run approval gate
-> ApprovalAuditEvent
```

The integration test verifies that `execution_permitted` remains `False` at every stage where it exists.

## Files added/updated

- Added `tests/test_inert_mini_stack_integration.py`
- Added `docs/audit/GT_RUNTIME_8G_INERT_MINI_STACK_INTEGRATION_REPORT.md`

## Mini-stack tested

The test uses the real existing components:

- `runtime.safety.bash_parser.parse_bash_command`
- `runtime.safety.approval_gate.evaluate_approval`
- `runtime.schemas.command_proposal.CommandProposal`
- `runtime.schemas.approval_decision.ApprovalDecision`
- `runtime.schemas.approval_audit_event.ApprovalAuditEvent`
- `runtime.schemas.approval_audit_event.from_proposal_and_decision`

No mocks are used for the mini-stack flow.

## What the integration test verifies

The integration test verifies:

- safe command path: `ls -la`
- dangerous command path: `rm -rf /`
- ambiguous command path: `echo $(whoami)`
- unknown parse-error path: `echo "unterminated`
- raw strings cannot enter the approval gate directly
- `ApprovalDecision.execution_permitted=True` is rejected
- `ApprovalAuditEvent.execution_permitted=True` is rejected
- frozen dataclasses cannot be mutated after creation
- the test file itself does not import or call forbidden execution primitives

For the safe path, `allowed=True` means only a dry-run approval decision, not execution permission.

## What remains non-executing

GT-RUNTIME-8G does not execute shell commands.

- The integration test is in-memory only.
- The integration test does not write audit events to disk.
- The integration test does not integrate `event_ledger.py`.
- `ApprovalDecision.execution_permitted` remains `False`.
- `ApprovalAuditEvent.execution_permitted` remains `False`.
- No subprocess/os.system/shell=True/eval/exec/Popen execution was added.

## Why no new runtime module was added

The milestone is intended to prove composition of existing inert components. Adding a new runtime module would expand the behavior surface before the current mini-stack is proven end-to-end.

## Why runtime/safety/pipeline.py was intentionally not added

`runtime/safety/pipeline.py` was intentionally not added because a pipeline facade would create a new runtime entry point. GT-RUNTIME-8G only tests the existing parser, approval gate, and audit event schema directly.

## Why HumanApprovalRequest was deferred

`HumanApprovalRequest` was deferred because GT-RUNTIME-8G is not a human-approval workflow milestone. It only proves the dry-run safety chain and audit event shape.

## Why event_ledger.py was not modified

`event_ledger.py` was not modified because GT-RUNTIME-8G does not add persistence, append behavior, disk logging, or audit-event storage. The audit event is constructed in memory only.

## Why NiFe docs/runtime were not modified

NiFe remains a docs-only future planning area. GT-RUNTIME-8G is a Bash Safety mini-stack proof and does not modify NiFe docs, docs/future, or any NiFe runtime concept.

## Validation performed

Validation commands:

```text
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
```

Validation result:

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS
- Test count: 452 run, 4 skipped
- Static execution primitive grep against the new test/report: PASS
- Static boundary-name grep found only documentation boundary statements in this report.
- Forbidden file and docs/future status checks: PASS

Static safety checks were run against the new test and report to confirm no forbidden execution primitives were introduced in executable test code and that boundary-only mentions remain in documentation.

## Limitations

- GT-RUNTIME-8G does not introduce a runtime pipeline.
- GT-RUNTIME-8G does not create `evaluate_and_audit_command`.
- GT-RUNTIME-8G does not create `evaluate_command_text`.
- GT-RUNTIME-8G does not write audit events to disk.
- GT-RUNTIME-8G does not test external shell behavior because shell execution remains out of scope.
- GT-RUNTIME-8G does not implement API, CLI, UI, provider, routing, Cloudflare, or NiFe runtime behavior.

## Explicit boundary confirmations

- `shell_tools.py`, `executor.py`, `event_ledger.py`, providers, routing, Cloudflare, and NiFe docs were not modified.
- No runtime/safety/pipeline.py facade was created.
- No evaluate_and_audit_command or evaluate_command_text function was created.
- No subprocess/os.system/shell=True/eval/exec/Popen execution was added.

## Recommended next step

Review the GT-RUNTIME-8G integration test and validation output. If accepted, a separate closure prompt can stage, commit, and push the two GT-RUNTIME-8G files without starting GT-RUNTIME-8H.
