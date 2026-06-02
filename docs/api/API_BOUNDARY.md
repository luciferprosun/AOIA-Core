# AOIA-Core API Boundary

## Current status

GT-RUNTIME-8B is a documentation-only planning milestone.

AOIA-Core does not execute shell commands in GT-RUNTIME-8B.

This document defines a boundary, not an implementation.

## What the API boundary is

The AOIA-Core API boundary is the future interface line between:

- model or user-originated command-like text
- inert proposal representation
- classification and review logic
- audit/provenance recording
- any later, explicitly gated execution layer

At this boundary, any future shell command must first be represented as an inert proposal.

Classification, review, and audit must happen before execution.

The boundary is intended to preserve local-first auditability, human review, and explicit control over any future action pathway.

## What the API boundary is not

The API boundary is not:

- a shell executor
- a terminal agent
- an autonomous command runner
- a production approval system
- a sandbox
- a replacement for OS-level containment
- a claim that AOIA-Core is shell-safe

## Allowed future inputs

Allowed future inputs at the boundary may include:

- proposed command strings
- normalized command representations
- `CommandProposal`-like inert objects
- source metadata describing where a proposal came from
- dry-run intent markers
- audit correlation identifiers
- human review decisions recorded separately from execution

These inputs are planning concepts only for GT-RUNTIME-8B.

## Forbidden direct actions

The future API boundary must never directly:

- execute shell commands
- dispatch to `shell_tools.py`
- dispatch to `executor.py`
- write approval as an execution side effect
- bypass classification
- bypass audit logging expectations
- treat model output as trusted executable intent

Any future execution path must remain outside this planning milestone and behind later explicit approval gates.

## Human approval requirement

Human approval is a hard boundary for risky or ambiguous commands.

At minimum, future `ambiguous`, `dangerous`, and `unknown` proposals must not cross from proposal state into any execution path without explicit human review.

Approval must remain separate from execution.

Approval must not imply automatic execution.

## Dry-run and CommandProposal relationship

`CommandProposal` is the current inert representation boundary for proposed shell commands.

Future dry-run behavior should treat proposed commands as reviewable records, not executable actions.

The intended sequence is:

1. proposal text arrives at the boundary
2. proposal is represented as an inert `CommandProposal`-style object
3. classification determines risk and review state
4. audit records capture the proposal path
5. execution remains blocked unless a later explicit phase permits more

GT-RUNTIME-8B does not implement this sequence in code. It documents the intended boundary only.

## Audit/provenance expectations

Future API boundary design should preserve:

- stable proposal identifiers
- source attribution
- classification reason fields
- approval-state visibility
- provenance context for later review
- audit events that do not imply execution

The audit boundary must support traceability without becoming an execution engine.

## Non-goals for GT-RUNTIME-8B

GT-RUNTIME-8B does not:

- implement shell execution
- implement a real API server
- integrate with providers
- integrate with routing
- modify `shell_tools.py`
- modify `executor.py`
- modify `event_ledger.py`
- add OS-level containment
- claim production shell safety

## Reviewer summary

AOIA-Core does not execute shell commands in GT-RUNTIME-8B.

Any future shell command must first be represented as an inert proposal.

Classification, review, and audit must happen before execution.

Human approval is a hard boundary for risky or ambiguous commands.

This document defines a boundary, not an implementation.
