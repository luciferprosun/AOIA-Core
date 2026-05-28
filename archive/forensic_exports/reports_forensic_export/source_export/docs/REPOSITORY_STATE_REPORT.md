# Repository State Report

Date: 2026-05-24
Repository: AOIA-Core
Local path: `/home/l/Desktop/AOIA-Core`
Remote: `https://github.com/luciferprosun/AOIA-Core.git`
Branch: `main`
HEAD at scan time: `ad548b73ea7cac692fff37207ae7c7119d986b16`

## Purpose

This report documents the current repository state for external architecture and epistemic-framework review.

This is documentation only. No architecture redesign, runtime refactor, file deletion, or research-material cleanup is performed here.

## Snapshot Policy

The transfer archive preserves repository content needed for:

- architecture review
- MHLM/MHSR framework planning
- AOIA lineage analysis
- provenance structure planning
- case-study separation analysis
- repository stabilization planning

The archive intentionally excludes generated or local machine artifacts:

- `.git`
- `.venv`
- `__pycache__`
- `.pytest_cache`
- `node_modules`
- `dist`
- `build`
- cache folders
- temporary runtime logs
- OS junk files such as `.DS_Store`

The archive keeps documentation, reports, prompts, architecture notes, research artifacts, datasets, experiments, lineage records, runtime state snapshots, and knowledge-base files.

## Current Architecture Overview

AOIA-Core is a Python-centered epistemic/runtime framework with a strong documentation layer around authority boundaries, provenance, memory ontology, deterministic routing, and runtime containment.

The repository currently combines:

- runtime application code under `runtime/`
- epistemic routing and deterministic knowledge components
- RHCSA/Linux command knowledge corpus
- provider adapters and model orchestration components
- persistent memory/state snapshots
- architecture and governance documentation
- forensic audit reports and refactor-preparation notes
- tests for routing, containment, determinism, retrieval, and kernel behavior

The current runtime direction is local-first and deterministic-first. Recent work added a deterministic boundary so external URLs and GitHub/GitLab repository requests bypass RHCSA/local Linux retrieval.

## Major Systems

### Runtime

Location: `runtime/`

Contains:

- `main.py` as the main runtime entrypoint
- `providers/` for model provider adapters
- `tools/` for executor, browser, filesystem, shell, memory, scanner, and validation utilities
- `adaptive_routing/` for routing configuration and epistemic kernel behavior
- `router/` and `orchestrator/` for routing and orchestration remnants
- `commands/` for command abstractions
- `prompts/system_prompt.txt` for planner/runtime prompt behavior
- `state/` and `memory/` for runtime state and memory snapshots

### Knowledge And Retrieval

Location: `runtime/knowledge/`

Contains:

- RHCSA/Linux command knowledge in Markdown
- canonical command JSON
- parsed/indexed/context/injection data
- validation tooling and reports
- source PDF retained as evidence/reference material

This area is central to the deterministic local knowledge path and must be reviewed carefully for retrieval boundaries.

### Memory And Provenance

Locations:

- `runtime/memory/`
- `memory/`
- `provenance/`
- `contradictions/`
- `runtime/provenance_registry.json`
- `runtime/contradiction_registry.json`

The repository currently distinguishes intended memory/provenance concepts in documentation, but runtime persistence is still mixed across JSONL logs, state files, and memory files. This is documented as a known contamination risk in the forensic reports.

### Documentation

Locations:

- root `*.md`
- `docs/`
- `docs/architecture/`
- `docs/forensic-runtime-audit/`
- `docs/refactor/`
- `docs/reports/`
- `docs/checkpoints/`
- `docs/ADR/`
- `docs/adr/`

The documentation layer includes architecture plans, memory ontology, contamination reports, dependency graphs, boundary recommendations, governance notes, runtime reports, ADRs, and checkpoint material.

### Tests

Location: `tests/`

Contains unit tests for:

- deterministic behavior
- epistemic kernel behavior
- epistemic registry behavior
- safeguards
- executor containment
- knowledge validation
- main runtime behavior
- RHCSA retrieval
- routing boundary behavior

### Web Surface

Location: `web/`

Contains minimal web/static surface files. It appears secondary to the runtime and architecture documentation.

## Current Folder Organization

Top-level organization:

- `runtime/` - active runtime code, tools, providers, routing, knowledge corpus, state, memory, and prompts
- `docs/` - architecture, ADRs, reports, checkpoints, and review documents
- `tests/` - unit/regression tests
- `archive/` - quarantine archive boundary
- `governance/` - governance placeholder/documentation surface
- `memory/` - top-level memory boundary documentation
- `provenance/` - top-level provenance boundary documentation
- `retrieval/` - top-level retrieval boundary documentation
- `contradictions/` - contradiction registry documentation surface
- `state/` - top-level state snapshots
- root Markdown files - legacy and current architecture reports/plans

