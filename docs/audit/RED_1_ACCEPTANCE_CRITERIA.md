# RED-1 Acceptance Criteria

Date: 2026-06-11

Branch: `feature/red1-a-surface-register`

Commit: `399279bec01f5b596a840cb9a986138fe12f9a9e`

Purpose: define machine-verifiable closure criteria for RED-1. These criteria are for future closure only; they do not close RED-1 now.

## Criteria

| Criterion ID | Surface | Closure requirement | Verification command or test | Expected result | Stop condition |
|---|---|---|---|---|---|
| RED1-BROWSER-001 | BROWSER | No browser action path may execute `open`, `click`, `type`, `press`, `read_html`, `get_visible_text`, `screenshot`, or `close` from a public entrypoint without a proposal object plus human approval. | `python3 -m unittest tests.test_red1_browser_boundary_negative -v` | Pass | Any browser action is reachable from a public entrypoint without approval proof |
| RED1-SHELL-001 | SHELL | No shell command may execute from reviewer-safe public entrypoints, and approval state must remain distinct from execution permission. | `python3 -m unittest tests.test_reviewer_safe_execution_lock -v` and `python3 -m unittest tests.test_executor_containment -v` | Pass | A shell command executes or a human approval token is treated as execution permission |
| RED1-PROVIDER-001 | PROVIDER_NETWORK | No provider/model call may occur without explicit approval-provenance checks, and output must remain untrusted. | `python3 -m unittest tests.test_red1_provider_boundary_negative -v`; `python3 -m unittest tests.test_model_router_controlled_call -v`; `python3 -m unittest tests.test_red1_approval_provenance_boundary -v` | Pass | A provider call happens without the approval gate or an approval payload can set active authority |
| RED1-FILE-001 | FILE_WRITE_DELETE | No file create/write/append/move/delete path may be auto-triggered from proposals or model output. | `python3 -m unittest tests.test_executor_containment -v`; `PROPOSED_TEST_NOT_IMPLEMENTED: tests.test_red1_filesystem_boundary_negative` | Existing generic containment passes; dedicated file-boundary test is proposed | A file mutation is reachable without explicit operator action and approval |
| RED1-GIT-001 | GIT | No git commit/push/reset/checkout path may be auto-triggered from proposals or model output; git side effects must remain explicitly human-initiated. | `PROPOSED_TEST_NOT_IMPLEMENTED: tests.test_red1_git_boundary_negative` | Dedicated negative test is not yet implemented | A git side effect can be triggered from model output, proposal data, or a hidden helper path |
| RED1-CANONICAL-001 | CANONICAL_PROMOTION | No provider output, router decision, or advisory memory object may auto-promote to canonical evidence. | `python3 -m unittest tests.test_provider_audit -v`; `python3 -m unittest tests.test_red1_approval_provenance_boundary -v`; `python3 -m unittest tests.test_model_router_schemas -v` | Pass | Any path can set `canonical_promotion_permitted=True` or write canonical evidence from generated text |
| RED1-MEMORY-001 | MEMORY_RETRIEVAL | No memory-hat or retrieval artifact may become canonical evidence or an execution authority source. | `python3 -m unittest tests.test_memory_layer_isolation_smoke -v`; `python3 -m unittest tests.test_memory_hat_control_surface -v`; `PROPOSED_TEST_NOT_IMPLEMENTED: tests.test_red1_memory_retrieval_boundary_negative` | Existing memory-isolation coverage passes; dedicated boundary test is proposed | Runtime memory, logs, or advisory tags are promoted to evidence or action authority |
| RED1-APPROVAL-001 | APPROVAL_GATE | Approval state must remain separate from execution state; `execution_permitted` must remain false and `human_approval_required` must remain true where required. | `python3 -m unittest tests.test_approval_gate_dry_run -v`; `python3 -m unittest tests.test_approval_audit_event -v`; `python3 -m unittest tests.test_inert_mini_stack_integration -v` | Pass | Any schema or approval object can authorize execution |
| RED1-UI-001 | WEB_UI | UI wording must not imply that approval equals execution, and preview controls must stay separate from send controls. | `PROPOSED_TEST_NOT_IMPLEMENTED: tests.test_red1_ui_wording_boundary_negative` | Dedicated UI wording test is not yet implemented | UI copy or control flow suggests preview/approval is execution |

## Closure requirements by surface

- Browser surface: require a proposal object, a human approval decision, and a negative test proving no browser action reaches the public entrypoint without approval.
- Shell surface: keep the reviewer-safe block at the final subprocess boundary and prove the shell path cannot execute from public entrypoints.
- Provider/network surface: keep output untrusted, keep approval provenance explicit, and keep provider/network calls blocked until the policy gate says otherwise.
- File write/delete surface: keep mutation out of proposal generation and out of model output; only explicit human action may trigger mutation.
- Git surface: keep git as an explicit human action, not an automatic side effect of proposals or model output.
- Canonical promotion surface: keep provider output, model-router decisions, and advisory memory out of canonical evidence unless a future review path explicitly authorizes it.
- Memory/retrieval surface: keep advisory memory, logs, and generated text out of canonical evidence and out of execution authority.
- Approval gate: ensure approval is a review state, not an execution permit.
- UI wording: keep preview, approval, and send separate in wording and interaction flow.

## Stop conditions for future RED-1 work

- Any live execution path is reachable without explicit human approval proof.
- Any browser, shell, provider, file, or git side effect is triggered from generated text or a proposal object alone.
- Any approval object can set `execution_permitted=True` in live code.
- Any runtime-generated or provider-generated text becomes canonical evidence without explicit provenance policy.
- Any UI message confuses approval with execution.

## Notes

- Criteria marked `PROPOSED_TEST_NOT_IMPLEMENTED` are future tests, not current evidence.
- Existing tests can satisfy only the parts that already exist.
- This file is an acceptance register for future closure, not a closure claim.

