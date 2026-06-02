# Approval Gate Control Flow v0.1

## Purpose

GT-RUNTIME-7C adds a mocked control-flow test that models a human-approved execution boundary for `CommandProposal` records.

The goal is narrow: prove that proposals marked as requiring human approval are stopped before any mock action sink is called.

## What GT-RUNTIME-7C Proves

- `CommandProposal` can be used in a test-only approval-gate flow.
- A `SAFE` proposal with `requires_human_approval=False` may continue through a mocked path.
- `DANGEROUS`, `AMBIGUOUS`, and `UNKNOWN` proposals with `requires_human_approval=True` are blocked before the mocked path is called.
- The approval flag itself is enough to stop the mocked path regardless of risk label.

## What GT-RUNTIME-7C Does Not Prove

- It does not prove a production approval system exists.
- It does not prove a runtime shell gate exists.
- It does not prove a real execution layer is safe.
- It does not prove complete protection against unsafe command suggestions.

## Relation to CommandProposal

`CommandProposal` is the inert schema introduced in GT-RUNTIME-7B. GT-RUNTIME-7C uses that schema as input data only.

## Relation to the GT-RUNTIME-7A Threat Model

GT-RUNTIME-7A established the claim boundary that proposed shell commands are untrusted until classified and reviewed. GT-RUNTIME-7C stays inside that boundary by testing only mocked control flow and by keeping the human-approved execution boundary explicit.

## Human-Approved Execution Boundary

The intended boundary is:

1. proposed command is represented as a `CommandProposal`
2. risk and approval requirement are inspected
3. if human approval is required, the proposal is blocked from the mocked path
4. no execution path is entered

## No Shell Execution Boundary

GT-RUNTIME-7C does not implement a production approval system.

GT-RUNTIME-7C does not execute shell commands.

GT-RUNTIME-7C only tests mocked control flow.

## Future Work Before Any Real Execution Is Considered

- approval-gate runtime integration design
- ledger integration design
- inert adversarial approval-path fixtures
- explicit reviewer decision recording
- execution-path design review after non-executing layers are audited
