# RED-1 Surface Register

Date: 2026-06-11

Branch: `feature/red1-a-surface-register`

Commit: `399279bec01f5b596a840cb9a986138fe12f9a9e`

Purpose: map execution-capable and side-effect-capable surfaces in the repo before any RED-1 executability work.

Method: read-only inspection of `runtime/main.py`, `runtime/webapp.py`, `runtime/tools/`, `runtime/model_router.py`, `runtime/provider_clients.py`, `runtime/provider_audit.py`, `runtime/safety/`, `runtime/memory_hat_registry.py`, `runtime/memory_hats/`, `runtime/knowledge/`, `tests/`, and the audit/governance docs. Commands used were grep, sed, find, and a runtime AST import scan. No AOIA shell/browser/provider tool was executed.

Inspected paths:
`runtime/main.py`
`runtime/webapp.py`
`runtime/tools/`
`runtime/model_router.py`
`runtime/provider_clients.py`
`runtime/provider_audit.py`
`runtime/safety/`
`runtime/memory_hat_registry.py`
`runtime/memory_hats/`
`runtime/knowledge/`
`tests/`
`docs/audit/RED_1_BLOCKER_REGISTER.md`
`docs/governance/`
`docs/architecture/`

## Surface register

| Surface ID | Surface type | File/path | Symbol/function/class | Evidence line or grep evidence | Current status | Potential side effect | Approval mechanism found | Known bypass risk | Recommended acceptance criterion | Recommended negative test | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RED1-SURFACE-001 | BROWSER | `runtime/tools/browser_tools.py`, `runtime/tools/executor.py`, `runtime/main.py` | `BrowserBridge.browser_start/open/click/type/press/read_html/get_visible_text/screenshot/current_url/close`, `ExecutionEngine._build_tool_registry`, `AgentRuntime.run_text_request` browser branch | `runtime/main.py` grep shows browser actions wrapped with `require_approval=True` at lines 465, 471, 940, 951, 968; `runtime/tools/browser_tools.py` defines live Playwright bridge methods | LEGACY_TRANSITIONAL | Open URLs, click/type, read DOM text, capture screenshots | Executor approval gate exists, but browser tools are also directly callable as code | Direct import of browser helpers or a legacy bootstrap path can bypass the public approval story if reachability is not fully fenced | No browser action may execute without a proposal object plus human approval proof, and no public entrypoint may call browser helpers directly | `tests/test_red1_browser_boundary_negative.py` | P0_BLOCKER |
| RED1-SURFACE-002 | SHELL | `runtime/tools/shell_tools.py`, `runtime/tools/executor.py`, `runtime/commands/local_commands.py`, `runtime/main.py` | `shell_execute`, `ExecutionEngine._execute_shell_action`, `/scan` command path | `runtime/tools/shell_tools.py` returns a reviewer-safe blocked result; `executor.py` still routes shell actions and asks for approval before handling risky actions | FROZEN | Command execution, package install, privilege-changing commands, arbitrary process launch if a future mode re-enables execution | Executor prompt approval exists; shell boundary currently returns blocked result in reviewer-safe default | A future mode or alternate entrypoint could re-open shell execution if the boundary is not tested as frozen | No shell command may execute from public entrypoints in the reviewer-safe default, and no approval token may be mistaken for execution permission | `tests/test_reviewer_safe_execution_lock.py`; `tests/test_executor_containment.py` | P0_BLOCKER |
| RED1-SURFACE-003 | PROVIDER_NETWORK | `runtime/provider_clients.py`, `runtime/model_router.py`, `runtime/webapp.py` | `call_selected_provider_once`, `execute_approved_model_call_once`, `/api/model-selection/propose`, `/api/model-selection/approve-and-call` | `provider_clients.py` performs `urllib.request.urlopen` calls; `webapp.py` exposes approve-and-call routes; `model_router.py` keeps `provider_call_permitted` and `execution_permitted` false unless approval is explicit | LEGACY_TRANSITIONAL | External provider calls, model output ingestion, downstream audit events | Human approval is required for one selected provider call; router schemas reject active authority flags | Approval payload confusion or a missing negative test can turn “approved” into an execution misunderstanding | No provider/API/model call may happen unless the policy gate, approval object, and call boundary all agree, with output kept untrusted | `tests/test_red1_provider_boundary_negative.py`; `tests/test_model_router_controlled_call.py`; `tests/test_red1_approval_provenance_boundary.py` | P0_BLOCKER |
| RED1-SURFACE-004 | FILE_WRITE_DELETE | `runtime/tools/filesystem_tools.py`, `runtime/tools/executor.py` | `create_file`, `write_file`, `append_file`, `move_file`, `delete_file`, `ExecutionEngine._build_tool_registry` | `filesystem_tools.py` directly calls `write_text`, `unlink`, `shutil.move`, and directory creation; executor exposes these as callable actions | ACTIVE | File creation, overwrite, append, move, delete | Executor approval prompt can gate some actions, but the raw functions are callable code paths | Direct import or a future planner path can call file mutation helpers without the shell-style safety story | No file mutation may be triggered from proposals or model output without explicit human approval and a dedicated boundary test | `tests/test_executor_containment.py` plus a proposed dedicated filesystem negative test | P0_BLOCKER |
| RED1-SURFACE-005 | GIT | `runtime/knowledge/extracted/linux_master_library_v1.*`, `runtime/knowledge/candidates/*`, `docs/`, shell-mediated paths | git command examples in knowledge corpus; shell-mediated git actions are implied through the shell surface | Knowledge corpus contains `git commit`, `git push`, `git reset`, `git checkout`; no dedicated git API was found in runtime code | DOC_ONLY | Human-side version control actions if shell execution is later reopened | No direct git automation gate was found | Knowledge text can be mistaken for an executable git surface; shell-mediated git commands can still become side effects if shell execution is re-opened | No direct git automation may exist; any git side effect must remain explicitly human-initiated and shell-gated | Proposed dedicated git negative test not implemented | P1_HIGH |
| RED1-SURFACE-006 | CANONICAL_PROMOTION | `runtime/model_router.py`, `runtime/provider_audit.py`, `runtime/memory_hat_registry.py`, `docs/governance/EVIDENCE_WRITE_CONTRACT.md`, `docs/architecture/FORBIDDEN_MEMORY_FLOWS.md` | `canonical_promotion_permitted`, `canonical_promotion_triggered`, `provider_output_trusted`, `promotion_policy` | `model_router.py` hard-codes `canonical_promotion_permitted=False`; `provider_audit.py` rejects trusted output and canonical promotion; memory hats require review/provenance | FROZEN | Canonical evidence promotion, trusted-output confusion, provenance drift | Hard-coded false flags and review/provenance language exist | A future caller could misread provider output or advisory memory as canonical evidence | No provider output, model-router decision, or memory-hat advisory may auto-promote to canonical evidence | `tests/test_provider_audit.py`; `tests/test_red1_approval_provenance_boundary.py`; `tests/test_model_router_schemas.py` | P0_BLOCKER |
| RED1-SURFACE-007 | MEMORY_RETRIEVAL | `runtime/memory_hat_registry.py`, `runtime/memory_hats/`, `runtime/retrieval/`, `runtime/main.py` | `get_memory_hat_payload`, `MemoryHatRecord`, `SQLiteTagStore`, `build_model_request` memory payload | `memory_hat_registry.py` marks hats runtime-visible and human-review-required; `memory_hats/storage.py` persists advisory tags; `runtime.main` injects active memory hat data into model requests | ACTIVE | Decision-context influence, advisory tag persistence, provenance shaping | Human-review-required flags and advisory-only notes exist | Advisory memory can be mistaken for evidence or truth if boundaries are not tested | No memory/retrieval artifact may become canonical evidence or an execution authority source | `tests/test_memory_layer_isolation_smoke.py`; `tests/test_memory_hat_control_surface.py` | P2_MEDIUM |
| RED1-SURFACE-008 | APPROVAL_GATE | `runtime/safety/approval_gate.py`, `runtime/schemas/approval_decision.py`, `runtime/schemas/model_router.py`, `tests/` | `evaluate_approval`, `ApprovalDecision`, `ModelSelectionProposal`, `ModelSelectionApproval`, `ModelRoutingDecision` | `approval_gate.py` only returns dry-run decisions; schemas reject `execution_permitted=True` and keep human review required | ACTIVE | Policy gating, dry-run allow/deny, reviewer decision metadata | Explicit approval objects and schema checks exist | UI wording or proposal payloads can still confuse approval with execution | Approval state must stay distinct from execution state, and `execution_permitted` must remain false in live schemas | `tests/test_approval_gate_dry_run.py`; `tests/test_approval_audit_event.py`; `tests/test_inert_mini_stack_integration.py` | P0_BLOCKER |
| RED1-SURFACE-009 | WEB_UI | `runtime/webapp.py`, `web/app.js`, `web/index.html`, `web/styles.css` | `/api/status`, `/api/model`, `/api/chat`, `/api/model-selection/propose`, `/api/model-selection/approve-and-call`, `/api/cpt/transform` | `webapp.py` mixes local UI, CPT transform, and model-selection routes; `web/app.js` handles composer and API calls | LEGACY_TRANSITIONAL | Local chat UI actions, model selection proposals, CPT prompt transformation | Separate local preview and manual-send controls exist; model-selection approval is explicit | UI can blur preview, proposal, and execution unless wording and tests stay strict | UI must not imply that preview or approval is execution, and local transform must remain non-networked | `tests/test_cpt_ui_preview.py`; `tests/test_red1_public_entrypoint_boundary_negative.py` | P1_HIGH |
| RED1-SURFACE-010 | UNKNOWN | `runtime/main.py`, `docs/audit/RED_1_BLOCKER_REGISTER.md` | browser-bootstrap reachability discussed in blocker register | Current grep of `runtime/main.py` did not show literal `require_approval=False`; the blocker register still records the historical browser bypass claim as open | UNKNOWN | Potential browser bootstrap approval bypass if an older path still exists outside the current literal grep | `require_approval=True` is visible on current browser action calls | Historical claim may still matter if another bootstrap path exists | Any browser bootstrap path must be grep-proven blocked or test-proven gated | Proposed dedicated browser-bootstrap reachability test not implemented | P0_BLOCKER |

## P0 blockers

- BROWSER reachability is still live in `runtime/main.py` and `runtime/tools/browser_tools.py`.
- SHELL execution is frozen at the current reviewer-safe boundary, but the code path remains present.
- PROVIDER_NETWORK remains live through `runtime/webapp.py` and `runtime/model_router.py`.
- FILE_WRITE_DELETE remains live through `runtime/tools/filesystem_tools.py`.
- APPROVAL_GATE and execution are still separate concepts; that separation must keep holding.
- The browser-bootstrap bypass claim is not confirmed as closed by a current literal grep of `runtime/main.py`.

## Unknowns requiring follow-up

- Whether every browser bootstrap path is fully covered by a negative test outside the historical blocker register.
- Whether git side effects need a dedicated direct boundary test or are sufficiently covered by shell containment.
- Whether any future canonical-promotion path exists outside the current false flags and policy docs.

## Explicit statements

This report does not close RED-1.

This report does not add execution.

This report does not approve future executability.
