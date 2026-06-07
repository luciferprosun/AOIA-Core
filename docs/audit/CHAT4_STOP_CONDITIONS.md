# Chat4 Stop Conditions

Date: 2026-06-07

Phase: C4-A docs-only agentic readiness policy.

## Purpose

This document defines conditions that stop C4 work.

If any stop condition is triggered:

- C4 work stops.
- Changes are reverted or quarantined.
- Human reviewer decides next step.

## Stop Conditions

C4 work stops if:

- helper bot writes files directly
- helper bot commits
- helper bot touches runtime behavior
- helper bot triggers browser action
- helper bot triggers shell command
- helper bot promotes canonical knowledge
- helper bot verifies sources without human review
- Hat domains are mixed
- docs overclaim autonomy or production readiness
- credential/login/cookie/session access appears
- Gemini/API/model call path is introduced before policy exists
- broad documentation rewrite is auto-approved
- existing Hat 001/002/003 records are edited by a bot

## Quarantine Rule

If a stop condition appears in proposed work, the affected change is quarantined for human review instead of being accepted as normal C4 work.

## Human Decision Rule

Only a human reviewer may decide whether stopped work is rejected, revised, split into a safer task, or resumed under a narrower scope.

## Non-implementation Statement

C4-A does not create enforcement code for these stop conditions. This is policy documentation only.
