# RED-1 Blocker Register

Register status: OPEN

Scope: Reviewer-facing blocker register for AOIA-Core before helper-bot production

Date: 2026-06-09

Baseline branch: dev/gt-runtime-8-bash-safety-planning

Baseline commit: 219b0da28a5e65a8c223c203a1f194744b601935

This register records blocking issues found during RED-1 adversarial review. It does not claim these blockers are fixed. It exists to make known risk surfaces visible, grep-checkable, and reviewable before any helper-bot production work.

## BLOCKER-01 — runtime/main.py browser paths may bypass approval

Status: OPEN

Severity: CRITICAL

Primary files: `runtime/main.py`, `runtime/tools/browser_tools.py`, `runtime/tools/web_reader.py`

Current evidence command: `grep -RIn "require_approval=False" runtime/main.py`

Acceptance criterion: closed only when the listed grep command no longer exposes an unguarded active path, or when a dedicated negative test proves the path is blocked by default.

Fix type: explicit legacy guard, approval gate mapping, or negative test coverage.

Must not be fixed by: deleting history, hiding browser references, or relabeling the path without proving the default block.

Notes: Browser-like paths must remain outside helper-bot production until approval behavior is grep-verifiable or test-verifiable.

## BLOCKER-02 — runtime/main.py still presents legacy autonomous-runtime wording or behavior

Status: OPEN

Severity: HIGH

Primary files: `runtime/main.py`, `README.md`, `STATUS.md`, `docs/audit/`

Current evidence command: `grep -RIn "Autonomous local runtime" runtime/main.py`

Acceptance criterion: closed only when reviewer-facing wording and runtime-visible behavior no longer imply autonomous execution, or when a dedicated reviewer note and negative tests prove the legacy wording is unreachable from current claims.

Fix type: wording correction, explicit legacy labeling, or test-backed boundary note.

Must not be fixed by: broad README rewrites, maturity claims, or removing context needed by reviewers.

Notes: Legacy wording can mislead reviewers even when safety boundaries exist elsewhere.

## BLOCKER-03 — legacy executor/shell surfaces remain visible in live tree

Status: OPEN

Severity: CRITICAL

Primary files: `runtime/executor.py`, `runtime/tools/shell_tools.py`, `runtime/commands/`, shell safety tests

Current evidence command: `grep -RInE "subprocess|os\.system|shell=True|exec\(|eval\(" runtime runtime/tools runtime/commands`

Acceptance criterion: closed only when the listed grep command no longer exposes an unguarded active execution path, or when dedicated negative tests prove helper-bot and router proposals cannot reach shell/executor primitives by default.

Fix type: execution surface register, default-deny guards, or diagnostic negative tests.

Must not be fixed by: deleting grep-visible terms, renaming functions, or weakening shell safety claims.

Notes: The issue is not the existence of historical code alone; the blocker is unresolved reachability and reviewer clarity.

## BLOCKER-04 — browser/web-reader surfaces remain present while H4 is not approved

Status: OPEN

Severity: CRITICAL

Primary files: `runtime/tools/browser_tools.py`, `runtime/tools/web_reader.py`, `runtime/main.py`, H4 governance docs

Current evidence command: `grep -RInE "playwright|browser_tools|web_reader|requests\.get|urlopen|urllib" runtime`

Acceptance criterion: closed only when browser and web-reader surfaces are mapped as frozen or guarded, and negative tests prove helper-bot proposals cannot browse, fetch, download, or ingest web output by default.

Fix type: browser/output quarantine mapping, default-deny tests, or explicit legacy guard.

Must not be fixed by: adding browser automation, adding provider calls, or treating browser output as trusted evidence.

Notes: H4 remains unapproved for production behavior until browser and web-reader reachability is proven blocked.

## BLOCKER-05 — provider/network call surfaces require complete gate coverage proof

Status: OPEN

Severity: HIGH

Primary files: `runtime/provider_clients.py`, `runtime/provider_config.py`, `runtime/provider_audit.py`, `runtime/model_router.py`

Current evidence command: `grep -RInE "requests\.|urllib|httpx|aiohttp|websocket|socket|urlopen" runtime tests docs`

Acceptance criterion: closed only when every provider/network-capable path has either explicit policy-gate coverage or a negative test proving no provider/API/model call occurs without configured permission and human approval.

Fix type: gate coverage matrix, negative tests, or provider-call audit mapping.

Must not be fixed by: claiming provider calls are safe, adding automatic fallback, or moving calls behind less visible wrappers.

Notes: M1 proves some controlled router boundaries, but RED-1 requires complete coverage proof before helper-bot production.

## BLOCKER-06 — file-write/delete/canonical-promotion surfaces require explicit guard mapping

Status: OPEN

Severity: HIGH

Primary files: `runtime/`, `knowledge/`, `memory/`, `runtime/memory_hats/`

Current evidence command: `grep -RInE "write_text|unlink|remove\(|shutil|delete_file|promote|canonical" runtime knowledge memory`

Acceptance criterion: closed only when file-write, delete, Git, and canonical-promotion paths are mapped and tests prove helper-bot proposals cannot write, delete, commit, or promote without a later approved governance path.

Fix type: file mutation surface register, canonical promotion guard map, or negative tests.

Must not be fixed by: broad cleanup, moving files, or treating draft helper-bot output as canonical.

Notes: Canonical promotion must remain human-reviewed and separate from proposal generation.

## BLOCKER-07 — helper-bot proposal boundary lacks negative tests

Status: OPEN

Severity: CRITICAL

Primary files: `runtime/`, `tests/`, `docs/audit/CHAT4_H4_POST_M1_HELPER_BOT_PRODUCTION_PLAN.md`

Current evidence command: `grep -RInE "helper|chat4|hat004|execution_permitted|canonical|human_review" runtime tests docs`

Acceptance criterion: closed only when dedicated negative tests prove helper-bot proposals cannot execute, browse, fetch, call providers, write files, commit, or promote canonical knowledge by default.

Fix type: diagnostic negative tests for proposal-only helper-bot boundaries.

Must not be fixed by: implementing bots first, adding schemas without tests, or relying on documentation-only assurances.

Notes: Helper-bot production remains blocked until proposal-only behavior is test-verifiable.

## Next Safe Steps

1. Create a RED-1 execution surface register if more detailed primitive mapping is needed.
2. Add diagnostic negative tests proving helper-bot proposals cannot reach execution, browser, provider, file-write, Git, or canonical-promotion surfaces.
3. Only after those tests exist, consider minimal code-hardening such as source-provenance checks or explicit legacy guards.
