# AOIA/NMS NLnet Update Summary

## Project Summary

AOIA/NMS is an open-source AI safety and epistemic-control effort built around AOIA-Core. It aims to make AI-assisted engineering workflows more auditable by separating evidence, provenance, contradictions, model output, and reviewer reasoning.

## Current Implemented State

The repository currently includes:

- local-first AOIA-Core runtime code
- governance documentation
- evidence boundary documentation
- provenance and verification contracts
- contradiction and retrieval-related tests
- reviewer-facing overview material
- stress-test protocol documentation under `docs/stress_tests/`
- grant-facing AOIA/NMS documentation under `docs/nms/`

Some capabilities are implemented in code, some are partial, and some are documentation-only. The project should not be described as production-ready, autonomous, or scientifically validating external claims.

## Recent Improvements Since Proposal Submission

- Reviewer entry points were added.
- Implemented capability status was clarified.
- External model output policy was documented.
- Stress-test and case-study documentation was added.
- Untracked audit artifacts were archived outside the repository.
- Corrected validation now uses `PYTHONPATH=runtime:.` for unittest discovery.
- A grant-facing `docs/nms/` layer now consolidates the AOIA/NMS documentation package.

## Validation Status

Current local validation status:

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS
- unittest count: 145 tests OK, 4 skipped

The skipped tests relate to optional local dependencies. This validation does not claim production readiness or full benchmark execution.

## Stress-Test Plan

The stress-test plan focuses on whether AOIA/NMS can:

- prevent unsupported claims from becoming evidence
- expose contradictions
- track provenance gaps
- compare model behavior under bounded prompts
- preserve uncertainty
- support local/private audit workflows

The current step is documentation, protocol, and roadmap clarity. Full ML benchmark execution is not part of this step.

## LSC Case-Study Boundary

The LSC archive is the first epistemic-audit stress-test case study. It is used to test whether AOIA/NMS can prevent premature validation, detect unsupported claims, track provenance, and expose contradictions.

The goal is not to prove LSC physics. AOIA/NMS does not validate neutrino theory, and model output must not be treated as scientific proof.

SCEMDA, HNC, and Gary material remain external methodological case-study or applied-prototype context. They are not canonical LSC neutrino evidence in this documentation layer.

## Four-Month Roadmap Summary

- Month 1: documentation, governance, and reviewer entry points
- Month 2: stress-test harness and reproducible audit protocol
- Month 3: model comparison workflow and contradiction/provenance reporting
- Month 4: public demo package, documentation cleanup, and sustainability

## What Funding Would Support

Funding would support practical open-source AI safety and epistemic-control work:

- development hardware or workstation access
- documentation and reproducibility work
- stress-test harness development
- local/private audit workflows
- public open-source demo preparation
- developer time

This should not be framed as neutrino research funding. The funding target is tooling for auditable AI-assisted workflows.

## Risks and Safeguards

Risks:

- overstating scientific meaning of the LSC case study
- treating model consensus as evidence
- confusing documentation density with validation
- scope creep into mobile, GUI, ML training, or production-agent work

Safeguards:

- explicit non-goals
- claim classification
- provenance requirements
- contradiction exposure
- reviewer escalation
- documentation-only scope for GT-NLNET-1

## Non-Goals

- proving LSC physics
- validating neutrino theory
- production-ready autonomous agents
- iOS work
- Android/PWA implementation in this step
- frontend or GUI build work
- ML training
- runtime architecture changes
- provider changes
- Evidence Memory activation
- provenance logic changes
- Contradiction Registry logic changes