## Research Branches And Experimental Areas

The repository contains multiple research and experimental surfaces:

- `runtime/adaptive_routing/dvm_research.md`
- `runtime/adaptive_routing/environment/`
- `runtime/knowledge/` RHCSA corpus, builders, validators, and context injection files
- `runtime/obsidian_vault/` session/evidence/reasoning vault material
- `docs/refactor/` memory and authority split planning
- `docs/forensic-runtime-audit/` forensic runtime mapping
- root architecture reports such as `AOIA_RUNTIME_MAP.md`, `AOIA_DEPENDENCY_GRAPH.md`, and `AOIA_CONTAMINATION_REPORT.md`

These should be preserved for review even where they overlap or are not yet canonical.

## Duplicated Structures

The repository has intentional or historical duplication that should be reviewed before stabilization:

- `docs/ADR/` and `docs/adr/` both exist.
- Memory concepts appear in root Markdown files, `docs/architecture/`, `docs/refactor/`, `runtime/memory/`, and top-level `memory/`.
- Provenance concepts appear in root documentation, `provenance/`, runtime registries, and Obsidian evidence files.
- State exists both at `runtime/state/` and top-level `state/`.
- Reports exist both as root architecture Markdown files and under `docs/reports/` or `docs/forensic-runtime-audit/`.

No consolidation was performed for this snapshot.

## Mixed Concerns

Areas with mixed runtime/research/documentation concerns:

- `runtime/` contains active code, generated scan output, state snapshots, memory files, knowledge datasets, source PDF material, and Obsidian vault content.
- `runtime/knowledge/` includes source material, derived parsed data, command indexes, validation tools, and generated context/injection products.
- `runtime/memory/` includes runtime memory code and JSONL persistence files.
- Root-level Markdown files include architecture doctrine, audit findings, transition plans, and current-state maps.

These mixed concerns are valuable for review but should be treated as stabilization targets later.

## Possible Chaos Points

Notes for reviewers:

- `runtime/tools/memory.py` remains a high-risk boundary because memory, logs, state, reasoning traces, and evidence concepts have historically overlapped.
- L2 reasoning traces and L4 evidence/provenance must remain separated in future implementation.
- RHCSA/local knowledge retrieval should not handle external repository or web URL requests.
- Browser/external URL handoff exists, but full external-source provenance capture is not finalized.
- Runtime state must not become canonical authority.
- Obsidian vault evidence/reasoning/session files are useful for lineage review but should not be treated as canonical evidence without policy.
- Documentation contains both current doctrine and refactor-preparation notes; reviewers should distinguish frozen doctrine from proposed future work.

## Archive Areas

Archive and quarantine surfaces:

- `archive/quarantine/`
- `docs/checkpoints/`
- `docs/forensic-runtime-audit/`
- `docs/refactor/`
- `runtime/obsidian_vault/`

These areas are preserved in the transfer archive because they carry lineage and review context.

## Naming Inconsistencies

Observed naming inconsistencies:

- mixed uppercase/lowercase ADR directories: `docs/ADR/` and `docs/adr/`
- root reports use several naming conventions: `AOIA_*`, `MEMORY_*`, `CURRENT_*`, `ROUTING_*`
- runtime state exists in both `runtime/state/` and top-level `state/`
- memory/provenance/retrieval names exist as both top-level boundary folders and runtime implementation/persistence areas

No renaming was performed.

## Current Working Tree Notes

At scan time, local changes were present in:

- `docs/reports/FINAL_URL_HANDOFF_PATCH.md`
- `runtime/main.py`
- `runtime/prompts/system_prompt.txt`
- `tests/test_routing_boundary.py`

Untracked runtime/state surfaces were also present:

- `runtime/memory/`
- `runtime/obsidian_vault/`
- `runtime/project_scan.json`
- `runtime/state/`
- `state/`

Generated log directories were excluded from the transfer archive as temporary runtime logs.

## File-Type Summary For Transfer Archive

Approximate included file counts after transfer exclusions:

- Python files: 61
- Markdown files: 130
- JSON files: 26
- JSONL files: 7
- text files: 3
- shell scripts: 3
- PDF files: 1

## Generated Documentation

Generated for this snapshot:

- `docs/FULL_PROJECT_TREE.txt`
- `docs/REPOSITORY_STATE_REPORT.md`

## Review Guidance

This repository should be reviewed as a living stabilization snapshot, not as a clean final product.

The highest-value review targets are:

- runtime boundary placement
- memory/provenance separation
- external URL/repository handoff policy
- RHCSA retrieval containment
- authority registry design
- contradiction registry semantics
- separation between research lineage, evidence, operational logs, and runtime state

No implementation changes are recommended or applied by this report.
