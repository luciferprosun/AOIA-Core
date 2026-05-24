# AIOA Core Forensic Architecture Summary

Generated: 2026-05-24T18:25:09  
Checkpoint commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`  
Git status at export start:

```text
## main...origin/main [ahead 1]
```

Latest commit:

```text
04adfbd (HEAD -> main) Checkpoint before forensic export snapshot
```

## Runtime Flow

```text
User input
  -> local fast routes
  -> external URL/repository boundary check
  -> local deterministic knowledge route when applicable
  -> model planning fallback
  -> structured JSON action validation
  -> human approval for non-response actions
  -> local executor
  -> operational memory/log update
  -> final response or next bounded step
```

## Retrieval Architecture

AIOA currently contains two related local retrieval/control paths:

- `runtime/adaptive_routing/epistemic_kernel.py`: deterministic epistemic kernel using RHCSA search, provenance, contradiction notices, pressure score, and routing depth.
- `runtime/retrieval/linux/`: first operational deterministic Linux retrieval engine with query normalization, exact/alias/subcommand/category/family/keyword lookup, scoring, provenance attachment, and refusal behavior.

The newer retrieval engine is tested but not yet wired into the main runtime router. That is intentional and avoids premature runtime behavior changes.

## Provenance Model

Source lineage is represented through:

- `runtime/knowledge/manifests/library_manifest.yaml`
- `runtime/knowledge/provenance/PROVENANCE_POLICY.md`
- `runtime/provenance_registry.json`
- `runtime/contradiction_registry.json`

Canonical Linux source:

```text
runtime/knowledge/source/linux_master_library_v1.pdf
SHA256: 7eab9450dd15cc5e1607c29d9fe3b19c4cf9854bb702f113534b6ec34a34dc03
```

Legacy source remains preserved:

```text
runtime/knowledge/source/RHCSA_Command_Library (1).pdf
SHA256: b8092eeabbfd80489d9e5ce8b49ba4d822aa83cc360da0a8f3c76276ac21d6b7
```

## Evidence and Reasoning Separation

The architecture documents define memory as layered authority, not one generic store:

- L0 ephemeral runtime state
- L1 operational logs
- L2 reasoning traces
- L3 provenance records
- L4 immutable evidence
- L5 contradiction registry

Important boundary: runtime logs and model reasoning must not become retrieval evidence without explicit source ingestion and provenance.

## Deterministic Safeguards and Feature Flags

Runtime safeguards include:

- `EPISTEMIC_KILL_SWITCH`
- `EPISTEMIC_DISABLE_MODEL`
- `EPISTEMIC_DISABLE_KNOWLEDGE_ROUTE`
- `EPISTEMIC_DISABLE_MEMORY_HATS`
- `EPISTEMIC_DISABLE_REASONING_TRACE`
- `EPISTEMIC_DISABLE_UNKNOWN_FALLBACK`

The Linux retrieval engine itself refuses low-confidence queries below the deterministic confidence threshold and does not call external APIs, embeddings, vector databases, or autonomous loops.

## Execution Boundaries

`runtime/tools/executor.py` dispatches structured actions only after validation. Non-response actions require human approval in normal runtime flow. Shell execution goes through command validation/classification before dispatch.

## Candidate Promotion Pipeline

Current candidate parser statistics:

| Metric | Count |
| --- | ---: |
| total parsed entries | 3152 |
| total candidate records | 3152 |
| total unique candidate commands | 2570 |
| candidate-only entries | 1978 |
| duplicates against existing canonical/index | 725 |
| internal candidate duplicates | 582 |
| malformed/unresolved entries | 97 |

No candidate rows were promoted into canonical indexes during parsing. This is the correct safety posture.

## Maturity Level

Current maturity: infrastructure prototype with strong local-first boundaries and an operational deterministic retrieval subsystem.

Implemented:

- bounded runtime loop
- approval-gated executor
- provider abstraction
- local RHCSA/Linux knowledge corpus
- canonical source manifest
- candidate parser and reports
- deterministic retrieval engine v1
- retrieval tests
- memory/provenance doctrine

Not yet implemented or intentionally deferred:

- runtime router hook for `LinuxRetrievalEngine`
- candidate promotion into canonical indexes
- reviewed alias/family expansion from candidate corpus
- full provider-independent retrieval answer renderer
- automated report packaging workflow inside repo

## Known Limitations

- Retrieval paths overlap and should be unified behind one facade before router integration.
- Candidate data contains weak descriptions, path artifacts, and PDF merge artifacts.
- Runtime logs/state are present in the repository checkpoint and should receive a long-term archival/ignore policy.
- The Linux retrieval engine is intentionally not wired into the main route yet.
- The system has local-first retrieval but not a production-grade RAG/vector layer; this is by design for deterministic auditability.
