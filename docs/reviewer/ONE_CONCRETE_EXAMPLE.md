# One Concrete Reviewer Example

## Scenario

A human operator asks AOIA-Core for help with a local engineering question about an RHCSA-style Linux configuration task.

The system uses local static knowledge where available. It may also use configured runtime paths and provider switching if a provider is available. The output is treated as operational context and reviewer context, not as automatic evidence.

The workflow is:

1. The operator asks a question about a local engineering issue.
2. AOIA-Core collects relevant local and configured knowledge.
3. AOIA-Core records provenance and logs the decision path.
4. The system presents a suggested action or explanation.
5. If the action is risky, a human approval gate is required before execution.

## What becomes evidence?

Nothing becomes evidence automatically. Promotion to evidence requires governed human approval and must follow the project authority rules.

Evidence is only accepted after explicit review and approval according to the authority boundaries documented in `docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md` and related governance documents.

## What this example does not prove?

- It does not prove model correctness.
- It does not prove production readiness.
- It does not prove scientific validity.
- It does not prove autonomous reasoning.
- It does not prove that external model output is authoritative.

## Notes

The example is intentionally conservative. It illustrates the separation between model-assisted output, operational context, and evidence.

Logs, provenance records, and model responses may support review, but they are not themselves proof of truth. Risky or destructive actions require human approval where gates are implemented.

External model output, if used, remains historical context unless explicitly reviewed and approved.
