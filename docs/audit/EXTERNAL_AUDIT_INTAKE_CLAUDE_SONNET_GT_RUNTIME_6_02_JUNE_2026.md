# External Audit Intake — Claude/Sonnet GT-RUNTIME-6 Claim Boundary Review

## 1. Source

This note summarizes an external model audit from Claude/Sonnet.

## 2. Verdict

READY AFTER MINOR WORDING FIXES

## 3. Strong Points

- Claim boundary is mostly honest.
- "What AOIA-Core Is NOT" is strong.
- Corpus commands are clearly inert data.
- Limitation list is honest.
- GT-RUNTIME-7 should not add execution yet.

## 4. Risk Points

- `accuracy=1.0` may be misread.
- PASS labels may look like external validation.
- 12-case corpus is too small for broad safety claims.
- Self-defined thresholds are internal regression gates.
- "Ready for audit" should mean ready to receive audit, not passed audit.

## 5. Required Wording Fixes

- Add corpus-size caveat near metrics table.
- Explain `accuracy=1.0` after JSON block.
- Replace "Ready for external model audit" with "Ready to receive external audit review. No external audit has been performed yet."
- Describe artifact as audit-readiness artifact, not safety certification.
- Clarify classifier layer must remain non-executing.

## 6. Recommended GT-RUNTIME-7 Direction

GT-RUNTIME-7 should remain non-executing and focus on:

- Benchmark limitations document.
- Ledger schema v0.1.
- Adversarial corpus v0.2 plan.
- Approval gate control-flow test.
- Dry-run `CommandProposal` schema.

## 7. Architectural Boundary

No execution layer.
No subprocess additions.
No `shell_tools.py` expansion.
No sudo automation.
No destructive command execution.

## 8. Status

This is an external audit intake note only.
No code changes are made by this note.
