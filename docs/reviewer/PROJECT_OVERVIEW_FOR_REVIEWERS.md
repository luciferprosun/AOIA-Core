# AOIA-Core Project Overview for Reviewers

AOIA-Core is a local-first, non-executing inspection and audit layer for
AI-proposed shell commands. Its current reviewer purpose is to make boundaries
explicit between proposed commands, dry-run inspection results, approval/audit
metadata, provenance context, and evidence-like records.

## What AOIA-Core Is

AOIA-Core is a local-first inspection and audit layer with explicit evidence,
provenance, and model-output boundaries. It is designed to separate:

- model output from evidence
- operational logs from canonical state
- provenance trails from raw tool output
- proposed actions from automatic execution

The project aims to keep AI-assisted shell-command review auditable without
treating every runtime artifact as authoritative.

Deterministic/local-first behavior means deterministic rule-based inspection
where implemented. External LLM providers are historical or optional context and
are not treated as deterministic runtime results.

## What AOIA-Core Is Not

AOIA-Core is not:

- an AGI system
- an autonomous system
- a truth engine
- validated science
- a production-ready deployment
- a generic chatbot or agent
- a model output validation engine
- a shell executor
- a sandbox

It is not intended to make model consensus equivalent to evidence. It is not a mechanism for automatic contradiction resolution or production-grade governance enforcement.

## What Is Implemented Now

Implemented capabilities include:

- inert Bash command parsing and classification tests
- dry-run shell safety inspection for proposed commands
- approval/audit metadata around proposed command decisions
- evidence write boundary documentation and control concepts
- append-only provenance and provenance record tracking
- contradiction tracking and registry ideas
- external model output policy as historical/reviewer context
- core documentation and reviewer-focused status materials

These are implemented at the documentation and inspection-layer level. Some
capabilities are present in the current codebase, while others are partial or
under active governance refinement.

## Boundary Clarifications

- `AOIAEpistemicKernel` is the canonical epistemic gate. `KnowledgeRouter` is a legacy/compatibility transition surface, not a second canonical authority.
- Provenance records and verifies local lineage/integrity for selected artifacts; it does not validate truth, scientific claims, external source authenticity, or model output.
- The evidence boundary is a controlled write path and audit-support mechanism, not a complete immutable content-addressed evidence store.
- Runtime safety contracts are strong design/governance contracts with partial runtime enforcement today; execution containment is out of current public scope.
- xAI/Grok and the model selector are historical or optional convenience/demo features. They do not change runtime authority, evidence/provenance boundaries, or command-inspection determinism.
- Web and TUI surfaces are legacy/transitional visualization, debug, and operator interfaces. Generated `state/`, `memory/`, `logs/`, and `obsidian_vault/` artifacts are not canonical source authority.
- Historical entrypoints such as `runtime/main.py`, `runtime/run.sh`, `runtime/run_web.sh`, and `scripts/start_tui.sh` are not the current NLnet second-review claim.

## What Is Planned / Inactive

Planned or inactive work includes:

- Evidence Memory Phase 1A approval and formal activation, pending ADR/operator decision
- full determinism certification and replay verification beyond syntax-level validation
- broader production hardening and deployment
- stress-test execution workflows (stress-test documentation exists, but execution is not part of this patch)
- any new external model evaluation or evidence promotion without explicit authority
- any shell execution, sandboxed execution, browser hardening, or autonomous agent loop

## What Is Out of Scope

Out of scope for this deliverable:

- stress-test execution results
- LSC/MHLM/MDLH/DVM theory as runtime authority
- external provider trustworthiness or model correctness claims
- production readiness guarantees
- TUI Phase 3 implementation and final GUI delivery
- autonomous or self-modifying runtime behavior
- shell execution or sandboxed execution
- provider-routing feature expansion

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
