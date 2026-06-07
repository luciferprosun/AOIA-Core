# Hat 004 Browser Governance Policy

Date: 2026-06-07

Status: draft freeze policy for H4-C only.

## Policy Verdict

Hat 004 is not implemented.

Current browser-adjacent runtime surfaces are `NOT_APPROVED_H4`.

No current AOIA-Core browser action is approved as Hat 004 governance. No current browser-adjacent file authorizes browser execution, browser routing, login, credential handling, cookie handling, session handling, download automation, scraping, or autonomous navigation.

## Scope

This policy applies to future planning for Controlled Browser Use / Web Interaction Governance.

It does not modify runtime behavior. It does not approve any action. It does not create a browser action path.

## Baseline Boundary

All Hat 004 work must remain:

- local-first
- human-led
- audit-first
- source-aware
- reviewer-auditable
- non-executing by default
- proposal-based before action
- blocked by default for risky browser operations

## Current Legacy Surface Classification

The following existing surfaces are architecture inputs only:

- `runtime/tools/browser_tools.py`
- `runtime/tools/web_reader.py`
- `runtime/tools/executor.py`
- `runtime/tools/event_ledger.py`
- `runtime/webapp.py`
- `runtime/providers/`

Classification:

- `runtime/tools/browser_tools.py`: `NOT_APPROVED_H4`
- `runtime/tools/web_reader.py`: `NOT_APPROVED_H4`
- browser actions registered in `runtime/tools/executor.py`: `NOT_APPROVED_H4`
- provider routing for browser work: `NOT_APPROVED_H4`
- event ledger browser-action use: `NOT_APPROVED_H4`

## Future Allowed Read-Only Candidates

These are candidates for future design only, not current implementation:

- read current URL
- read page title
- read visible page text
- list visible links
- list visible form fields without filling them
- capture screenshot only under explicit local storage policy

Each candidate must be represented as a proposal and reviewed against policy before execution is considered.

## Future Human-Review Required Candidates

These are candidates that must require explicit human review in any future design:

- open external URL
- follow link
- click visible element
- type into a field
- press Enter
- upload local file
- accept or save download
- capture screenshot of authenticated or sensitive page
- extract page text from pages containing personal, financial, account, medical, legal, or credential-like content

## Always Forbidden Current/Near-Term Actions

The following are forbidden in current and near-term Hat 004 work:

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
- cookie theft
- session theft
- cookie reuse
- session reuse
- provider key handling
- API key handling
- autonomous online actions
- autonomous navigation

## Proposal Requirements For Future Work

Any future browser action proposal must include:

- action type
- target URL or current URL
- visible target label or selector
- user-visible reason
- read-only or mutating classification
- credential risk classification
- session risk classification
- cookie risk classification
- download risk classification
- form-submission risk classification
- human-review requirement
- local audit event preview

No browser action should enter runtime action flow without a proposal object.

## Audit Event Requirements For Future Work

Future browser audit events must be separate from command audit events.

They should record:

- proposed action
- normalized URL
- visible target text
- risk classifications
- human-review decision
- local-only timestamp
- redacted payload
- no credential values
- no cookie values
- no session tokens
- no password text

Browser audit logs must not claim compliance-grade auditability unless a later audited system provides that property.

## Implementation Freeze

H4-C freezes implementation.

Do not add:

- Playwright
- Selenium
- `requests`
- browser routing
- provider routing
- model routing
- executor integration
- browser action execution
- login support
- download automation
- credential handling
- cookie/session handling
- autonomous action logic

## Reviewer Gate

Before any Hat 004 implementation begins, reviewers should require:

- approved browser action taxonomy
- approved proposal schema
- approved forbidden action list
- approved human-review boundary
- approved browser audit schema
- tests that prove forbidden operations cannot be routed
- explicit decision on whether legacy `browser_tools.py` is disabled, quarantined, wrapped, or replaced

Until that review is complete, Hat 004 remains policy and snapshot only.
