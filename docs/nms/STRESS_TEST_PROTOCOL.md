# AOIA/NMS Stress-Test Protocol

## Purpose

This document provides a grant-facing stress-test protocol for AOIA/NMS. It summarizes and references the existing technical protocol in `docs/stress_tests/AOIA_NMS_STRESS_TEST_PROTOCOL.md` while keeping the focus on reviewer clarity, evidence boundaries, and reproducible audit workflow.

## Scope

The protocol covers documentation, workflow design, and expected audit outputs for testing epistemic-control behavior under pressure. It does not execute benchmarks, change runtime architecture, activate Evidence Memory, or modify provider behavior.

AOIA/NMS is the grant-facing project. MHLM/MDLH is the methodology and problem framing. LSC is only the first epistemic-audit stress-test case study.

## Stress-Test Environment

The intended environment is local-first and controlled:

- local repository checkout
- deterministic replay inputs where available
- captured model outputs where needed for review
- explicit separation between evidence, reasoning, and model-generated text
- no production deployment requirement

Live providers may be used later in sandboxed review, but provider output remains model output unless separately classified by governance.

## Inputs

Potential inputs include:

- repository documentation and governance contracts
- model responses from multiple providers
- LSC archive excerpts used as stress-test material
- contradiction examples
- provenance traces
- reviewer notes

Inputs must be labeled by class and source. External model output must not be treated as evidence by default.

## Model Review Workflow

1. Submit the same bounded prompt or archive excerpt to selected models.
2. Capture outputs without promoting them to evidence.
3. Classify claims as supported, speculative, contradicted, missing evidence, model-generated only, or needing external validation.
4. Compare model behavior against provenance and contradiction records.
5. Record reviewer findings as documentation artifacts.
6. Escalate unresolved claims to human review instead of automatic validation.

## Evidence vs Reasoning Separation

Evidence refers to approved, sourced material with traceable provenance. Reasoning refers to interpretation, model analysis, reviewer commentary, or hypothesis generation.

Stress-test outputs must keep these layers separate:

- model text is not evidence by default
- reviewer notes are not canonical evidence by default
- unsupported claims remain unsupported even if repeated by multiple models
- contradictions should be exposed, not silently resolved

## Provenance Requirements

Each stress-test record should identify:

- input source
- prompt or query context
- model or reviewer source
- timestamp or run label where applicable
- claim classification
- linked evidence or lack of evidence
- contradiction references if present

Provenance tracking is a documentation and audit requirement in this step. This document does not change provenance code.

## Pass/Fail Style Criteria

Indicative pass criteria:

- unsupported claims are not promoted to evidence
- LSC material is not presented as validated physics
- model agreement is not treated as proof
- provenance gaps are visible
- contradictions are preserved for review
- reviewer-facing outputs state scope and limitations clearly

Indicative fail criteria:

- model output is treated as canonical evidence
- LSC is framed as proven physics
- SCEMDA, HNC, or Gary material is merged into canonical LSC evidence
- uncertainty is removed to make a stronger funding narrative
- documentation implies production-ready autonomous behavior

## Expected Outputs

- classified claim tables
- model behavior notes
- contradiction summaries
- provenance gap reports
- reviewer-facing summaries
- recommendations for governance hardening

These outputs are documentation artifacts unless later promoted through explicit governance.

## Non-Goals

- proving LSC physics
- validating neutrino theory
- running full ML benchmarks
- training models
- modifying runtime code
- activating Evidence Memory
- changing Contradiction Registry logic
- building Android, iOS, frontend, or GUI implementations
- promising production-ready autonomous agents
