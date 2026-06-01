# Python Knowledge Library Schema

This schema defines the intended record format for AIOA Whitehat Python knowledge records.

## Trust Boundary

- All imported records start as `imported_unverified` or `candidate`.
- No record may be promoted without official Python documentation cross-check and human review.
- Dangerous examples are inert strings only.
- Tests must not execute examples.
- Runtime integration is forbidden until an explicit future integration gate.

## Required Fields

| field | purpose |
| --- | --- |
| `id` | Unique stable record identifier. |
| `title` | Human-readable record title. |
| `domain` | Top-level domain, currently `python` for schema-hardened records. |
| `subdomain` | Controlled subdomain such as `keywords`, `builtins`, `subprocess`, `filesystem`, or `serialization`. |
| `difficulty` | One of the allowed difficulty enum values. |
| `tags` | Small list of lowercase tags. |
| `python_version_scope` | Version scope such as `Python 3.10+`. |
| `unsafe_or_wrong_pattern` | Intentional unsafe or incorrect pattern, if applicable. |
| `corrected_pattern` | Safer or corrected reference pattern as inert text. |
| `explanation` | Explanation of behavior or correction. |
| `safety_notes` | Safety caveats and mitigation notes. |
| `verification_steps` | Human verification checklist or references. |
| `negative_tests` | Static negative-test descriptions. |
| `related_linux_rhcsa_links` | Links or labels for related Linux/RHCSA contexts. |
| `official_docs_refs` | Official documentation references; required before official-docs-checked or promoted states. |
| `evidence_refs` | Non-authoritative supporting references. |
| `review_status` | Lifecycle state for review. |
| `reviewer` | Reviewer identity or system marker. |
| `confidence_level` | Low/medium/high confidence marker. |
| `risk_level` | Low/medium/high/critical risk marker. |
| `execution_policy` | Execution boundary for examples and advice. |
| `promotion_status` | Promotion gate state. |
| `last_reviewed` | ISO date for last review. |
| `known_limitations` | Known caveats. |
| `source_ref` | Source reference identifier. |

## Review Lifecycle

Records may move through:

1. `imported_unverified`
2. `candidate`
3. `human_reviewed`
4. `official_docs_checked`
5. `promoted`

Rejected and deprecated records stay available only as audit/reference material. Promotion is forbidden without human review and official documentation cross-check.

## Execution Boundary

Knowledge records are data. They are not executable code. Examples and corrected patterns are inert strings. No test should call `eval`, `exec`, import, subprocess, or shell execution on record content.
