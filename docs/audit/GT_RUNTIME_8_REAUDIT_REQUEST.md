# GT-RUNTIME-8 Reaudit Request

Copy this prompt into an external model or reviewer workflow.

```text
You are reviewing AOIA-Core after GT-RUNTIME-8 closure.

Repository path:
/home/l/Desktop/AOIA-Core

Current branch:
dev/gt-runtime-8-bash-safety-planning

Latest pre-GT-RUNTIME-8M HEAD:
cf69e0c docs: add GT-RUNTIME-8 final phase closure package

GT-RUNTIME-8 completed milestones:
- GT-RUNTIME-8G: inert mini-stack integration
- GT-RUNTIME-8H: reviewer boundary statement
- GT-RUNTIME-8I: Bash Safety corpus v0.3
- GT-RUNTIME-8J: corpus coverage matrix + classifier gap report
- GT-RUNTIME-8K: targeted parser hardening
- GT-RUNTIME-8L: final phase closure package

Current validation:
- compileall PASS
- targeted v0.3 tests PASS
- targeted 8J/8K coverage tests PASS
- full unittest PASS: 470 run / 4 skipped

Current Bash Safety boundary:
- no shell execution exists
- no runtime pipeline exists
- no event ledger integration exists
- no GUI/API/terminal agent exists
- no command runner exists
- no HumanApprovalRequest exists
- no evaluate_command_text or evaluate_and_audit_command exists

Current Bash Safety mini-stack:
- CommandProposal
- Bash parser/classifier
- ApprovalDecision
- dry-run approval gate
- ApprovalAuditEvent
- adversarial corpus v0.3
- coverage matrix
- classifier gap report
- targeted parser hardening

Please answer:
1. Was GT-RUNTIME-8 closed coherently?
2. Does the no-execution boundary still hold?
3. Are the Bash Safety parser/corpus/coverage/gap-report steps appropriate?
4. What are the highest-risk remaining gaps?
5. What should GT-RUNTIME-9 be?
6. Should GT-RUNTIME-9 begin with:
   A. corpus v0.4 expansion
   B. more parser hardening
   C. threat model update
   D. inert event/audit schema preparation without event_ledger integration
   E. reviewer/security package consolidation
   F. other, with justification
7. Should shell execution still remain excluded? If not, provide a staged safety gate plan.

Preferences:
- prefer conservative, testable, non-execution steps
- avoid overclaiming safety
- distinguish dry-run approval from execution permission
- treat "safe" as a parser label only, not safe-to-execute
- do not recommend execution as an immediate next step unless you provide a concrete staged safety gate plan
```
