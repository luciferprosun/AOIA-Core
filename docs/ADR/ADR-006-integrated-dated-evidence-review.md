# ADR-006: Integrate Dated Evidence Review into AOIA-Core

Date: 2026-08-25

Status: Accepted

## Context

A bounded dated-evidence prototype existed outside the canonical AOIA-Core runtime. Keeping a separate package, launch script, HTTP server, UI identity, and test suite created two product surfaces for one architecture. The operator explicitly requested consolidation into AOIA-Core.

The useful capability is the deterministic review contract: validate candidate text, compare known dated values, expose official source metadata, bind inputs and evidence with SHA-256, and always stop at human review.

## Decision

- Place the canonical implementation under `runtime/evidence_review/`.
- Expose it through the existing slash-command registry as `/review`.
- Expose it through the existing `runtime/webapp.py` server.
- Present it as a module in the existing `web/` console.
- Keep the module provider-independent, read-only, deterministic, and non-authoritative.
- Keep one bundled scenario until a separate extension decision defines a general scenario schema and matcher contract.
- Do not import competition presentation, judging, or submission material into runtime authority.

## Consequences

- AOIA-Core has one active runtime and one operator-facing identity.
- The separate demonstration server and package entrypoint are unnecessary.
- Existing assistant provider selection does not affect evidence-review output.
- All successful reviews still return `HUMAN_REVIEW_REQUIRED` and `METADATA_ONLY_NO_AUTHORITY`.
- New scenario types require explicit design and tests; the current euro-value matcher must not be generalized by assumption.

## Validation requirement

The decision is complete only when focused engine/API/boundary tests and the full AOIA-Core suite pass, active surfaces contain no retired identity, and the unified web launch serves both assistant and evidence-review views from loopback.
