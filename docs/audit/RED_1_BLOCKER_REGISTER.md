# RED-1 Blocker Register

Register status: `RECONCILED_BY_RED_1_FINAL`

Scope: reviewer-facing blocker reconciliation for the RED-1 freeze/reconciliation phase

Date: 2026-06-12

Reconciled branch: `feature/red1-final-surface-reconciliation`

Reconciled baseline: `bf2f267` (`docs(red1): add final surface reconciliation report`)

Purpose: record the major RED-1 blockers that originally kept AOIA-Core out of production action flows, and show how RED-1-FINAL reconciled them as freeze/default-off boundaries rather than execution approvals.

Important boundary:

- This register does **not** approve production execution.
- This register does **not** approve provider calls.
- This register does **not** approve browser automation.
- This register does **not** approve shell execution.
- This register does **not** approve filesystem/git mutation.
- This register only states that the listed legacy surfaces were identified, frozen/default-off where applicable, and backed by reviewer-visible evidence.

## Reconciled blockers

| Blocker | Original risk | Final state | Evidence | Residual note |
|---|---|---|---|---|
| BLOCKER-01 | `runtime/main.py` browser-like paths might bypass approval. | Reconciled as frozen/default-off browser surface plus public-entrypoint negative coverage. | `docs/audit/RED_1_C_BROWSER_SURFACE_FREEZE_REPORT.md`; `tests/test_red1_browser_surface_freeze.py`; `tests/test_red1_public_entrypoint_boundary_negative.py` | Browser automation remains unapproved for production use. |
| BLOCKER-02 | Runtime wording/behavior could imply autonomous execution. | Reconciled by explicit RED-1 semantic statements and reviewer-facing closure wording. | `docs/audit/RED_1_FINAL_SURFACE_RECONCILIATION_REPORT.md`; `docs/audit/RED_1_CLOSURE_CHECKLIST.md` | AOIA-Core is still not an autonomous agent. |
| BLOCKER-03 | Legacy shell/executor reachability remained visible in the tree. | Reconciled as frozen/default-off shell/executor surface with explicit environment gate and negative tests. | `docs/audit/RED_1_E_SHELL_EXECUTOR_FREEZE_REPORT.md`; `tests/test_red1_shell_executor_freeze.py`; `tests/test_reviewer_safe_execution_lock.py` | No production shell execution flow is approved. |
| BLOCKER-04 | Browser/web-reader surfaces remained present while unapproved. | Reconciled as legacy frozen/default-off surface, not removed but blocked by default. | `docs/audit/RED_1_C_BROWSER_SURFACE_FREEZE_REPORT.md`; `tests/test_red1_browser_surface_freeze.py` | Presence in tree does not equal approval. |
| BLOCKER-05 | Provider/network call coverage needed complete gate proof. | Reconciled as frozen/default-off provider/network surface with local-only catalog/config paths and negative tests. | `docs/audit/RED_1_D_PROVIDER_NETWORK_GATEWAY_SEPARATION_REPORT.md`; `tests/test_red1_provider_network_gateway_separation.py`; `tests/test_red1_boundary_negative.py` | Provider output remains UNTRUSTED and no live provider flow is approved. |
| BLOCKER-06 | File-write/delete/canonical-promotion surfaces needed explicit guard mapping. | Reconciled as filesystem mutation freeze plus approval-provenance and public-boundary evidence. | `docs/audit/RED_1_C2_FILESYSTEM_GIT_FREEZE_REPORT.md`; `tests/test_red1_filesystem_git_surface_freeze.py`; `tests/test_red1_approval_provenance_boundary.py` | No automatic canonical promotion is approved. |
| BLOCKER-07 | Proposal/helper-bot boundary lacked strong negative tests. | Reconciled for RED-1 scope by negative tests proving public/CPT/reviewer-safe paths stay non-executing and non-authoritative. | `docs/audit/RED_1_B_NEGATIVE_TEST_REPORT.md`; `tests/test_red1_boundary_negative.py`; `tests/test_red1_public_entrypoint_boundary_negative.py`; `tests/test_reviewer_safe_execution_lock.py` | This does not approve a future helper bot or controlled agent loop. |

## Closure interpretation

RED-1 reconciles these blockers as follows:

- known dangerous legacy surfaces are reviewer-visible;
- major action-capable surfaces are frozen/default-off where applicable;
- approval state remains distinct from execution permission;
- provider/model output remains UNTRUSTED;
- no model-to-action chain is approved;
- no production browser or shell execution flow is approved.

This means the RED-1 blocker register is closed **for the freeze/reconciliation phase only**.

It does **not** mean later phases may skip:

- proposal/action separation;
- key management policy;
- cost/call ceilings;
- append-only audit logging;
- sandboxed execution design;
- explicit execution architecture review.

## Remaining post-RED-1 blockers

These are not RED-1 blockers anymore. They are next-phase blockers:

1. Controlled Provider Critic design must define an explicit UNTRUSTED write boundary.
2. Provider-output-to-evidence contamination tests must exist before any live provider call.
3. Key management and redaction policy must exist before any live provider call.
4. Cost/call ceilings must exist before any live provider call.
5. Proposal/action separation must be implemented before any execution architecture.
6. Sandboxed execution must exist before any model-assisted action path.
