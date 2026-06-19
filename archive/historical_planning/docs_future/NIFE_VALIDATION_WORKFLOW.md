# NiFe Validation Workflow

## Status

This is docs-only future planning.

- This workflow is not implemented in runtime yet.
- This workflow does not authorize execution.
- No tag resolver, server storage, retrieval system, API endpoint, or model-ranking implementation exists yet.

## Purpose

The NiFe validation workflow defines how a symbolic tag may move from a draft concept toward a promoted future knowledge entry.

Validation exists to keep tags tied to scoped evidence rather than treating tags as proof by themselves.

## Validation philosophy

Validation does not mean universal truth; it means validated for a specific scope.

Every promoted tag should have:

- clear claim scope
- explicit limitations
- source or test evidence
- contradiction handling
- a reproducible repository state when commit-backed

Model output is not validated knowledge by default. Public LLM conversations are not validated knowledge by default.

## Promotion path

Required promotion path:

```text
planned
→ reference_only
→ reviewed
→ validated_by_tests
→ validated_by_commit
→ promoted
```

A tag starts as `planned` or `reference_only`.

## Source review workflow

Source review should check:

- what claim the source supports
- whether the source is primary, secondary, model-generated, or project-local
- whether the source is current enough for the claim
- whether the source conflicts with other evidence
- whether the source is sufficient for the requested status

Review can move a tag from `reference_only` to `reviewed`, but review alone is not enough for `validated_by_tests` or `validated_by_commit`.

## Test validation workflow

A tag can only become `validated_by_tests` if there is a reproducible test or test report.

The test evidence should identify:

- exact behavior tested
- command or input examples, if relevant
- expected result
- test command or report path
- limitations of the test

Dangerous admin or shell-command examples must pass Bash Safety inspection where applicable and still require human review.

## Commit validation workflow

A tag can only become `validated_by_commit` if linked to a commit or reproducible repository state.

Commit validation should include:

- commit hash or immutable repository reference
- files changed
- validation command or report
- claim scope
- known limitations

Commit validation must not imply broader truth than the committed evidence supports.

## Contradiction workflow

Required side path:

- `contradicted`

When a contradiction appears:

- mark the affected tag or source as `contradicted`
- stop promotion
- document the conflicting evidence
- narrow, split, or revise the claim
- restore promotion only after the contradiction is resolved by review and evidence

Contradiction notes should remain visible in the source registry.

## Deprecation workflow

Required side path:

- `deprecated`

A tag or source can become `deprecated` when:

- the claim is obsolete
- the tag mapping is misleading
- better source evidence replaces it
- the scope can no longer be defended

Deprecation should include a reason and, when possible, a replacement tag or narrower claim.

## Public LLM conversation workflow

A public LLM conversation starts as `model_generated_unverified` or `reference_only`.

Public LLM conversation links:

- may be useful as low-cost references
- must not be treated as validated knowledge by default
- must not be promoted without source comparison, review, and validation
- must not become active knowledge until a future source registry and validation workflow exist

## Hat tag promotion workflow

Hat tag promotion should move one tag at a time.

Before promotion, each tag needs:

- clear scope
- source record links
- validation status
- contradiction review
- limitations

A promoted tag must have clear scope, limitations, and contradiction handling.

## Model verification preparation

This workflow can later prepare evidence for IOA / LLM model verification.

Future model verification may inspect:

- source discipline
- uncertainty handling
- contradiction handling
- safety-boundary compliance
- ability to separate validated knowledge from model-generated suggestions

No model verification or ranking implementation exists yet.

## Non-goals

This document does not implement:

- runtime validation logic
- automatic promotion
- tag resolver behavior
- server storage
- knowledge retrieval
- API endpoints
- model-ranking code
- execution authority
- public LLM conversation ingestion as active knowledge

## Future implementation notes

A future implementation should be designed only after the docs-level source registry and workflow are reviewed.

Any future implementation would need:

- structured schemas
- deterministic tests
- contradiction records
- audit reports
- security review
- explicit no-execution boundary checks

## Short example

Example tag:

```text
mV:-70.000010 execution_permitted=False hard lock
```

Example promotion:

```text
planned → reviewed → validated_by_tests → validated_by_commit → promoted
```

The promoted scope would be limited to the AOIA-Core approval boundary validated by its tests and commit history. It would not authorize execution and would not make broader claims about all command approval systems.
