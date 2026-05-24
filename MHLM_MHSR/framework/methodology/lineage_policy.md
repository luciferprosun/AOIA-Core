# Lineage Policy

## Purpose

Define how artifact history should be recorded during future migration phases.

## Lineage Event Types

- import: raw artifact enters the framework.
- normalize: raw artifact is converted into a standard format.
- classify: artifact is assigned to a case study or taxonomy.
- synthesize: derived report or summary is created.
- review: human or model reviewer records observations.
- quarantine: artifact is held due to ambiguity or provenance risk.

## Lineage Rules

- Every normalized artifact should trace to one or more raw artifacts.
- Every derived artifact should trace to raw or normalized inputs.
- Case study assignment must be explicit.
- LSC and AOIA lineage must remain separate unless a future cross-case reference policy is approved.
- A lineage event records what happened; it does not prove correctness.

## Non-Authoritative Records

Operational logs and reasoning traces may be recorded as lineage context, but they are not evidence by themselves.
