# Python Master Library Consolidated External Review Plan

## Purpose

This plan consolidates the Kimi and DeepSeek external reviews into a safe implementation direction for the Python Master Library in AIOA Whitehat. Both reviews are treated as `external_model_review_unverified`: useful planning input, not canonical truth.

## Accepted Principles

- Python is the correct first programming-language library for AIOA Whitehat.
- Imported PDFs are unverified references only.
- External model reviews are advisory only.
- Schema and tests come before corpus expansion.
- Dangerous APIs must be classified early.
- Runtime integration is forbidden until a future explicit gate.
- No examples are executed during validation.
- Model output is not canonical.

## Kimi Contributions Accepted

- broad taxonomy for Python knowledge domains
- curriculum levels from glossary/safe basics through delayed advanced topics
- dangerous APIs list
- Python + Linux/RHCSA bridge principles
- first 25 candidate record topics for later draft work
- integration gate idea
- repository layout suggestions

## DeepSeek Contributions Accepted

- strict schema hardening
- enum validation
- dangerous pattern tests
- no premature promotion
- no runtime integration
- no corpus expansion before schema stability
- high/critical risk classification
- `never_execute` policy for dangerous items

## Resolved Combined Direction

1. Source registry and deduplication.
2. Schema/enums hardening.
3. Dangerous API index.
4. Validation tests.
5. Official docs cross-check plan.
6. Only then first draft advisory records.
7. Runtime integration postponed.

## Not Accepted Yet

- no 100-record threshold as binding requirement yet
- no runtime feature flag implementation yet
- no promoted records
- no execution_policy that allows execution
- no large corpus generation
- no runtime connection

## Immediate Next Safe Task

Recommended next task:

H18 — Python Master Library Official Docs Cross-Check Plan

H18 should create:
- official docs cross-check checklist
- discrepancy log template
- source verification workflow
- source status lifecycle
- no web scraping
- no copied official docs
- only references, links, and checklists

## Boundary

This consolidated plan does not promote any record, validate any PDF claim as true, or connect the Python library to runtime. It is a planning document only.
