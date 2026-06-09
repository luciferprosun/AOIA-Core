# AOIA-Core Current State

Status: Research prototype / safety-core in progress

Audience: reviewers, contributors, security reviewers

Last updated: 2026-06-09

Branch: dev/gt-runtime-8-bash-safety-planning

AOIA-Core is not currently a production autonomous-agent runtime. It is a local-first research prototype for pre-execution inspection, proposal review, and audit-oriented safety controls for AI-assisted workflows.

## 1. What AOIA-Core Is

AOIA-Core is a local-first research prototype and safety-core in progress.

It currently focuses on:

- pre-execution inspection
- proposal review
- audit-oriented safety controls
- human approval boundaries
- provenance and evidence-boundary documentation
- controlled model selection/proposal work

The current work is incremental and checkpoint-driven.

## 2. What AOIA-Core Is Not

AOIA-Core is not:

- an autonomous agent runtime
- helper-bot production
- browser automation
- a shell execution product
- a finished security system
- a trusted model-output system
- an automatic source-trust system
- an automatic canonical knowledge promotion system

Reviewer claims should be read narrowly and checked against the current docs, tests, and blocker register.

## 3. What Is Currently Enforced

Current enforced boundaries include:

- local validation through the repository test suite
- non-execution claims for the current reviewer-facing safety-core scope
- model-router proposal and approval separation
- provider output remaining untrusted in the controlled router path
- no automatic fallback in the controlled router checkpoint
- explicit distinction between legacy runtime surfaces and current reviewer claims

These boundaries do not remove all legacy risk surfaces from the repository.

## 4. What Is Test-Enforced

Current tests cover:

- controlled model router boundary checks
- provider-call gating behavior in the M1 router path
- OpenRouter Free / generic free route rejection for sensitive, canonical, and secret-adjacent tasks
- provider output remaining untrusted and non-canonical in tested paths
- shell safety parser and approval-gate behavior
- memory-hats and provenance-related invariants in their current scoped tests

The current expected suite count is 618 tests with 4 skipped at this checkpoint.

Recent RED-1 cleanup checkpoint:

- RED-1-C through RED-1-I added diagnostic negative tests and three narrow runtime hardening changes.
- RED-1-G removed the `KnowledgeRouter` import-time `token_savings_report.json` write from the `runtime.webapp` path.
- RED-1-H hardened `runtime/main.py` browser approval exposure and removed the legacy "Autonomous local runtime" wording.
- RED-1-I hardened the model-router approval provenance boundary for untrusted proposal/decision payloads.
- Current checkpoint: 618 tests OK, 4 skipped; GitHub Actions green; HEAD `0e258c01204644fb7b0401aa25547bcbfec5f888`.
- This does not close RED-1 globally. Legacy runtime and public entrypoint surfaces remain open for framework cleanup.

## 5. What Is Documentation-Only Or Future-Planned

The following remain documentation-only or future-planned unless separately implemented, tested, and reviewed:

- helper-bot governance and workflows
- browser/output quarantine policy
- expanded negative tests for helper-bot boundaries
- execution surface mapping
- complete provider/network gate coverage proof
- canonical promotion hardening
- source-provenance checks for future helper-bot workflows

Documentation should not be read as runtime authority.

## 6. RED-1 Known Blockers

RED-1 blockers remain OPEN.

See `docs/audit/RED_1_BLOCKER_REGISTER.md`.

The blocker register records known surfaces that must be mapped and tested before helper-bot production work:

- legacy browser paths
- legacy executor and shell surfaces
- browser and web-reader surfaces
- provider and network call surfaces
- file-write, delete, Git, and canonical-promotion surfaces
- missing negative tests for helper-bot proposal boundaries

No blocker is claimed as fixed by this document.

## 7. Reviewer Quick Path

Recommended review order:

1. `README.md`
2. `CURRENT_STATE.md`
3. `docs/audit/RED_1_BLOCKER_REGISTER.md`
4. `docs/REVIEWER_QUICKSTART.md`
5. `tests/`

Use the tests and blocker register to challenge current claims.

## 8. Safe Next Engineering Steps

Safe next steps:

1. Keep RED-1 blockers visible and OPEN until mapped and tested.
2. Add diagnostic negative tests for helper-bot proposals.
3. Map legacy execution, browser, provider, file-write, Git, and canonical-promotion surfaces.
4. Add explicit guard documentation before any helper-bot workflow prototype.
5. Treat future helper-bot output as draft, non-canonical, and human-review-required.
