# Mutable State Isolation Plan

Date: 2026-05-23
Phase: AOIA Runtime Stabilization

## Current Mutable State Surfaces

Observed repo-local runtime outputs:
- `state/`
- `memory/`
- `logs/`
- `screenshots/`
- `obsidian_vault/`

Observed producers:
- `runtime/tools/memory.py`
- `runtime/tools/executor.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/providers/config.py`
- browser bridge configuration through executor

## State Classification

### Runtime state

Definition:
- mutable machine-readable control state needed for active runtime continuity

Current examples:
- `state/agent_state.json`
- `state/model_config.json`
- `state/providers.json`
- `state/browser_profile/`

### Evidence state

Definition:
- captured artifacts used as local evidence or later audit inputs

Current examples:
- `memory/evidence_memory.jsonl`
- page text snapshots in `memory/`
- selected session-level evidence traces

### Operational logging

Definition:
- execution traces, command logs, browser logs, error logs, session logs

Current examples:
- `logs/browser/`
- `logs/commands/`
- `logs/errors/`
- `logs/sessions/`
- `memory/history.jsonl`

### User-facing vault material

Definition:
- human-readable persistent notes generated for inspection or continuity

Current examples:
- `obsidian_vault/`

### Screenshots

Definition:
- browser-capture artifacts that are runtime outputs, not canonical source

Current examples:
- `screenshots/`

## What Must Never Live Inside Canonical Repo Root

Recommended exclusions from canonical source authority:
- browser profiles
- screenshots
- session logs
- error logs
- command logs
- daily vault notes
- generated evidence traces
- interactive runtime state snapshots

Reason:
- these are execution byproducts, not source authority

## Isolation Principle

Recommended principle:
- canonical repo root should contain code, tests, docs, schemas, and committed knowledge artifacts
- mutable runtime outputs should live outside canonical source authority

## Planned Boundary Model

### Keep in repo authority

- committed registries
- committed knowledge corpus
- committed docs
- committed tests
- static prompt files
- source build scripts

### Move to external runtime data root in a later phase

- `state/`
- `memory/`
- `logs/`
- `screenshots/`
- `obsidian_vault/`

## Proposed Separation Model

Recommended future split:
- source authority under repo root
- mutable runtime data under external AOIA data root

Example target classes:
- runtime state root
- evidence root
- logs root
- vault root
- screenshots root

This phase does not execute that migration.

## Immediate Stabilization Recommendation

Before ontology work:
1. formally mark repo-local mutable directories as transitional
2. stop treating them as canonical architecture surfaces
3. define one future external state root
4. separate runtime continuity from source authority in architecture docs first

## Risk If Not Isolated

- repository contamination after normal usage
- blurred provenance between source and execution artifacts
- harder archive and backup semantics
- unstable git hygiene
- increased ambiguity during memory ontology design
