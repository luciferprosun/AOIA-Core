# RED-1-B Negative Boundary Test Report

Date: 2026-06-11

Branch: `feature/red1-b-boundary-negative-tests`

Base commit before this work: `a2aed20a40f6de894efc9029ec5ab2bde9c5ca28`

Purpose: add negative boundary tests for safe/public/CPT/webapp paths and prepare a targeted fix queue for RED-1-C. This task does not implement runtime fixes.

## Test files added

- `tests/test_red1_boundary_negative.py`

## Boundaries covered

- browser-bootstrap reachability
- shell execution
- provider/network
- file-write/delete
- git side effects
- approval bypass tokens in live runtime/web files

## What was proven

- `runtime.webapp` import does not import browser execution modules or execution-capable provider/router modules on its own.
- CPT transform endpoint path returns a local transform response without invoking patched browser, shell, provider, file-write, or git primitives.
- CPT transform prompt path does not require browser or provider imports to produce a transformed prompt.
- CPT transform endpoint does not auto-write audit records during the safe transform path.
- Live runtime/web files scanned in this test file do not contain the dangerous bypass tokens listed in the task.

## What remains unproven

- Browser-bootstrap reachability is still not fully closed by proof. This test shows the safe CPT/public path does not trigger browser execution; it does not close the browser surface.
- Shell execution remains present as a frozen legacy surface. This test proves the CPT/public path does not invoke shell primitives; it does not remove shell reachability from the repo.
- Direct filesystem and git boundary coverage remain partial. This test shows the safe CPT/public path does not invoke mutation primitives, but it does not remove the underlying mutation helpers.
- Provider/network gateway separation remains a live architecture concern outside the CPT transform path.
- Memory/retrieval and canonical-promotion follow-up remains open.

## RED-1-C targeted fix queue

Fix ID: RED1-C-001  
Surface: BROWSER  
Problem: browser-bootstrap reachability is still not proven closed for all public entrypoints.  
Evidence: `docs/audit/RED_1_SURFACE_REGISTER.md` marks browser reachability as `P0_BLOCKER`; this RED-1-B test only proves CPT/public transform paths do not trigger browser execution.  
Proposed minimal fix: add a dedicated browser-bootstrap boundary guard and a narrow negative test that proves browser bootstrap cannot be reached from any approved public entrypoint without explicit approval proof.  
Files likely touched: `runtime/main.py`, `runtime/tools/browser_tools.py`, `tests/test_red1_browser_boundary_negative.py` or a new browser-bootstrap-specific test.  
Tests to add or update: browser-bootstrap negative test, public-entrypoint import test.  
Risk: high.  
Should be done now: yes.

Fix ID: RED1-C-002  
Surface: FILE_WRITE_DELETE / GIT  
Problem: direct mutation helpers exist even though the safe CPT/public path does not invoke them.  
Evidence: `runtime/tools/filesystem_tools.py` and knowledge docs contain mutation-capable primitives; current coverage proves non-invocation on the transform path only.  
Proposed minimal fix: add a dedicated boundary guard for direct file mutation and a direct git-negative test, then route any future mutating action through explicit human approval.  
Files likely touched: `runtime/tools/filesystem_tools.py`, `runtime/tools/executor.py`, `tests/test_red1_filesystem_boundary_negative.py`, `tests/test_red1_git_boundary_negative.py`.  
Tests to add or update: filesystem boundary negative test, git boundary negative test.  
Risk: high.  
Should be done now: yes.

Fix ID: RED1-C-003  
Surface: PROVIDER_NETWORK / APPROVAL_GATE  
Problem: provider/model gateway separation is strong, but the repo still carries live provider routing and approval plumbing that must be kept explicitly separate from action execution.  
Evidence: `runtime/model_router.py`, `runtime/provider_clients.py`, and `runtime/webapp.py` expose live proposal/approval routes; this RED-1-B test only proves CPT/public transform does not invoke them.  
Proposed minimal fix: add a dedicated provider gateway register with a narrow approval-provenance test around public entrypoints and keep provider output quarantined from execution authority.  
Files likely touched: `runtime/model_router.py`, `runtime/provider_clients.py`, `runtime/webapp.py`, `tests/test_red1_provider_gateway_boundary_negative.py`.  
Tests to add or update: provider gateway negative test, approval-provenance test.  
Risk: medium-high.  
Should be done now: yes.

Fix ID: RED1-C-004  
Surface: MEMORY_RETRIEVAL / CANONICAL_PROMOTION  
Problem: advisory memory and canonical promotion boundaries remain partially mapped, not fully closed.  
Evidence: `runtime/memory_hat_registry.py`, `runtime/memory_hats/`, `runtime/model_router.py`, and the RED-1-A surface register still mark these surfaces as active/frozen rather than closed.  
Proposed minimal fix: add a narrow follow-up boundary test proving advisory memory and router decisions cannot auto-promote to canonical evidence.  
Files likely touched: `runtime/memory_hat_registry.py`, `runtime/memory_hats/`, `runtime/provider_audit.py`, `tests/test_red1_memory_canonical_boundary_negative.py`.  
Tests to add or update: memory/canonical promotion negative test.  
Risk: medium.  
Should be done now: later, after browser/filesystem/git/provider boundary work.

## Notes

- This report is intentionally scoped to RED-1-B.
- It does not claim RED-1 is closed.
- It does not implement any fixes.

