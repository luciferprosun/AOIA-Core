# CommandProposal Schema v0.1

## Purpose

`CommandProposal` is an inert data structure for representing a proposed shell command in a form that can later be reviewed, logged, and used in approval-gate tests.

It exists to support a pre-execution command classifier and an auditable AI-agent action boundary. It does not perform execution.

## Fields

- `command`: proposed command string.
- `risk_level`: one of `SAFE`, `AMBIGUOUS`, `DANGEROUS`, or `UNKNOWN`.
- `reason`: human-readable explanation of the current classification or review state.
- `requires_human_approval`: explicit approval flag.
- `source`: where the proposal came from, such as a model output channel or test fixture.
- `created_by`: the component or process that created the proposal record.
- `metadata`: extra inert structured fields for future review or logging context.
- `proposal_id`: stable identifier for the proposal record.

## Risk Levels

- `SAFE`: low-risk label within the current classifier boundary.
- `AMBIGUOUS`: requires explicit review because the command meaning or impact is not clear enough.
- `DANGEROUS`: indicates clearly high-risk command content.
- `UNKNOWN`: default or unresolved risk state.

## What It Does Not Do

- It does not execute shell commands.
- It does not approve shell commands.
- It does not dispatch commands to any runtime executor.
- It does not write to the event ledger.
- It does not replace review, containment, or OS-level controls.

## Non-Execution Boundary

This schema is inert. It is a representation-only object and is intentionally separated from shell execution, shell helpers, runtime executors, and provider logic.

## Future Use

The intended next use is in approval-gate control-flow tests and documentation-facing review paths.

## Relation to GT-RUNTIME-7A

GT-RUNTIME-7A established the reviewer honesty pack, threat model, and conservative claim boundary. `CommandProposal` continues that path by adding a schema-only review object without introducing shell execution.

## Current Boundary

This is not a shell executor and not an approval system yet.
