# RED-1 Approval Gate Bypass Verification

Date: 2026-06-11

Branch: `feature/red1-a-surface-register`

Commit: `399279bec01f5b596a840cb9a986138fe12f9a9e`

Purpose: verify where approval-related bypass strings exist, whether they are live code or test/doc fixtures, and whether the browser-bootstrap claim from the blocker register is still supported.

## Exact commands used

```bash
grep -RInE "require_approval\s*=\s*False|require_approval=False|approval_required\s*=\s*False|human_approval_required\s*=\s*False|execution_permitted\s*=\s*True|auto_approve|skip_approval|bypass_approval|without approval|no approval" runtime tests docs web || true
grep -RInE "playwright|selenium|browser|web_reader|browser_tools|page\.|goto\(|click\(|type\(|submit\(|screenshot|download" runtime tests docs web || true
grep -RInE "subprocess|os\.system|pty|pexpect|shell=True|Popen|run\(|exec\(|eval\(|chmod|chown|sudo|apt |apt-get|pip install|npm install" runtime tests scripts docs web || true
grep -RInE "openai|anthropic|google\.generativeai|gemini|openrouter|requests|urllib|httpx|socket|urlopen|api_key|Authorization|Bearer|provider|model_router|fallback|health_check" runtime tests docs web || true
grep -RInE "write_text|write_bytes|open\(.*['\"]w|unlink|remove\(|rmtree|shutil\.move|shutil\.copy|git commit|git push|git reset|git checkout|Path\(" runtime tests scripts docs web || true
grep -RInE "canonical|promote|promotion|trusted|verified|evidence|provenance|memory|hat|pheromone|source_status" runtime tests docs web || true
grep -n "require_approval\|browser_" runtime/main.py
```

## Approval-related findings

- `require_approval=False` was found in tests only:
  - `tests/test_executor_containment.py:26`
  - `tests/test_memory_layer_isolation_smoke.py:20`
  - `tests/test_epistemic_safeguards.py:77`
  - `tests/test_red1_public_entrypoint_boundary_negative.py` uses the string as a negative fixture
- `execution_permitted=True` was found in tests/docs as a rejected or negative case:
  - `tests/test_approval_gate_dry_run.py`
  - `tests/test_inert_mini_stack_integration.py`
  - `tests/test_approval_audit_event.py`
  - `docs/audit/GT_RUNTIME_8G_INERT_MINI_STACK_INTEGRATION_REPORT.md`
- `human_approval_required=False` was not found in live runtime code during this pass.
- `auto_approve`, `skip_approval`, and `bypass_approval` were not found as live runtime controls in the inspected runtime paths during this pass.

## Require-approval verification

Found: partial

Files: `runtime/main.py`, `docs/audit/RED_1_BLOCKER_REGISTER.md`, `tests/test_red1_public_entrypoint_boundary_negative.py`

Line evidence:
- Current `runtime/main.py` grep shows browser actions and browser bootstrap paths are called with `require_approval=True` at lines 465, 471, 940, 951, and 968.
- `docs/audit/RED_1_BLOCKER_REGISTER.md` still records the historical claim as `BLOCKER-01` and says the browser-related calls were changed from `require_approval=False` to `require_approval=True`.
- `runtime/main.py` did not show a current literal `require_approval=False` match in this pass.

Live code, test-only, doc-only, or legacy:
- The current `require_approval=False` string matches are test-only or fixture text.
- The browser-bootstrap and browser-action paths in `runtime/main.py` are live legacy/transitional code paths.

Effect on browser/bootstrap paths:
- The current literal grep does not prove a live `require_approval=False` browser path remains in `runtime/main.py`.
- It does not close the browser/bootstrap question either, because the browser surface is still live and the blocker register still marks the issue open.

RED-1 blocker risk:
- Yes. The browser surface remains a P0 blocker until reachability is proved blocked by negative test coverage.

Recommended negative tests:
- Existing: `tests.test_red1_browser_boundary_negative`
- Proposed if the bootstrap path needs narrower proof: `PROPOSED_TEST_NOT_IMPLEMENTED: tests.test_red1_browser_bootstrap_approval_boundary_negative`

## Other bypass findings

- `execution_permitted=True` is rejected by schemas and appears only in tests/docs as a negative case.
- `provider_call_permitted=False` is the default in current router schemas and approval objects.
- `canonical_promotion_permitted=False` is hard-coded in the model-router path.
- No live runtime approval bypass string was found that directly authorizes execution in the inspected code paths.

## Interpretation

The bypass strings found in tests and docs are not evidence of a live bypass by themselves.

The live risk is the remaining reachability of browser, shell, provider, file, and canonical surfaces, not the presence of the negative-test strings.

This report does not close RED-1.

This report does not approve future executability.
