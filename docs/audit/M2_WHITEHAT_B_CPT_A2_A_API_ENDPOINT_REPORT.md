# M2 Whitehat B CPT-A2-A API Endpoint Report

## Purpose

Add a local backend-only CPT preview endpoint for transforming a user prompt before any manual send flow exists.

## Endpoint Behavior

- `POST /api/cpt/transform`
- Input: `{"prompt": "...", "mode": "balanced_critic"}`
- `mode` defaults to `balanced_critic`.
- Success returns `ok: true` plus a small CPT record with hashes, transformed prompt, canonical status, and inert safety flags.
- Errors return `ok: false` with a clear error message.
- The endpoint uses `runtime.cpt.transformer.transform_prompt`.

## Changed Files

- `runtime/webapp.py`
- `tests/test_cpt_api_preview.py`
- `docs/audit/M2_WHITEHAT_B_CPT_A2_A_API_ENDPOINT_REPORT.md`

## Tests

- `tests.test_cpt_api_preview`
- Existing CPT schema, sanitizer, transformer, security, audit, and hardening tests.
- Full unittest discovery.

## Validation

Validation was run locally with compile, focused CPT API tests, existing CPT tests, full unittest discovery, diff check, and git status.

## Explicit Non-Goals

- No UI in CPT-A2-A.
- No provider calls.
- No auto-send.
- No audit auto-write.
- No browser or shell action.
- RED-1 is not closed by this task.
