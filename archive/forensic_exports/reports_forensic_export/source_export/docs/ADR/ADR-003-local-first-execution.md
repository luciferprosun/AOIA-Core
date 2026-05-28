# ADR-003: Local-First Execution

## Context

AOIA is intended to support reliable operation with minimal external dependency.

## Decision

AOIA must prefer local configuration, local validation, and local knowledge
before any external path is considered.

## Consequences

External providers and network-dependent behavior must remain outside the core
router unless a later phase explicitly defines their boundary.
