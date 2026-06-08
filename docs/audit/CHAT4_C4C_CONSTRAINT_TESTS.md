# Chat4 C4-C Constraint Tests

Date: 2026-06-08

Phase: C4-C proposal safety constraint tests.

## Purpose

C4-C adds tests only.

C4-C proves that C4-B helper-model proposal objects cannot write, commit, execute, call browser/runtime tools, or promote canonical knowledge.

## Relationship To C4-B

C4-B added inert helper-model proposal schemas.

C4-C adds negative-path tests around those schemas. It does not change the schemas and does not add runtime behavior.

## What C4-C Tests Prove

C4-C tests that helper-model proposal objects remain `DRAFT`, `NOT_CANONICAL`, `UNVERIFIED`, human-reviewed, non-executing, and non-committing by default.

C4-C tests:

- proposal objects do not permit execution or automatic commits
- reviewer decisions cannot authorize promotion, execution, or commits
- source provenance is mandatory for Hat knowledge candidates
- broad documentation rewrites cannot be auto-approved
- browser-visible text remains unverified source candidate material
- Hat domain separation is explicit in valid candidates
- C4-B objects expose no execution-like methods
- the C4-B schema module contains no forbidden implementation imports or method definitions
- audit trail entries remain local-only and not compliance-grade
- model output cannot become canonical through C4-B objects

## What C4-C Does Not Implement

C4-C does not implement helper bots.

C4-C does not call Gemini, APIs, or models.

C4-C does not launch a browser.

C4-C does not execute shell commands.

C4-C does not create a repo-write workflow.

C4-C does not create a commit workflow.

C4-C does not promote canonical knowledge.

C4-C does not modify runtime behavior, providers, tools, approval gates, event ledgers, knowledge records, packages, CI, scripts, or application files.

## Required Boundaries

C4-C is test-only.

Allowed files:

- `tests/hat004/test_chat4_agentic_constraints.py`
- `docs/audit/CHAT4_C4C_CONSTRAINT_TESTS.md`

No schema edits are part of C4-C unless a separate stop-and-report decision is made.

## Validation Commands

Expected validation:

```text
python3 -m compileall -q tests/hat004/test_chat4_agentic_constraints.py
PYTHONPATH=runtime:. PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.hat004.test_chat4_agentic_constraints -v
PYTHONPATH=runtime:. PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/hat004 -p "test*.py" -v
PYTHONPATH=runtime:. PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test*.py" -v
git diff --check
```

## Stop Conditions

C4-C work stops if it requires:

- editing files outside the allowed C4-C file set
- modifying the C4-B schema without prior report
- touching runtime behavior
- touching knowledge records
- adding browser, shell, provider, API, model, repo-write, commit, or promotion behavior
- installing packages
- committing or pushing

## Reviewer Summary

C4-C is a proof-of-constraint test phase.

It adds no implementation and exercises the existing C4-B proposal objects only as inert data. Its expected output is reviewer confidence that future helper-model proposal records cannot become execution, commit, browser, runtime, or canonical-promotion channels by default.
