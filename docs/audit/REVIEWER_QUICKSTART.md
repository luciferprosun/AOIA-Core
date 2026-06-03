# Reviewer Quickstart

## What to read first

Read these files first:

- `docs/audit/AOIA_CORE_BOUNDARY_STATEMENT.md`
- `docs/audit/GT_RUNTIME_8G_INERT_MINI_STACK_INTEGRATION_REPORT.md`
- `tests/test_inert_mini_stack_integration.py`

Then inspect the current implementation files:

- `runtime/schemas/approval_decision.py`
- `runtime/schemas/approval_audit_event.py`
- `runtime/safety/approval_gate.py`
- `runtime/safety/bash_parser.py`

## What AOIA-Core currently does

AOIA-Core currently has an inert Bash Safety mini-stack:

```text
raw command text
-> parse_bash_command
-> CommandProposal
-> evaluate_approval
-> ApprovalDecision
-> from_proposal_and_decision
-> ApprovalAuditEvent
```

It can classify command proposals, produce dry-run approval decisions, and construct in-memory audit-event data objects.

## What it does not do

AOIA-Core currently does not execute shell commands through this mini-stack.

It also does not provide:

- terminal automation
- safe command execution
- shell sandboxing
- OS containment
- persistent compliance audit logging
- human approval UI
- API/GUI approval flow
- NiFe runtime
- source registry runtime

## How to reproduce validation

Run:

```text
python3 -m compileall runtime tests
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v
grep -rn "subprocess\|os\.system\|shell=True\|Popen\|eval(\|exec(" runtime/safety runtime/schemas || true
grep -rn "execution_permitted=True" runtime/safety runtime/schemas tests || true
git status --short
git log --oneline -12
```

## Expected current validation state

At GT-RUNTIME-8G closure, validation passed with:

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS
- Test count: 452 run, 4 skipped

GT-RUNTIME-8H is a documentation milestone. It should not change runtime behavior.

## Files proving the no-execution boundary

Key files:

- `runtime/schemas/approval_decision.py`
- `runtime/schemas/approval_audit_event.py`
- `runtime/safety/approval_gate.py`
- `runtime/safety/bash_parser.py`
- `tests/test_inert_mini_stack_integration.py`

Important checks:

- `ApprovalDecision.execution_permitted` rejects `True`.
- `ApprovalAuditEvent.execution_permitted` rejects `True`.
- `evaluate_approval` accepts `CommandProposal`, not raw strings.
- `parse_bash_command` returns inert `CommandProposal` objects.
- The 8G integration test covers safe, dangerous, ambiguous, and unknown command paths.

## Files intentionally not touched

These should remain untouched by 8H:

- `runtime/tools/event_ledger.py`
- `shell_tools.py`
- `executor.py`
- `runtime/providers`
- `runtime/orchestrator`
- `docs/future`
- Cloudflare files

## Common misunderstanding warnings

- `safe` does not mean safe to execute.
- `allowed=True` does not authorize execution.
- `approved` is schema vocabulary, not proof of human approval.
- `approval gate` is a dry-run decision gate, not an execution gate.
- `audit event` is an inert data object, not a compliance-grade audit record.
- `pre-execution` does not imply execution exists.
- Bash classification is heuristic and not exhaustive.

## Next safe audit questions

- Are the current terms clear enough for external reviewers?
- Are there remaining overclaims in top-level docs?
- Which corpus-hardening gaps should become GT-RUNTIME-8I or later?
- Should future docs separate Bash Safety terms from broader AOIA runtime terms?
- What exact evidence is needed before any human approval workflow is designed?
