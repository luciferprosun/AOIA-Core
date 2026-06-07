# Hat 004 Inert Schema Definition

Date: 2026-06-07

Branch: `dev/gt-runtime-8-bash-safety-planning`

Phase: H4-B inert governance schemas only.

## Executive Verdict

H4-B defines inert proposal vocabulary only.

No browser automation was implemented. No browser was launched. No Playwright, Selenium, `requests`, browser routing, provider routing, model routing, or execution logic was added. No PDF or ZIP file was read, created, modified, packed, unpacked, or parsed.

The new schema file is a proposal-shape definition for future controlled browser/file/PDF/ZIP governance. It is not a runtime action path.

## Files Created

H4-B creates:

- `runtime/schemas/hat004_action_proposals.py`
- `tests/hat004/test_hat004_action_proposals.py`
- `docs/audit/HAT_004_INERT_SCHEMA_DEFINITION.md`

No runtime execution behavior was modified.

## Schema Purpose

`runtime/schemas/hat004_action_proposals.py` defines:

- `Hat004ActionDomain`
- `Hat004ReviewState`
- read-only candidate action names
- human-review-required candidate action names
- near-term forbidden action names
- `Hat004ActionProposal`

The schema is designed for proposal records only.

Required inert defaults:

- `dry_run`: `true`
- `proposal_only`: `true`
- `execution_permitted`: `false`
- `autonomous_action`: `false`
- `login_requested`: `false`
- `credential_handling_requested`: `false`
- `cookie_access_requested`: `false`
- `session_access_requested`: `false`
- `form_submission_requested`: `false`
- `download_requested`: `false`
- `file_write_requested`: `false`
- `pdf_parse_requested`: `false`
- `zip_unpack_requested`: `false`
- `external_network_action_requested`: `false`

Any attempt to construct a proposal with execution, autonomous, login, credential, cookie, session, form-submission, download, file-write, PDF-parse, ZIP-unpack, or external-network flags enabled is rejected.

Dictionary payloads are also bounded: `from_dict()` rejects unknown fields instead of silently carrying session-like, credential-like, or execution-like data through the schema.

## Action Vocabulary

Read-only candidate actions:

- `browser_read_current_url`
- `browser_read_page_title`
- `browser_read_visible_text`
- `browser_list_visible_links`
- `browser_list_visible_form_fields`
- `file_describe_local_candidate`
- `pdf_describe_candidate`
- `zip_describe_candidate`

Human-review-required candidate actions:

- `browser_open_url`
- `browser_follow_link`
- `browser_click_visible_element`
- `browser_type_text`
- `browser_press_enter`
- `browser_capture_screenshot`
- `file_prepare_download_review`
- `pdf_extract_text_review`
- `zip_list_entries_review`
- `zip_extract_review`

Near-term forbidden actions:

- `browser_login`
- `browser_enter_password`
- `browser_handle_credentials`
- `browser_create_account`
- `browser_payment_action`
- `browser_checkout`
- `browser_submit_form_without_review`
- `browser_install_extension`
- `browser_captcha_bypass`
- `browser_stealth_automation`
- `browser_cookie_access`
- `browser_session_access`
- `browser_autonomous_navigation`
- `file_execute_download`
- `pdf_parse_without_review`
- `zip_unpack_without_review`

## Boundary Statement

H4-B does not approve any current browser-adjacent runtime surface.

H4-B does not approve:

- old browser actions in the generic executor
- `runtime/tools/browser_tools.py`
- `runtime/tools/web_reader.py`
- provider or API routing
- event ledger browser integration
- browser login
- credential handling
- cookie or session access
- autonomous navigation
- PDF parsing
- ZIP listing or extraction
- file download handling

The schema can represent action proposals, including forbidden action names, so reviewers can test and discuss policy boundaries without executing anything.

## Test Coverage

`tests/hat004/test_hat004_action_proposals.py` checks:

- read-only browser proposal shape
- human-review-required browser proposal shape
- near-term forbidden browser action representation
- file, PDF, and ZIP proposal domains
- round-trip dictionary serialization
- rejection of execution and autonomous flags
- rejection of login, credential, cookie, session, and form-submission flags
- rejection of download, file-write, PDF-parse, ZIP-unpack, and external-network flags
- rejection of unknown dictionary payload fields
- rejection of mismatched derived dictionary payload fields
- rejection of unknown action types
- disjoint action vocabulary sets
- absence of runtime execution/browser imports in the schema module
- this report's non-implementation statement

## Non-Implementation Statement

H4-B did not:

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
- modify runtime execution behavior
- touch executor, browser tools, web reader, shell tools, approval gate, event ledger, providers, or webapp files
- read real PDF files
- create real PDF files
- modify real PDF files
- parse real PDF files
- read real ZIP files
- create real ZIP files
- modify real ZIP files
- pack real ZIP files
- unpack real ZIP files
- call APIs
- call model providers
- install packages
- commit
- push

## Reviewer Conclusion

H4-B is safe to review as an inert vocabulary and schema phase.

It defines future proposal language for controlled browser/file/PDF/ZIP governance while preserving the H4-C browser surface freeze and no-execution boundary.
