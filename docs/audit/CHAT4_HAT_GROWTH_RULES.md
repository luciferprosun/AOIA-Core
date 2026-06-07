# Chat4 Hat Growth Rules

Date: 2026-06-07

Phase: C4-A docs-only agentic readiness policy.

## Purpose

This document defines a safe future growth workflow for Hat 001, Hat 002, and Hat 003 knowledge.

C4-A does not add, edit, promote, or verify Hat records.

## Domain Separation

Hat domains are explicit:

- Hat 001 = Bash / shell safety / pre-execution command inspection
- Hat 002 = Linux / RHCSA
- Hat 003 = Python Knowledge Library

Material must not cross domains without an explicit human-reviewed reason.

## Growth Workflow

1. Source discovery

   A helper model may propose source leads only. Source discovery is not source verification.

2. Source capture

   A human reviewer controls source capture. Source URL or locator, timestamp, capture method, source type, and quarantine location are recorded where applicable.

3. Candidate entry creation

   Candidate records are separate from canonical records. Candidate source IDs are required. Model name and timestamp are recorded. Source type is recorded. Verification starts `UNVERIFIED`. Canonical status starts `NOT_CANONICAL`.

4. Duplicate check

   Duplicates are linked, not silently merged. Similar candidates remain reviewable until a human resolves the relationship.

5. Domain separation check

   Hat domain ownership is checked before review continues. Domain boundaries are explicit.

6. Risk classification

   Proposed command/code snippets are inert text only. Risk classification is advisory until a human reviewer accepts it.

7. Source verification queue

   Candidate material enters a verification queue. Model output does not verify sources.

8. Human review

   Human review checks source provenance, domain fit, duplicate links, contradictions, risk classification, and wording.

9. Promotion rules

   Bot cannot directly add canonical knowledge. Bot cannot directly edit existing Hat records. Promotion requires separate human approval and must preserve provenance.

10. Commit rules

   Commits are human-controlled. A helper model may draft a commit summary, but it must not stage, commit, push, or approve repository changes.

## Mandatory Candidate Fields

Future candidate records should record:

- candidate source ID
- source type
- source locator
- capture timestamp
- model name when model-assisted
- model output timestamp when model-assisted
- Hat domain
- verification status starting as `UNVERIFIED`
- canonical status starting as `NOT_CANONICAL`
- duplicate links where applicable
- reviewer questions

## Hard Boundaries

Bot cannot directly add canonical knowledge.

Bot cannot directly edit existing Hat records.

Candidate records are separate from canonical records.

Proposed command/code snippets are inert text only.

Duplicates are linked, not silently merged.

Domain boundaries are explicit.
