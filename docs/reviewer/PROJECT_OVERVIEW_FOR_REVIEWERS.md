# AOIA-Core Project Overview for Reviewers

AOIA-Core is a local-first runtime for AI-assisted engineering workflows. Its purpose is to make boundaries explicit between model outputs, provenance logs, operational memory, evidence-like records, and human-approved execution.

## What AOIA-Core Is

AOIA-Core is a local-first runtime for AI-assisted engineering workflows with explicit evidence, provenance, and model-output boundaries. It is designed to separate:

- model output from evidence
- operational logs from canonical state
- provenance trails from raw tool output
- human-approved actions from automatic execution

The project aims to keep AI-assisted engineering work auditable and reviewable without treating every runtime artifact as authoritative.

## What AOIA-Core Is Not

AOIA-Core is not:

- an AGI system
- an autonomous system
- a truth engine
- validated science
- a production-ready deployment
- a generic chatbot or agent
- a model output validation engine

It is not intended to make model consensus equivalent to evidence. It is not a mechanism for automatic contradiction resolution or production-grade governance enforcement.

## What Is Implemented Now

Implemented capabilities include:

- evidence write boundary documentation and control concepts
- append-only provenance and provenance record tracking
- contradiction tracking and registry ideas
- deterministic local retrieval and controlled provider switching
- human approval gates for risky actions
- external model output policy as historical/reviewer context
- core documentation and reviewer-focused status materials

These are implemented at the documentation and runtime-design level. Some capabilities are present in the current codebase, while others are partial or under active governance refinement.

## What Is Planned / Inactive

Planned or inactive work includes:

- Evidence Memory Phase 1A approval and formal activation, pending ADR/operator decision
- full determinism certification and replay verification beyond syntax-level validation
- broader production hardening and deployment
- stress-test execution workflows (stress-test documentation exists, but execution is not part of this patch)
- any new external model evaluation or evidence promotion without explicit authority

## What Is Out of Scope

Out of scope for this deliverable:

- stress-test execution results
- LSC/MHLM/MDLH/DVM theory as runtime authority
- external provider trustworthiness or model correctness claims
- production readiness guarantees
- TUI Phase 3 implementation and final GUI delivery
- autonomous or self-modifying runtime behavior

## How to Verify the Repo

Reviewers can verify the repository by checking:

- `README.md` for current reviewer guidance and scope statements
- `docs/reviewer/PROJECT_OVERVIEW_FOR_REVIEWERS.md` for reviewer context
- `docs/governance/IMPLEMENTED_CAPABILITIES.md` for conservative capability status
- `docs/reviewer/ONE_CONCRETE_EXAMPLE.md` for an example workflow and authority boundaries
- `docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md` for external model output policy
- `docs/stress_tests/README.md` for clarity on stress-test research context
- `LICENSE` for licensing status
- `MHLM_MHSR/README.md` for research background context if present

This repo should be read as a review-oriented engineering runtime, not as a validated AI product.

## License Note

AOIA-Core is released under the MIT License. See `LICENSE` for the full terms.

## Documentation Taxonomy

Reviewer-facing documents are collected under `docs/reviewer/`.

Governance and capability documents are collected under `docs/governance/`.

Stress-test and research-context documents are collected under `docs/stress_tests/`.

External model output, audit, and background research context are explicitly separated from the core runtime deliverable.
