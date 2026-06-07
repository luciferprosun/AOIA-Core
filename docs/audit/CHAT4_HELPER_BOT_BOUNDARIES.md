# Chat4 Helper Bot Boundaries

Date: 2026-06-07

Phase: C4-A docs-only agentic readiness policy.

## Boundary Summary

The roles below are planned roles only. They are not implemented by C4-A.

Every role has the same mandatory boundary:

- no direct repo writes
- no commits
- no shell execution
- no browser action
- no runtime mutation
- no canonical promotion
- human review required

Allowed future outputs may include:

- `ModelResearchProposal`
- `SourceCandidate`
- `HatKnowledgeCandidate`
- `HatUpdateProposal`
- `ContradictionReport`
- `GapReport`
- `ReviewerDecision`
- `AuditTrailEntry`
- `SafetyReview`
- `ReviewerQuestion`

These are future artifact names only, not C4-A schemas.

## Gemini Source Bot

Status: planned role only, not implemented.

Useful task:

- draft source discovery leads for a human reviewer
- summarize candidate source relevance
- identify missing provenance fields

Allowed output:

- `ModelResearchProposal`
- `SourceCandidate`
- `ReviewerQuestion`
- `AuditTrailEntry`

Forbidden output/action:

- direct source verification
- direct repository write
- direct canonical knowledge update
- browser action
- download action
- shell command
- model-to-repo action chain

Required human checkpoint:

- human reviewer checks source identity, provenance, license or access constraints, and domain fit before any manual capture or candidate record is created.

## Hat Consistency Bot

Status: planned role only, not implemented.

Useful task:

- compare candidate text against Hat domain rules
- flag duplicate-like or contradiction-like material
- ask reviewer questions about unclear domain ownership

Allowed output:

- `ContradictionReport`
- `GapReport`
- `HatUpdateProposal`
- `ReviewerQuestion`
- `SafetyReview`

Forbidden output/action:

- automatic merge
- automatic canonical promotion
- direct edit to Hat 001, Hat 002, or Hat 003 records
- runtime mutation
- shell execution
- commit or push

Required human checkpoint:

- human reviewer confirms whether a gap, duplicate, contradiction, or domain conflict is real before any manual follow-up.

## Backlog Polish Bot

Status: planned role only, not implemented.

Useful task:

- improve wording of existing draft proposals
- identify incomplete review fields
- organize reviewer questions

Allowed output:

- `HatUpdateProposal`
- `ReviewerQuestion`
- `AuditTrailEntry`
- `SafetyReview`

Forbidden output/action:

- rewrite canonical records directly
- approve its own wording
- modify repository files
- stage or commit changes
- turn a draft into canonical knowledge
- execute formatting tools

Required human checkpoint:

- human reviewer accepts or rejects wording changes before any manual edit.

## Safety Critic Bot

Status: planned role only, not implemented.

Useful task:

- identify unsafe autonomy claims
- flag missing human-review boundaries
- find overbroad source trust language
- check proposed workflow text against no-execution policy

Allowed output:

- `SafetyReview`
- `ContradictionReport`
- `ReviewerQuestion`
- `AuditTrailEntry`

Forbidden output/action:

- enforce policy by modifying files directly
- block or approve commits automatically
- call runtime gates
- run shell commands
- launch browsers
- alter schemas or tests

Required human checkpoint:

- human reviewer decides whether a safety concern requires revision, quarantine, rejection, or separate work.

## Team Simulation Bot

Status: planned role only, not implemented.

Useful task:

- simulate reviewer objections
- produce alternative interpretations for policy review
- identify missing checks before manual action

Allowed output:

- `ReviewerQuestion`
- `ReviewerDecision`
- `GapReport`
- `SafetyReview`
- `AuditTrailEntry`

Forbidden output/action:

- act as a real approval authority
- replace human review
- modify repository state
- commit or push
- mutate runtime behavior
- promote canonical knowledge

Required human checkpoint:

- human reviewer treats simulated feedback as untrusted advisory material and records the actual decision separately.
