# M1 Router Controlled Model Router Reviewer Note

Date: 2026-06-08

## Status

DOCS-ONLY / REVIEWER NOTE / NO RUNTIME CHANGE

This note records the reviewer-facing state of the Controlled Model Router UI after the M1-ROUTER-B and M1-ROUTER-B2 UI cleanup checkpoints.

The current UI should be described as a controlled model selection/proposal UI. It should not be described as an autonomous model router.

## What Changed In M1-ROUTER-B/B2

The main web UI is now centered on Controlled Model Router selection.

Provider and model selection uses the controlled model catalog path. The main selection state is separate from legacy runtime model state.

Legacy session details, legacy composer controls, and legacy model-switching UI were moved under:

```text
Advanced / Legacy runtime
```

Raw JSON, audit flags, router booleans, and catalog detail were moved under:

```text
Advanced / Audit details
```

User-facing router statuses were simplified into readable English so reviewers do not have to interpret raw enum labels in the main screen.

## What This Phase Does Not Do

This phase does not execute shell commands.

This phase does not launch browser automation.

This phase does not call provider APIs.

This phase does not make model output trusted.

This phase does not promote provider output to canonical knowledge.

This phase does not change the approval gate, executor, shell tools, memory hats, browser tools, provider policy, or runtime router backend logic.

The UI itself does not grant execution permission.

## Current Safety Boundary

Provider and model selection remains a controlled selection/proposal UI boundary.

Provider calls remain gated by backend policy.

OpenRouter Free and generic free model paths remain blocked for sensitive, canonical, or secret-adjacent tasks.

Provider output remains untrusted.

Human approval remains required where configured.

No automatic fallback should be claimed for this phase.

## Validation Evidence From Previous Checkpoint

The M1-ROUTER-B2 checkpoint reported the following validation results before commit:

- `python3 -m compileall -q runtime tests` passed
- focused router tests passed: 41 tests
- full unittest discovery passed: 579 tests, 4 skipped
- `node --check web/app.js` passed
- `git diff --check` passed
- secret scan found no real secrets; only false positives on `router-task-mode`

These validation results support the UI cleanup checkpoint only. They should not be interpreted as a general security validation of provider calls.

## Reviewer Interpretation

Reviewers should treat the current UI as an explicit model selection and proposal surface.

The UI makes provider/model choice more visible and moves legacy runtime controls and detailed audit data out of the primary screen.

Provider output remains external, untrusted material until separately reviewed under the existing AOIA boundaries.

## Next Intended Steps

Planned follow-up work:

1. M1-ROUTER-D: small boundary tests or checks if useful.
2. M1 final checkpoint report.
3. After router closure, return to Chat4/H4 helper-bot governance planning.
