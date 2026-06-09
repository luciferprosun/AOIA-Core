# Chat4/H4 Post-M1 Helper-Bot Production Plan

Date: 2026-06-09

## Status

DOCS-ONLY / TRANSITION PLAN / NO RUNTIME CHANGE

## 1. Executive Summary

M1 Controlled Model Router is closed as a stable checkpoint.

The next production direction is Chat4/H4 helper-bot governance, not immediate bot execution.

Helper bots must begin as proposal generators only. Model output is untrusted. Human approval remains required. No bot may write, commit, execute, browse, fetch, promote, or modify canonical knowledge without explicit later governance, tests, and checkpoint review.

This transition plan does not authorize autonomous agents, bot execution, provider calls, browser automation, shell execution, or canonical Hat promotion.

## 2. Why Not Code Bots Immediately

Helper bots are useful, but they are risky if introduced before governance boundaries are explicit.

Immediate bot implementation could cause:

- hallucinated knowledge entering Hats
- source and provenance drift
- unsafe browser or web ingestion
- hidden provider/API calls
- unwanted repository edits
- accidental canonical promotion
- confusion between proposal output and verified knowledge

The first helper-bot production work should therefore define what bots may propose, what they may never do, how humans review proposals, and how outputs remain quarantined until accepted.

## 3. Safe Next Sequence

Recommended sequence:

1. H4-A / Chat4-A docs-only helper-bot governance policy.
2. H4-B browser/output quarantine policy.
3. C4-B inert proposal schemas.
4. Tests proving proposals cannot execute, browse, commit, or promote.
5. Only then, minimal helper-bot workflow prototypes.

Each step should remain separately reviewable. Runtime behavior should not change until governance, inert schemas, and negative boundary tests are already in place.

## 4. Helper-Bot Roles As Future-only

The following roles are future-only and proposal-only.

### Source Discovery Bot

Potential future role: suggest source candidates for human review.

Output status: `DRAFT / NOT_CANONICAL / HUMAN_REVIEW_REQUIRED`.

### Hat Consistency Bot

Potential future role: detect contradictions, duplicates, or inconsistent Hat statements.

Output status: `DRAFT / NOT_CANONICAL / HUMAN_REVIEW_REQUIRED`.

### Safety Critic Bot

Potential future role: critique proposed changes for safety, boundary, provenance, or execution risk.

Output status: `DRAFT / NOT_CANONICAL / HUMAN_REVIEW_REQUIRED`.

### Backlog Polish Bot

Potential future role: propose clearer backlog wording, task ordering, or review checklists.

Output status: `DRAFT / NOT_CANONICAL / HUMAN_REVIEW_REQUIRED`.

### Reviewer Simulation Bot

Potential future role: simulate reviewer questions or identify weak claims.

Output status: `DRAFT / NOT_CANONICAL / HUMAN_REVIEW_REQUIRED`.

### Documentation Assistant Bot

Potential future role: draft documentation changes for human review.

Output status: `DRAFT / NOT_CANONICAL / HUMAN_REVIEW_REQUIRED`.

## 5. Hard Boundary

This transition does not add:

- autonomous agents
- bot swarm execution
- browser automation
- shell execution
- provider/API/model calls
- filesystem-writing bots
- Git commit bots
- canonical Hat promotion
- automatic source trust
- automatic fallback

No helper-bot output should be treated as verified knowledge, execution authority, or canonical memory.

## 6. Relationship To M1 Router

M1 provides a controlled model selection/proposal foundation.

M1 does not authorize helper bots to act.

Model routing remains separate from bot execution. Provider output remains untrusted and non-canonical. A selected model or approved provider invocation does not grant permission to write files, browse, execute commands, commit changes, or promote knowledge.

Helper-bot governance must preserve the M1 boundary: model output may propose, but humans decide.

## 7. Recommended Next Prompt

Recommended next step:

```text
CHAT4-H4-A: Helper-Bot Governance Policy — docs only
```
