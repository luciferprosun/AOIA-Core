# NiFe Synapses Project

## Status

This is docs-only future planning.

- Not implemented in AOIA-Core runtime.
- Does not change AOIA-Core execution behavior.
- No tag resolver, server, API, or runtime integration exists yet.
- No execution authority is created by this plan.

## Purpose

NiFe Synapses is a future AOIA knowledge-addressing layer. Its purpose is to define how lightweight symbolic tags may later point toward validated knowledge entries without embedding the full knowledge payload inside a hat.

## Relationship to AOIA / IOA roadmap

This plan expands the future direction described in `docs/future/AOIA_IOA_2027_2028_VERIFICATION_ROADMAP.md`.

- 2027 remains the planning phase for knowledge tagging and hat registry structure.
- 2028 remains the future IOA / LLM model-verification direction.
- Current AOIA-Core priority remains Bash Safety and pre-execution command inspection.

## Why hats store tags, not full knowledge

Hats should remain lightweight and composable.

- Hats store symbolic tags or pheromone keys, not full knowledge blobs.
- Full knowledge may later live in local knowledge bases, repositories, or server-side knowledge oceans.
- Tags may point to future validated knowledge entries.
- Tags must not be treated as proof by themselves.

This separation keeps runtime boundaries conservative and makes provenance, contradiction handling, and validation easier to audit.

## Symbolic mV pheromone tags

NiFe uses symbolic `mV:` identifiers as conceptual pheromone tags.

- Tags are address markers, not measurements.
- Tags are stable symbolic references for future knowledge mapping.
- Example tags:
  - `mV:-70`
  - `mV:-70.000001`
  - `mV:-70.000002`

## Critical rule: tags are strings, not floats

Pheromone tags are symbolic identifiers, not biological measurements and not floating-point numbers.

- Tags are strings.
- Tags must not be parsed as numeric truth scores.
- Tags must not be used as biological measurements.
- Tags must not be used to bypass validation or safety review.

## First spark: mV:-70

The first symbolic knowledge spark is `mV:-70`.

In this planning phase, `mV:-70` is the conceptual root key for Hat 001: Bash Safety / Pre-Execution Command Inspection.

## Hat/domain root-key approach

Each future hat can have a domain root key.

- Hat 001 root key: `mV:-70`
- Hat 002 root key: `mV:-71`

Sub-tags extend from the domain root. This allows a compact namespace that can later map concepts, evidence, contradiction states, and source links without storing the full knowledge directly inside the hat.

## Knowledge resolver concept, future-only

A future knowledge resolver may translate a symbolic tag into a validated knowledge entry or evidence bundle.

Important boundaries:

- No resolver exists yet.
- No runtime lookup exists yet.
- No automatic retrieval exists yet.
- A tag can suggest retrieval, but it cannot authorize execution or bypass AOIA safety gates.

## Knowledge ocean / local KB / server KB concept, future-only

Future storage concepts may include:

- local knowledge bases
- repository-backed knowledge records
- server-side knowledge oceans

These are future-only concepts.

- No local KB implementation exists yet.
- No server KB implementation exists yet.
- No AOIA-Core runtime integration exists yet.

## Open-source knowledge principle

NiFe should prefer auditable, open-source, and reviewable knowledge sources wherever possible.

Open-source knowledge is valuable because it improves:

- transparency
- reproducibility
- public review
- provenance tracing
- contradiction handling

Open-source links are useful only when source status remains explicit and conservative.

## Public LLM conversation links are deferred

Public LLM conversations must not be treated as validated knowledge without a future source registry and validation workflow.

- Public LLM conversation links are deferred.
- They may later exist as `reference_only`.
- They must not be promoted by default.
- Model-generated conversation text is not proof.

## Model verification/ranking is future-only

Future IOA model verification may later evaluate epistemic behavior, source discipline, contradiction handling, and safety-boundary compliance.

- No model-verification implementation exists yet.
- No model-ranking implementation exists yet.
- No leaderboard or scoring runtime exists yet.

## Safety and epistemic rules

- Tags do not authorize execution.
- Tags do not bypass evidence, provenance, or contradiction rules.
- Model output is not validated knowledge by default.
- Public LLM conversations are not validated knowledge by default.
- Dangerous knowledge areas require explicit source review and human oversight.
- AOIA-Core runtime boundaries remain unchanged by this plan.

## Non-goals

This document does not implement:

- runtime code changes
- tag resolver logic
- server storage
- knowledge retrieval
- API endpoints
- model-ranking code
- public LLM chat ingestion
- execution
- trading bot integration
- Cloudflare/provider/routing changes

## What can start now

- docs-only hat planning
- tag vocabulary design
- conceptual tag maps
- source-registry planning
- validation-workflow planning
- linking future tags to validated AOIA reports and commits

## What must wait

- runtime tag resolution
- automatic retrieval
- server-backed knowledge storage
- active public conversation linking
- model verification engine
- model ranking outputs
- any execution coupling

## Recommended next steps

1. Define the initial tag status vocabulary and promotion rules.
2. Establish Hat 001 as the conceptual Bash Safety map tied to GT-RUNTIME-8B through GT-RUNTIME-8F.
3. Establish Hat 002 as an RHCSA/Linux Administration planning shell with conservative validation requirements.
4. Prepare future docs for source registry and validation workflow before any runtime integration is discussed.
