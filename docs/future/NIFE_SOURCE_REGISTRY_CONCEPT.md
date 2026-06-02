# NiFe Source Registry Concept

## Status

This is docs-only future planning.

- The source registry is future-only and not implemented in runtime.
- No server, resolver, API, or automatic ingestion exists yet.
- This document does not change AOIA-Core execution behavior.
- A source can support retrieval, but it cannot authorize execution.

## Purpose

The NiFe source registry concept defines how future AOIA knowledge hats may attach evidence, source status, trust level, contradiction notes, and validation history to symbolic tags.

The registry is intended to keep tags from becoming unsupported claims. Tags may point to future validated knowledge entries, but tags are not proof by themselves.

## Why source registry is required

NiFe tags are compact symbolic string identifiers. They do not carry full evidence by themselves.

A source registry is required so future systems can distinguish:

- draft notes from validated knowledge
- model-generated text from reviewed sources
- tested claims from untested references
- current evidence from contradicted or deprecated evidence
- commit-backed project facts from external claims

Without a source registry, tag lookup would risk treating labels as proof.

## Relationship to NiFe Synapses tags

NiFe Synapses tags can point to source records.

- Tags are symbolic string identifiers, not floats.
- Tags may refer to one or more source records.
- Source records describe the status, evidence, trust level, and limitations of the material behind a tag.
- Tags do not bypass evidence, provenance, contradiction, or safety rules.

## What counts as a source

A source is any record that supports, challenges, narrows, or documents a tag claim.

Sources can include repository commits, tests, reports, official documentation, external articles, public LLM conversations, model audits, human reviews, datasets, benchmark results, and contradiction notes.

## Source types

Required source types:

- `repo_commit`
- `test_result`
- `docs_report`
- `primary_documentation`
- `external_article`
- `public_llm_conversation`
- `model_audit`
- `human_review`
- `dataset`
- `benchmark_result`
- `contradiction_note`

## Source status values

Required source statuses:

- `reference_only`
- `model_generated_unverified`
- `reviewed`
- `validated_by_tests`
- `validated_by_commit`
- `contradicted`
- `deprecated`
- `promoted`

Status values must remain conservative. A public link, model output, or draft report does not become validated knowledge by existing in the registry.

## Trust levels

Required trust levels:

- `unverified`
- `low`
- `medium`
- `high`
- `canonical`

Trust level should describe how strongly the source supports a scoped claim. It must not imply universal truth or execution authority.

## Required source fields

Future source records should include:

- `source_id`
- `source_type`
- `status`
- `trust_level`
- `title`
- `uri_or_path`
- `related_tags`
- `claim_scope`
- `validation_method`
- `limitations`
- `contradictions`
- `reviewer`
- `created_at_utc`
- `updated_at_utc`

These fields are conceptual. No schema, API, server, or runtime object exists yet.

## Public LLM conversation links

Public LLM conversations are not validated knowledge by default.

- A public LLM conversation can begin as `model_generated_unverified` or `reference_only`.
- Model output must not be promoted without review or validation.
- Public LLM links must not become active knowledge until a future source registry and validation workflow exist.
- Public LLM conversations may provide context, but they do not provide proof by themselves.

## Commit/test/report links

Repository-backed sources can provide stronger evidence when their scope is clear.

Useful source links may include:

- commit hashes
- test reports
- docs reports
- closure reports
- validation summaries

Commit/test/report evidence should identify what was validated and what was not validated.

## Contradiction handling

Contradiction records are first-class sources.

- A contradiction should be linked to the affected tag.
- The affected tag should stop promotion until the contradiction is resolved.
- The claim may need to be narrowed, deprecated, or split into separate tags.
- Contradictions must remain visible instead of being overwritten by later summaries.

## Promotion and demotion

Source promotion should follow the NiFe status vocabulary.

Typical promotion direction:

```text
reference_only
-> reviewed
-> validated_by_tests
-> validated_by_commit
-> promoted
```

Demotion can happen when:

- new evidence contradicts the claim
- tests fail
- source scope was overstated
- the source is obsolete
- the source cannot be reproduced

## Non-goals

This document does not implement:

- runtime source registry code
- server storage
- resolver logic
- knowledge retrieval
- automatic ingestion
- API endpoints
- model-ranking code
- execution authority
- public LLM conversation ingestion as active knowledge

## Future implementation notes

A future source registry may become a structured document set, local database, or server-backed knowledge service. Any implementation would need separate design review, tests, security review, contradiction handling, and explicit runtime boundary review.

Future implementation must preserve the rule that a source can support retrieval but cannot authorize execution.

## Example JSON-like source records

GT-RUNTIME-8E commit/test source:

```json
{
  "source_id": "source:aoia:gt-runtime-8e:commit:8f8bde8",
  "source_type": "repo_commit",
  "status": "validated_by_commit",
  "trust_level": "high",
  "title": "GT-RUNTIME-8E approval gate hardening",
  "uri_or_path": "git:8f8bde8",
  "related_tags": ["mV:-70.000009", "mV:-70.000010", "mV:-70.000012", "mV:-70.000013"],
  "claim_scope": "ApprovalDecision and approval gate dry-run boundary in AOIA-Core GT-RUNTIME-8E",
  "validation_method": "pushed commit with associated tests and docs/api report",
  "limitations": "Valid only for the scoped AOIA-Core implementation at the referenced checkpoint",
  "contradictions": [],
  "reviewer": "future_registry_reviewer",
  "created_at_utc": "future-caller-supplied",
  "updated_at_utc": "future-caller-supplied"
}
```

Public LLM conversation as `reference_only`:

```json
{
  "source_id": "source:public-llm-conversation:example-reference-only",
  "source_type": "public_llm_conversation",
  "status": "reference_only",
  "trust_level": "unverified",
  "title": "Example public LLM conversation reference",
  "uri_or_path": "https://example.invalid/public-llm-conversation",
  "related_tags": ["mV:-71.000015"],
  "claim_scope": "Possible discussion context only; not validated knowledge",
  "validation_method": "none",
  "limitations": "Model output and public conversation links are not validated by default",
  "contradictions": [],
  "reviewer": "none",
  "created_at_utc": "future-caller-supplied",
  "updated_at_utc": "future-caller-supplied"
}
```

Contradiction note:

```json
{
  "source_id": "source:contradiction:example-admin-command-safety",
  "source_type": "contradiction_note",
  "status": "contradicted",
  "trust_level": "medium",
  "title": "Example contradiction for an overstated admin command safety claim",
  "uri_or_path": "docs/future/example-contradictions.md",
  "related_tags": ["mV:-71.000015"],
  "claim_scope": "A prior draft implied an admin command was broadly safe without context",
  "validation_method": "human review found missing privilege and environment constraints",
  "limitations": "Example record only; no runtime registry exists",
  "contradictions": ["original claim was too broad"],
  "reviewer": "future_registry_reviewer",
  "created_at_utc": "future-caller-supplied",
  "updated_at_utc": "future-caller-supplied"
}
```
