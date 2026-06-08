# Chat4 Inert Proposal Schema Definition

Date: 2026-06-08

Phase: C4-B inert helper-model proposal schemas only.

## Purpose

C4-B defines inert helper-model proposal schemas only.

C4-B creates data shapes for future human-reviewed helper-model workflow proposals. These shapes are not bots, agents, runtime routes, execution paths, browser integrations, provider calls, file-writing workflows, commit workflows, or canonical promotion workflows.

## Relationship To C4-A

C4-A documented the agentic readiness policy and the proposal-only boundary.

C4-B turns that policy vocabulary into inert Python dataclasses for future proposal records. C4-B does not expand C4-A into automation.

## Relationship To H4-B

H4-B defined inert browser/file/PDF/ZIP action proposal vocabulary.

C4-B does not alter H4-B. Future helper-model proposal objects remain separate from H4 browser/file governance and cannot use browser-derived material unless H4 governance is reviewed.

## Object Inventory

C4-B defines:

- `ModelResearchProposal`
- `SourceCandidate`
- `HatKnowledgeCandidate`
- `HatUpdateProposal`
- `ContradictionReport`
- `GapReport`
- `ReviewerDecision`
- `AuditTrailEntry`

C4-B also defines enum vocabularies for proposal status, canonical status, verification status, Hat target, and object type.

## Shared Invariants

All future helper-model outputs remain `DRAFT`, `NOT_CANONICAL`, `UNVERIFIED`, human-reviewed, non-executing, and non-committing by default.

Shared proposal invariants:

- `status` is `DRAFT`
- `canonical_status` is `NOT_CANONICAL`
- `verification_status` is `UNVERIFIED`
- `human_review_required` is `True`
- `execution_permitted` is `False`
- `automatic_commit_permitted` is `False`

## Source Provenance Requirement

Source-linked objects require explicit source references.

`HatKnowledgeCandidate` and `HatUpdateProposal` reject empty `source_ids`. `ModelResearchProposal` requires at least one `source_candidate_id`. `GapReport` requires at least one suggested source reference.

Source material remains unverified until human review.

## Hat Domain Separation

C4-B keeps Hat targets explicit:

- `HAT_001_BASH_SAFETY`
- `HAT_002_LINUX_RHCSA`
- `HAT_003_PYTHON_KNOWLEDGE`
- `HAT_004_BROWSER_FILE_GOVERNANCE`
- `UNASSIGNED`

Candidate material is not allowed to silently cross Hat domains.

## No Execution Boundary

C4-B does not execute shell commands.

C4-B proposal objects do not contain execution methods. They do not run commands, invoke runtime tools, launch browsers, call providers, parse files, unpack archives, or mutate repository state.

## No Commit Boundary

C4-B does not create a commit workflow.

`automatic_commit_permitted` remains `False`. `ReviewerDecision` rejects `commit_authorized=True`.

## No Canonical Promotion Boundary

C4-B does not write to canonical knowledge.

C4-B does not promote knowledge. `canonical_status` remains `NOT_CANONICAL`, and `ReviewerDecision` rejects `promotion_allowed=True`.

## Non-goals

C4-B does not:

- implement helper bots
- call Gemini, APIs, or models
- launch a browser
- execute shell commands
- write to canonical knowledge
- create a repo-write workflow
- create a commit workflow
- promote knowledge
- modify existing Hat 001, Hat 002, or Hat 003 records
- modify runtime routing
- install packages

## Stop Conditions

C4-B work stops if any future change requires:

- editing files outside the allowed C4-B file set
- invoking a model or API provider
- launching a browser
- executing shell actions beyond requested validation
- modifying runtime behavior
- adding helper bot behavior
- writing canonical knowledge
- creating commit or promotion automation
- touching unrelated local savepoint or weekend checkpoint files

## Validation Checklist

C4-B is valid only if:

- only `runtime/schemas/chat4_agentic_proposals.py`, `tests/hat004/test_chat4_agentic_proposals.py`, and this report are created or modified
- compile validation passes
- focused C4-B unittest validation passes
- Hat 004 unittest discovery passes
- `git diff --check` passes
- local savepoint and weekend checkpoint files remain untouched
- no forbidden runtime, browser, provider, shell, package, or commit behavior is added

## Non-implementation Statement

C4-B does not implement helper bots.

C4-B does not call Gemini, APIs, or models.

C4-B does not launch a browser.

C4-B does not execute shell commands.

C4-B does not write to canonical knowledge.

C4-B does not create a repo-write workflow.

C4-B does not create a commit workflow.

C4-B does not promote knowledge.
