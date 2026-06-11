# M2 Whitehat B CPT-A2-B Composer UI Report

## Purpose

Add a manual Critic Transform control to the existing chat composer.

## Changed Files

- `web/index.html`
- `web/app.js`
- `web/styles.css`
- `tests/test_cpt_ui_preview.py`
- `docs/audit/M2_WHITEHAT_B_CPT_A2_B_COMPOSER_UI_REPORT.md`

## UI Behavior

- The user enters text in the legacy chat composer.
- The user clicks `Critic Transform`.
- The frontend posts to `/api/cpt/transform` with `mode: balanced_critic`.
- On success, the composer text is replaced with the transformed CPT prompt.
- The transformed prompt remains editable.
- The user must manually send with Enter or the Send button.

## Endpoint Used

- `POST /api/cpt/transform`

## Safety Boundaries

- Transform modifies composer text only.
- No provider call during transform.
- No auto-send.
- No browser or shell action.
- No telemetry, cookies, `localStorage`, or `sessionStorage`.
- CPT improves critical framing, not truth.
- Human review remains required.
- RED-1 is not closed by this task.

## Tests Run

- `python3 -m compileall -q runtime tests`
- `python3 -m unittest tests.test_cpt_api_preview -v`
- `python3 -m unittest tests.test_cpt_ui_preview -v`
- Existing CPT schema, sanitizer, transformer, security, audit, and hardening tests.
- Full `python3 -m unittest discover -s tests`
- `node --check web/app.js`
- `git diff --check`

## Known Limitations

- CPT does not verify truth.
- CPT does not make output safe.
- CPT does not send automatically.
- The legacy runtime send path remains separate and manual.
