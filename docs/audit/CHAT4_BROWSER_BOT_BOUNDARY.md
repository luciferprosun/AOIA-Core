# Chat4 Browser Bot Boundary

Date: 2026-06-07

Phase: C4-A docs-only agentic readiness policy.

## Relationship To H4

C4-A does not approve browser use.

Helper bots cannot use browser outputs until H4 governance is reviewed.

Current old `browser_tools`, `web_reader`, and executor browser actions are not approved H4 flow.

H4-C froze existing browser-adjacent runtime surfaces as not approved for H4. H4-B added inert proposal vocabulary only. C4-A does not change that status.

## Browser-visible Material

Browser-visible text is candidate source material only.

Browser output is not verified knowledge.

For any future browser-derived source, the following fields are required:

- source URL
- timestamp
- capture method
- local quarantine path
- reviewer identity or review queue identity
- verification status

## Required Human Control

A human reviewer must decide whether browser-derived material is allowed into a candidate queue.

No helper model may treat browser text, screenshots, page titles, URLs, or visible links as verified evidence without review.

## Forbidden For Helper Bots

Helper bots must not perform or trigger:

- login
- password entry
- credential handling
- cookie/session access
- downloads unless quarantined and human-approved
- form submission
- CAPTCHA interaction
- scraping/crawling
- autonomous navigation chains
- direct model-to-browser action

## Browser Output Quarantine

Any future browser-derived source must remain quarantined until a human reviewer checks:

- source identity
- capture method
- timestamp
- URL or locator
- local quarantine path
- domain relevance
- source trust limits
- privacy or credential risk

## Non-implementation Statement

C4-A does not launch a browser, call browser tools, add browser routing, approve browser actions, or create browser automation.
