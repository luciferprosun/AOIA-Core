# Memory Boundary Analysis

Date: 2026-05-23
Phase: Memory Ontology Foundation

## Analyzed Surfaces

- `runtime/tools/memory.py`
- repo-local mutable directories
- `obsidian_vault/`
- `logs/`
- retrieval path through `AOIAEpistemicKernel`

## Mixed Authority Paths

### Path 1: operational result -> history + evidence

Observed:
- executor records every action result as both history and evidence

Boundary problem:
- operational execution trace crosses directly into evidence authority

### Path 2: event logging -> vault projection

Observed:
- history and browser events generate human-readable daily notes

Boundary problem:
- continuity projection is coupled to low-level operational data

### Path 3: retrieval evidence -> reasoning + evidence

Observed:
- kernel evidence is written to evidence store
- kernel reasoning is written separately

Boundary problem:
- this path is closer to correct ontology, but still lacks a strict evidence object model

### Path 4: repo-root source -> mutable runtime outputs

Observed:
- source authority and runtime mutability occupy the same repository root

Boundary problem:
- source and execution byproducts are not physically isolated

## Recursive Contamination Risks

1. vault summaries may later be treated as operator memory despite being derived from mixed sources
2. action logs may re-enter later reasoning as if they were factual evidence
3. saved page text snapshots may become evidence without provenance fingerprinting
4. generated registry outputs may be treated as immutable truth even when underlying knowledge changes

## Mutable / Immutable Ambiguity

Clearly mutable today:
- `state/`
- `logs/`
- `memory/`
- `screenshots/`
- `obsidian_vault/`

Should be treated as mostly immutable or versioned:
- provenance registry snapshots
- contradiction registry snapshots
- evidence captures once persisted

Ambiguity:
- current `memory/evidence_memory.jsonl` is append-only in practice, but not formally protected as immutable evidence

## Evidence / Log Overlap

Current overlap sources:
- `append_history("action_result", payload)`
- `append_evidence("action_result", payload)`

This is the clearest ontology violation in current memory behavior.

## Runtime / Report Overlap

Observed:
- Obsidian vault acts both as runtime side effect and human-facing continuity/report surface

Impact:
- report-like memory is generated from operational runtime paths by default

## Boundary Recommendations

1. separate operational logging from evidence capture semantically
2. require explicit promotion rules from captured artifact to evidence
3. treat vault notes as projection, not canonical memory authority
4. treat provenance and contradiction registries as dedicated layers, not generic memory
5. isolate mutable directories from source authority root in a later implementation phase

## Final Boundary Judgment

Current memory system is functional but boundary-ambiguous.

Main boundary failure:
- logs and evidence are not yet ontologically separated strongly enough
