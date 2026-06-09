# M1 Controlled Model Router Final Checkpoint

Date: 2026-06-09

## Status

FINAL CHECKPOINT / DOCS-ONLY / NO RUNTIME CHANGE

## 1. Executive Summary

M1 closes the Controlled Model Router UI and proposal phase.

The completed work should be described as controlled model selection/proposal with policy-gated provider invocation. Provider output remains untrusted. Human approval remains required where configured.

This checkpoint does not claim autonomous routing, safe provider execution, production security validation, trusted model output, automatic fallback, or agentic execution.

## 2. Completed Commits

```text
776b38368058a66d2f78c045d1a3c41353bf46f0
ui: simplify controlled model router selection
```

This commit simplified the web UI around the Controlled Model Router path. It moved legacy runtime controls into advanced sections, moved raw audit/catalog detail out of the main screen, and mapped user-facing router status text to readable English.

```text
3e455c35d21ff835fc39001f77b63c9e2ad74866
docs: add controlled model router reviewer note
```

This commit added a reviewer-facing note explaining the current controlled model selection/proposal UI, what it does not do, and the safety boundaries reviewers should apply when reading the UI.

```text
563d8dac160fa1c655280908607432afde81adac
tests: add controlled model router boundary checks
```

This commit added focused tests proving that model selection/proposal remains non-executing, non-canonical, non-fallback, and non-provider-calling unless the existing backend policy and explicit approval path permit invocation.

## 3. Current Behavior

The main UI now centers on Controlled Model Router.

Provider and model selection uses the controlled model catalog path.

Legacy session, legacy composer, and legacy model-switching UI are under:

```text
Advanced / Legacy runtime
```

Raw JSON, audit flags, router booleans, and catalog detail are under:

```text
Advanced / Audit details
```

User-facing statuses are mapped to readable English.

Model proposal and selection are not provider execution.

Provider calls remain blocked unless backend policy permits them.

OpenRouter Free and generic free routes remain blocked for sensitive, canonical, and secret-adjacent tasks.

Provider output remains untrusted, non-canonical, non-executing, and does not trigger fallback.

## 4. Boundary Evidence

After M1-ROUTER-B/B2:

- `python3 -m compileall -q runtime tests` OK
- focused router tests OK: 41 tests
- full unittest discovery OK: 579 tests, 4 skipped
- `node --check web/app.js` OK
- `git diff --check` OK
- secret scan found no real secrets; only false positives on `router-task-mode`

After M1-ROUTER-C:

- `python3 -m compileall -q runtime tests` OK
- full unittest discovery OK: 579 tests, 4 skipped
- `node --check web/app.js` OK
- `git diff --check` OK
- secret scan found no real secrets; false positives only around secret-adjacent wording and previous secret scan wording

After M1-ROUTER-D:

- `python3 -m compileall -q runtime tests` OK
- targeted boundary tests OK: 5 tests
- full unittest discovery OK: 584 tests, 4 skipped
- `node --check web/app.js` OK
- `git diff --check` OK
- secret scan found no real secrets; false positives only on `secret_adjacent` test naming and `TaskSensitivity.SECRET_ADJACENT`

These results support the M1 router checkpoint. They should not be interpreted as a broad production security validation of provider execution.

## 5. Explicit Non-goals

M1 did not add autonomous agents.

M1 did not add bot swarms.

M1 did not add browser automation.

M1 did not add shell execution.

M1 did not add provider/API/model calls by default.

M1 did not add trusted model output.

M1 did not add automatic fallback.

M1 did not promote provider output into canonical memory.

M1 did not modify `executor.py`, `shell_tools.py`, `browser_tools.py`, `web_reader.py`, memory hats storage, providers, CI, or packaging.

## 6. Reviewer Quick Path

For a short review path:

1. Inspect this final checkpoint report.
2. Inspect `docs/audit/M1_ROUTER_CONTROLLED_MODEL_ROUTER_REVIEWER_NOTE.md`.
3. Inspect `tests/test_m1_router_boundary_checks.py`.
4. Run:

```text
python3 -m compileall -q runtime tests
python3 -m unittest discover -s tests
node --check web/app.js
git diff --check
```

## 7. Next Phase

The recommended next phase is not router expansion.

Recommended sequence:

1. Freeze M1 as a stable router checkpoint.
2. Return to Chat4/H4 helper-bot governance planning.
3. Keep bots and helper agents under proposal-only, approval-gated, non-executing design until separately reviewed.
