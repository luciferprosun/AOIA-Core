# NiFe Tag Status Vocabulary

## Purpose

This document defines the future status vocabulary for NiFe knowledge tags.

- It is docs-only planning.
- It is not implemented in AOIA-Core runtime.
- It does not grant execution authority.

A tag can suggest retrieval, but it cannot authorize execution or bypass AOIA safety gates.

## Status table

| Status | Short meaning |
| --- | --- |
| `planned` | Concept exists but has no attached reference material yet |
| `reference_only` | Tag points to reference material that is not yet validated |
| `model_generated_unverified` | Tag points to model-produced material that has not been validated |
| `reviewed` | Human review occurred, but validation is still incomplete |
| `validated_by_tests` | Supporting behavior or examples were validated by tests |
| `validated_by_commit` | Validation is tied to a concrete reviewed commit |
| `contradicted` | Evidence conflicts with the current claim |
| `deprecated` | Tag or claim should no longer be promoted |
| `promoted` | Tag is mature enough for trusted future knowledge routing |

## Meaning of each status

`planned`

- The concept exists as a placeholder.
- No active evidence bundle is attached yet.

`reference_only`

- The tag may point to notes, links, or draft docs.
- The material is useful for orientation, not validation.

`model_generated_unverified`

- The referenced material came from model output.
- It remains untrusted until reviewed against sources or tests.

`reviewed`

- A human inspected the material.
- Review alone is not equivalent to proof.

`validated_by_tests`

- Tests or equivalent deterministic checks support the claim.
- Validation is still scoped to the tested boundary.

`validated_by_commit`

- A reviewed commit anchors the validated material in project history.
- This status ties the tag to a concrete checkpoint.

`contradicted`

- New evidence or tests conflict with the claim.
- Promotion must stop until the contradiction is resolved.

`deprecated`

- The tag, mapping, or claim is no longer preferred.
- A replacement or narrower interpretation may be needed.

`promoted`

- The tag has enough validated support for future trusted routing concepts.
- Promotion still does not imply execution authority.

## Allowed promotion path

```text
planned
-> reference_only
-> reviewed
-> validated_by_tests
-> validated_by_commit
-> promoted
```

## Side paths: contradicted/deprecated

Two side paths can interrupt or replace the main promotion flow:

- `contradicted`
- `deprecated`

Either side path should block promotion until the tag map is corrected, narrowed, or replaced.

## Why model output is not validated knowledge

Model output can be useful for drafts, summaries, and candidate mappings, but it is not validated knowledge by default.

- It may hallucinate.
- It may blur evidence and inference.
- It may omit contradiction context.
- It may overstate certainty.

Because of that, model output starts at `model_generated_unverified` or `reference_only`, not at a validated status.

## Why public LLM chats are not validated knowledge by default

Public LLM chats are deferred as active knowledge inputs until a future source registry and validation workflow exist.

- They may be useful as references.
- They are not evidence by default.
- They must not be treated as validated knowledge without review, source comparison, and contradiction handling.

## How a tag can move from reference_only to validated_by_tests

Typical future path:

1. A tag begins as `reference_only` with attached source notes, docs, or draft mappings.
2. A human review narrows the claim and checks whether it is testable.
3. Deterministic tests, reproducible examples, or equivalent controlled checks are added.
4. If the tests support the scoped claim, the tag can advance to `validated_by_tests`.

## How a tag can move from validated_by_tests to validated_by_commit

Typical future path:

1. The tested material is committed in a reviewed project checkpoint.
2. The tag is linked to the exact commit and relevant supporting docs.
3. The evidence bundle records what was tested and what was not.
4. The tag can then advance to `validated_by_commit`.

## How contradiction handling should work

Contradiction handling must remain explicit.

- Conflicting evidence should move the tag to `contradicted`.
- Promotion should pause immediately.
- The narrower claim should be restated before further promotion.
- If the concept is obsolete or misleading, it should move to `deprecated`.

## Non-goals

This document does not implement:

- runtime resolver behavior
- automatic promotion logic
- retrieval systems
- server storage
- API integration
- execution control
- model-ranking code
