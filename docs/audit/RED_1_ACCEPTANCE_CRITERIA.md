# RED-1 Acceptance Criteria

Date: 2026-06-12

Status: `SATISFIED_FOR_FREEZE_AND_RECONCILIATION_PHASE`

Validated branch: `feature/red1-final-surface-reconciliation`

Purpose: define the minimum evidence required to accept RED-1 as closed **only** as a freeze/reconciliation phase.

## Acceptance criteria

| Criterion ID | Surface | Closure requirement | Verification command or test | Expected result |
|---|---|---|---|---|
| RED1-BROWSER-001 | Browser automation | Browser-capable legacy paths are blocked/frozen by default and not approved as a production action path. | `python3 -m unittest tests.test_red1_browser_surface_freeze -v`; `python3 -m unittest tests.test_red1_public_entrypoint_boundary_negative -v` | Pass |
| RED1-FILESYSTEM-001 | Filesystem mutation | File create/write/append/move/delete helper paths are blocked/frozen by default. | `python3 -m unittest tests.test_red1_filesystem_git_surface_freeze -v`; `python3 -m unittest tests.test_red1_public_entrypoint_boundary_negative -v` | Pass |
| RED1-GIT-001 | Git automation | No direct runtime git action path is approved or registered. | code review of `runtime` action surfaces; `python3 -m unittest tests.test_red1_filesystem_git_surface_freeze -v` | Pass |
| RED1-PROVIDER-001 | Provider/network | Provider/model calls are blocked/default-off; local catalog/config paths remain non-networked. | `python3 -m unittest tests.test_red1_provider_network_gateway_separation -v`; `python3 -m unittest tests.test_red1_boundary_negative -v` | Pass |
| RED1-SHELL-001 | Shell/executor | Shell/executor paths are blocked/frozen by default and reviewer-safe entrypoints cannot execute commands. | `python3 -m unittest tests.test_red1_shell_executor_freeze -v`; `python3 -m unittest tests.test_reviewer_safe_execution_lock -v` | Pass |
| RED1-PUBLIC-001 | Public runtime/web entrypoints | Public/runtime entrypoints cannot bypass frozen surfaces. | `python3 -m unittest tests.test_red1_public_entrypoint_boundary_negative -v` | Pass |
| RED1-APPROVAL-001 | Approval semantics | `allowed=True` and human approval remain review state only, not execution permission. | `python3 -m unittest tests.test_reviewer_safe_execution_lock -v`; `python3 -m unittest tests.test_red1_approval_provenance_boundary -v` | Pass |
| RED1-UNTRUSTED-001 | Provider output trust boundary | Provider/model output remains UNTRUSTED and cannot claim canonical or execution authority. | `python3 -m unittest tests.test_red1_approval_provenance_boundary -v`; `python3 -m unittest tests.test_red1_provider_network_gateway_separation -v` | Pass |
| RED1-VALIDATION-001 | Whole-tree validation | RED-1 closure evidence must survive full repo validation. | `python3 -m compileall -q runtime tests`; `python3 -m unittest discover -s tests`; `node --check web/app.js`; `git diff --check` | Pass |

## Minimum grep/code-review evidence

These grep hits are acceptable only when they appear in frozen paths, docs, tests, or guarded code.

- shell primitives: `subprocess|os.system|Popen|exec\(|eval\(`
- provider/network primitives: `requests|urllib|httpx|socket|aiohttp`
- browser automation primitives: `selenium|playwright|puppeteer|webdriver`
- filesystem/git mutation primitives: `write_text|write_bytes|unlink|shutil|os.rename|os.remove|git `
- public endpoint primitives: `app.run|flask|fastapi|uvicorn|http.server`
- semantic boundary strings:
  - `allowed=True`
  - `UNTRUSTED`
  - `human approval`
  - `AOIA_SHELL_EXECUTION_ENABLED`
  - `AOIA_PROVIDER_CALLS_ENABLED`

## Required semantic boundaries

RED-1 is acceptable only if the repo and reviewer docs make all of the following true:

- AOIA-Core is not currently an autonomous agent.
- No production shell execution flow is approved.
- No production browser automation flow is approved.
- No model-to-action chain is approved.
- Provider/model output remains UNTRUSTED.
- `allowed=True` does not imply execution.
- Human approval does not imply execution.
- No automatic canonical knowledge promotion is approved.
- No model-to-git chain is approved.

## Acceptance boundary

RED-1 closure means:

- major dangerous legacy surfaces are identified;
- major action-capable surfaces are frozen/default-off where applicable;
- negative tests exist for the main public/reviewer-safe boundaries;
- reviewer-facing documentation matches the actual boundary posture.

RED-1 closure does **not** mean:

- provider integration is approved;
- execution architecture is approved;
- sandboxed execution exists;
- a controlled agent loop exists.
