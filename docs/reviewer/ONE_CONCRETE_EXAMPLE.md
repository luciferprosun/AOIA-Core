# One Concrete Reviewer Example

## Scenario

A human operator asks AOIA-Core to inspect an AI-proposed shell command before
the operator decides what to do outside AOIA-Core.

The system parses the proposed command, applies current Bash Safety inspection
rules, and returns a dry-run decision with audit context. The output is treated
as operational/reviewer context, not as automatic evidence and not as execution
authorization.

The workflow is:

1. An AI system or human proposes a shell command.
2. AOIA-Core inspects the proposed command without executing it.
3. AOIA-Core records classification, dry-run decision, and audit context.
4. The system presents a conservative explanation of the decision.
5. Any real-world action remains outside the current public AOIA-Core scope.

## What becomes evidence?

Nothing becomes evidence automatically. Promotion to evidence requires governed human approval and must follow the project authority rules.

Evidence is only accepted after explicit review and approval according to the authority boundaries documented in `docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md` and related governance documents.

## What this example does not prove?

- It does not prove model correctness.
- It does not prove production readiness.
- It does not prove scientific validity.
- It does not prove autonomous reasoning.
- It does not prove that external model output is authoritative.
- It does not execute the proposed command.
- It does not prove sandbox containment.

## Notes

The example is intentionally conservative. It illustrates the separation between model-assisted output, operational context, and evidence.

Logs, provenance records, and model responses may support review, but they are
not themselves proof of truth. Approval metadata records review context; it does
not convert `allowed=True` into execution authorization.

External model output, if used, remains historical context unless explicitly reviewed and approved.
