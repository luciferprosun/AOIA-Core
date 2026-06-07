# Chat4 Proposal Based Workflow

Date: 2026-06-07

Phase: C4-A docs-only agentic readiness policy.

## Purpose

This document describes a future proposal lifecycle for helper-model review artifacts.

C4-A does not implement schemas, agents, bots, storage, routing, tests, or runtime behavior. This is prose only.

## Lifecycle States

Future proposal artifacts may move through these states:

- `DRAFT`
- `UNDER_REVIEW`
- `NEEDS_REVISION`
- `REJECTED`
- `APPROVED_FOR_MANUAL_ACTION`
- `ARCHIVED`

`APPROVED_FOR_MANUAL_ACTION` means a human may perform a separate manual action. It does not authorize automatic execution.

## Required Invariants

Every future proposal artifact must obey these invariants:

- `status` starts as `DRAFT`
- `canonical_status` starts as `NOT_CANONICAL`
- `verification_status` starts as `UNVERIFIED`
- `human_review_required` is `true`
- `execution_permitted` is `false`
- `automatic_commit_permitted` is `false`
- source provenance is required
- model output is untrusted until reviewed

## Future Object Descriptions

The names below are future object descriptions only. C4-A does not implement them as schemas.

## ModelResearchProposal

A proposed research direction from a helper model.

It may describe why a source area might be relevant, what question it could answer, and what provenance fields a human would need to collect.

It is not verified evidence.

## SourceCandidate

A candidate source reference for human review.

It should include proposed source title, source type, source locator, capture timestamp, model name if model-assisted, and reviewer questions.

It is not canonical knowledge.

## HatKnowledgeCandidate

A candidate knowledge entry for one Hat domain.

It should include proposed domain, source linkage, risk classification, duplicate references, and uncertainty notes.

It must remain separate from canonical records.

## HatUpdateProposal

A proposed update to existing Hat material.

It may explain a possible addition, clarification, contradiction, or replacement, but it must not directly edit existing Hat 001, Hat 002, or Hat 003 records.

## ContradictionReport

A report that two or more records, candidates, or sources may conflict.

It should identify the conflicting claims and ask a human reviewer to decide whether the conflict is real.

## GapReport

A report that a Hat domain may be missing coverage.

It should describe the suspected gap, why it matters, and what source evidence would be needed before any manual update.

## ReviewerDecision

A human-authored decision record.

It may accept, reject, request revision, approve manual action, or archive a proposal. A helper model may draft decision wording, but the decision itself belongs to a human reviewer.

## AuditTrailEntry

A review trace entry.

It should record what was proposed, who reviewed it, what decision was made, and what source or policy evidence supported the decision.

## Lifecycle Notes

No proposal lifecycle state allows automatic execution, automatic commit, automatic browser action, automatic source verification, or automatic canonical promotion.

Human review is not a formality. It is the controlling authority.
