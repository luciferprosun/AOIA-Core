# NiFe Hat 001 — Bash Safety / Pre-Execution Command Inspection

## Status

Hat 001 is conceptual tagging based on validated project work. It is not a runtime hat implementation yet.

- Docs-only planning.
- Not implemented as a runtime hat.
- Does not change AOIA-Core execution behavior.

## Root key: mV:-70

The Hat 001 domain root key is `mV:-70`.

## Why Bash is Hat 001

Bash Safety is Hat 001 because AOIA-Core already has validated GT-RUNTIME work around inert command representation, classification, approval boundaries, and dry-run audit structure. That makes Bash Safety the first future hat with a clear evidence trail in project history.

## Relationship to GT-RUNTIME-8B through GT-RUNTIME-8F

Hat 001 maps directly onto the public AOIA-Core GT-RUNTIME-8 sequence:

- GT-RUNTIME-8B: API boundary planning
- GT-RUNTIME-8C: inert Bash parser/schema
- GT-RUNTIME-8D: Bash safety corpus v0.2
- GT-RUNTIME-8E: approval gate hardening
- GT-RUNTIME-8F: approval audit event

These milestones describe validated project work that can anchor conceptual tags without turning the tags into runtime behavior.

## Core knowledge scope

Hat 001 covers the future knowledge map for:

- no-execution boundary
- inert command representation
- Bash parse/classify behavior
- dry-run-only approval boundaries
- audit-event documentation boundary
- stable checkpoint discipline across tests, commit, and push

## Tag map

```text
mV:-70          Root: Bash Safety / Pre-Execution Command Inspection
mV:-70.000001  No-execution boundary
mV:-70.000002  CommandProposal is inert data
mV:-70.000003  Bash parser normalizes/classifies but never executes
mV:-70.000004  Classification labels: safe / ambiguous / dangerous / unknown
mV:-70.000005  Dangerous command policy
mV:-70.000006  Ambiguous command policy
mV:-70.000007  Unknown command policy
mV:-70.000008  Bash safety corpus v0.2
mV:-70.000009  ApprovalDecision schema
mV:-70.000010  execution_permitted=False hard lock
mV:-70.000011  allowed=True means dry-run decision only
mV:-70.000012  Approval gate accepts only CommandProposal
mV:-70.000013  No evaluate_command_text in GT-RUNTIME-8E runtime
mV:-70.000014  ApprovalAuditEvent schema
mV:-70.000015  event_id and created_at_utc are caller-supplied
mV:-70.000016  No event_ledger.py integration in GT-RUNTIME-8F
mV:-70.000017  No disk/network logging in GT-RUNTIME-8F
mV:-70.000018  Forbidden files remain untouched
mV:-70.000019  Cloudflare stash remains untouched
mV:-70.000020  Stable checkpoint rule: tests -> commit -> push
```

## Validation evidence

Hat 001 is grounded in existing AOIA-Core reports and pushed checkpoints:

- `docs/api/GT_RUNTIME_8B_API_PLANNING_REPORT.md`
- `docs/api/GT_RUNTIME_8C_INERT_BASH_SCHEMA_REPORT.md`
- `docs/api/GT_RUNTIME_8D_BASH_CORPUS_REPORT.md`
- `docs/api/GT_RUNTIME_8E_APPROVAL_GATE_REPORT.md`
- `docs/api/GT_RUNTIME_8F_APPROVAL_AUDIT_EVENT_REPORT.md`
- current public Git history / pushed checkpoints through `a511d95`

Evidence relationship:

- GT-RUNTIME-8B establishes the API and no-execution planning boundary.
- GT-RUNTIME-8C establishes the inert Bash parser/schema and classification behavior.
- GT-RUNTIME-8D establishes the Bash safety corpus v0.2 checkpoint.
- GT-RUNTIME-8E establishes the `ApprovalDecision` dry-run hardening boundary.
- GT-RUNTIME-8F establishes the `ApprovalAuditEvent` schema and its caller-supplied metadata boundary.

## What is not included yet

This hat does not include:

- runtime hat loading
- resolver logic
- automatic retrieval
- event ledger integration
- execution authority
- provider or Cloudflare integration

## Future expansion

Future docs may later attach:

- source bundles per tag
- contradiction notes
- finer-grained Bash subdomain tags
- links to tested examples and commit-level evidence packs

## Non-goals

This document does not implement:

- runtime code
- tests
- approval execution
- server storage
- API endpoints
- model-ranking logic
- trading bot integration
