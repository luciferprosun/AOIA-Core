# Forbidden Memory Flows

Status: canonical doctrine for AOIA-Core v0.1
Phase: 1A - Memory Ontology Freeze

## Purpose

This document lists memory flows that AOIA-Core must reject by design. These prohibitions exist to prevent runtime convenience, generated text, or operational traces from becoming epistemic authority.

## Absolute Forbidden Flows

| Source | Destination | Status | Reason |
| --- | --- | --- | --- |
| L0 Ephemeral Runtime State | L3 Provenance Records | forbidden | Runtime state is volatile and cannot define source lineage. |
| L0 Ephemeral Runtime State | L4 Immutable Evidence | forbidden | Session continuity is not factual support. |
| L0 Ephemeral Runtime State | L5 Contradiction Registry | forbidden | Temporary state cannot establish contradiction authority. |
| L1 Operational Logs | L3 Provenance Records | forbidden by default | Logs describe runtime actions, not source identity. |
| L1 Operational Logs | L4 Immutable Evidence | forbidden | Execution traces are procedural records, not evidence. |
| L1 Operational Logs | L5 Contradiction Registry | forbidden by default | Logs do not establish source conflict without evidence promotion policy. |
| L2 Reasoning Traces | L3 Provenance Records | forbidden | Reasoning is generated inference, not source lineage. |
| L2 Reasoning Traces | L4 Immutable Evidence | forbidden | Reasoning must never become evidence. |
| L2 Reasoning Traces | Retrieval Corpus | forbidden | Retrieval over reasoning traces creates self-confirming memory. |
| Cloud Planner Output | L3 Provenance Records | forbidden | Planner output is not an external source. |
| Cloud Planner Output | L4 Immutable Evidence | forbidden without external provenance | Provider text is generated output, not evidence. |
| System-Generated Summaries | L3 Provenance Records | forbidden | Summaries are derivatives, not source identity. |
| System-Generated Summaries | L4 Immutable Evidence | forbidden unless linked to raw evidence as derivative | Summaries can drift from source content. |
| L5 Contradiction Registry | Automatic Resolution | forbidden | Contradictions must not be silently erased. |

## Prohibited Patterns

Reasoning-to-evidence promotion:
- Any direct conversion of L2 reasoning text, model explanation, route rationale, confidence note, or fallback explanation into L4 evidence is forbidden.
- Allowed alternative: create an audit reference to the L2 trace while keeping it outside evidence.

Operational-log evidence promotion:
- Any direct conversion of command output, tool result, approval prompt, browser action, or runtime event into L4 evidence is forbidden.
- Allowed alternative: recapture the underlying artifact through an explicit evidence capture policy with fingerprint and provenance.

Runtime-state authority:
- Any use of current task, recent output, active browser page, open tabs, current working directory, or session state as canonical source authority is forbidden.
- Allowed alternative: treat L0 as continuity context only.

Generated-output provenance:
- Any use of provider output, local planner output, summarizer output, or generated markdown as L3 source provenance is forbidden.
- Allowed alternative: use generated output only as a derivative audit artifact linked to external source provenance.

Contradiction auto-resolution:
- Any automatic deletion, overwrite, downgrade, or resolution of L5 contradiction records is forbidden.
- Allowed alternative: append a new status event with explicit evidence/provenance references and reviewer or policy context.

Retrieval over quarantined layers:
- Retrieval must not index or answer from L0 runtime state, L1 operational logs, or L2 reasoning traces.
- Allowed alternative: retrieval may use L3 provenance and L4 evidence subject to authority policy and contradiction checks.

Unfingerprinted capture:
- Browser text, screenshots, copied snippets, generated extracts, and temporary files must not become L4 evidence without fingerprint, capture time, and source linkage.
- Allowed alternative: store them as quarantined captures until evidence creation policy accepts them.

## Forbidden Output Effects

Forbidden effects on L3:
- Creating provenance from runtime convenience state.
- Replacing prior source identity silently.
- Treating generated summaries as source artifacts.
- Removing old lineage during regeneration without explicit epoch metadata.

Forbidden effects on L4:
- Overwriting existing evidence.
- Storing evidence without content identity.
- Storing evidence without source linkage when the artifact is derived.
- Treating reasoning, logs, or cloud output as evidence.

Forbidden effects on L5:
- Resolving contradictions automatically.
- Deleting contradiction history.
- Creating contradictions from generated disagreement alone.
- Collapsing contradiction status into runtime confidence state.

## Quarantine Requirements

The following must remain quarantined unless a future explicit policy says otherwise:
- L0 runtime state snapshots.
- L1 operational logs and command logs.
- L2 reasoning traces and reasoning summaries.
- Cloud planner output.
- Provider responses.
- System-generated summaries.
- Operator notes not promoted by review.
- Browser captures lacking fingerprint and source linkage.
- Any artifact with unknown source identity.

## Required Promotion Gate

Any future promotion into L3, L4, or L5 must answer:
- What is the source artifact?
- What is the source fingerprint or identity?
- Is the destination layer allowed for this artifact class?
- Is the transformation deterministic or reviewed?
- Is derivative lineage preserved?
- Are contradictions preserved rather than erased?
- Is the promotion recorded as an append-only event?

If any answer is missing, promotion is forbidden.
