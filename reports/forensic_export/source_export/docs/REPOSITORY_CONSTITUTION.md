# Repository Constitution

## Purpose

This repository contains the local terminal application used for controlled
AI-assisted shell, filesystem, browser, memory, and research workflows.

AOIA work must evolve this application gradually. The project should gain
adaptive behavior only through small, reviewable layers that preserve local
control and do not destabilize the existing terminal runtime.

## Current System Identity

- Project root: `/home/l/Desktop/app2terminl_opened`
- Primary CLI entrypoint: `run.sh`
- Web UI entrypoint: `run_web.sh`
- Runtime core: `main.py`
- Existing local knowledge path: `knowledge/`, `tools/rhcsa_search.py`
- Existing state path: `state/`
- Existing logs path: `logs/`
- AOIA foundation path: `adaptive_routing/`

## Non-Negotiable Rules

- Do not redesign the whole application in one step.
- Do not add autonomous behavior without explicit approval.
- Do not connect new routing layers to providers until the local model is
  documented, tested, and reviewed.
- Do not move existing runtime modules unless a migration plan exists.
- Do not store secrets in repository files.
- Do not publish local partner notes, private contacts, tokens, browser state,
  or mailbox data.
- Keep AOIA additions modular and reversible.

## Evolution Model

The application evolves in staged layers:

1. Document the concept.
2. Add a small isolated local module.
3. Add tests or manual validation.
4. Create a checkpoint.
5. Integrate only after explicit approval.

This keeps the system stable while allowing long-term growth.

## AOIA Direction

AOIA means Adaptive Oceanic Intelligence Architecture. In this repository it is
an architecture metaphor and routing discipline inspired by biological systems,
especially Diel Vertical Migration.

AOIA is not AGI, not an autonomous ecosystem, and not a distributed compute
system at this stage.

## Public vs Private Boundary

Public-safe:
- architecture documents
- routing mode definitions
- static local profiles
- tests
- high-level research notes

Private/local-only:
- API keys
- Gmail tokens
- partner identity notes
- browser profiles
- logs containing private user content
- screenshots with personal data
- unpublished research drafts unless approved

## Acceptance Criteria For New AOIA Steps

Each AOIA step must state:

- objective
- files added or changed
- what is intentionally not implemented
- validation performed
- restore/checkpoint path when relevant

