# Hat 004 Browser Surface Freeze Report

Date: 2026-06-07

Branch: `dev/gt-runtime-8-bash-safety-planning`

Purpose: H4-C freeze/documentation/test-boundary phase only.

## Executive Verdict

H4-C freezes the current browser-adjacent surface for reviewer inspection.

Existing browser-adjacent code is `NOT_APPROVED_H4`. Existing browser actions in the generic executor are `NOT_APPROVED_H4`. H4-C adds no browser execution capability, no browser routing, no provider routing, no model routing, no autonomous online action, and no browser control.

This report is documentation only. The accompanying tests are inert static boundary tests only.

## Current Browser-Adjacent Surfaces

Current architecture inputs and risk boundaries:

- `runtime/tools/browser_tools.py`
- `runtime/tools/web_reader.py`
- `runtime/tools/executor.py`
- `runtime/tools/event_ledger.py`
- `runtime/safety/approval_gate.py`
- `runtime/schemas/approval_decision.py`
- `runtime/schemas/approval_audit_event.py`
- `runtime/webapp.py`
- `runtime/providers/`

These files were inspected as current context only. H4-C does not modify them.

## Browser Tools Status

`runtime/tools/browser_tools.py` already contains an older Playwright-oriented `BrowserBridge` surface with actions such as:

- browser session start and close
- URL open
- click
- type/fill text
- key press
- read HTML
- read visible text
- screenshot
- current URL

H4-C classification:

- this surface is `NOT_APPROVED_H4`
- this surface is not Hat 004 governance
- this surface is not a controlled browser policy layer
- this surface is not approved for login, credentials, cookies, sessions, downloads, form submission, scraping, or autonomous navigation
- this surface must be reviewed before any future Hat 004 implementation reuses or wraps it

## Generic Executor Browser Actions

`runtime/tools/executor.py` currently imports browser tool functions and registers browser actions in the generic tool registry.

Observed browser action names:

- `browser_start`
- `browser_open`
- `browser_click`
- `browser_type`
- `browser_press`
- `browser_read_html`
- `browser_get_visible_text`
- `browser_screenshot`
- `browser_close`
- `browser_current_url`

H4-C classification:

- these executor entries are `NOT_APPROVED_H4`
- these executor entries are not approved Hat 004 flow
- these executor entries do not prove browser governance exists
- these executor entries should be treated as legacy architecture risk boundaries
- future Hat 004 work must define browser-specific proposal objects, human review states, event schemas, and forbidden action gates before runtime action integration

## Web Reader Status

`runtime/tools/web_reader.py` is a separate web-fetching surface.

H4-C classification:

- this surface is `NOT_APPROVED_H4`
- this surface is not browser automation
- this surface is not approved scraping
- this surface is not approved provider/API routing
- this surface requires separate review before any Hat 004 page-reading design

## No New Capability Statement

H4-C does not:

- implement browser automation
- launch a browser
- add browser control
- add Playwright
- add Selenium
- add `requests`
- add browser routing
- add provider routing
- add model routing
- add execution logic
- add autonomous actions
- add download automation
- add login support
- add credential handling
- add cookie handling
- add session handling
- add form submission
- modify runtime behavior

## Required Future Browser Governance

Future browser work must be proposal-based and human-reviewed.

Before any implementation, Hat 004 must define:

- browser proposal schema
- browser action taxonomy
- read-only action list
- approval-required action list
- always-forbidden action list
- URL normalization and display rules
- redirect handling rules
- local-only browser session boundaries
- screenshot storage and redaction policy
- download quarantine policy
- cookie and session prohibitions
- credential redaction and non-capture rules
- browser audit event schema
- tests proving forbidden actions cannot enter runtime action flow

## Near-Term Forbidden Scope

The following remain forbidden for current and near-term Hat 004 work:

- website login
- password entry
- credential handling
- account creation
- payment actions
- checkout
- form submission without explicit human review
- browser extension installation
- software or package installation
- scraping at scale
- CAPTCHA bypass
- stealth automation
- cookie or session theft
- provider or API key handling
- autonomous online actions

## Validation Added By H4-C

H4-C adds inert boundary tests in:

- `tests/hat004/test_browser_surfaces_frozen.py`

The tests:

- inspect source files as text
- confirm current browser action names are documented as frozen
- confirm policy documents mark legacy browser surfaces as `NOT_APPROVED_H4`
- confirm the policy contains no-login, no-credential, no-cookie, no-session, no-autonomous-navigation boundaries
- avoid importing or executing browser runtime code
- avoid launching browsers
- avoid network access

## Reviewer Conclusion

H4-C is a freeze point, not implementation.

Existing browser-adjacent code remains an architecture input and risk boundary. It is not approved Hat 004 governance. Any future controlled browser use must pass a separate reviewer-approved design and test phase before runtime action flow is changed.
