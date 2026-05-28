# RHCSA/Linux Existing State Audit

Audit date: 2026-05-24

Scope: AIOA Core RHCSA/Linux knowledge layer, deterministic retrieval assets, evidence/provenance boundaries, and the new canonical PDF input `Library of Linux - Unified RHCSA/RHCE Linux Command Knowledge Library`.

## Audit Result

An RHCSA/Linux knowledge structure already exists. The safe action is to reuse and extend the existing `runtime/knowledge/` tree instead of creating a parallel `knowledge/linux-engineering/` archive.

## Existing RHCSA/Linux-Related Folders

- `runtime/knowledge/`
- `runtime/knowledge/source/`
- `runtime/knowledge/canonical/`
- `runtime/knowledge/raw/`
- `runtime/knowledge/parsed/`
- `runtime/knowledge/index/`
- `runtime/knowledge/context/`
- `runtime/knowledge/injection/`
- `runtime/knowledge/tools/`
- `runtime/knowledge/schema/`
- `runtime/knowledge/validator/`
- `runtime/knowledge/bash/`
- `runtime/knowledge/filesystem/`
- `runtime/knowledge/networking/`
- `runtime/knowledge/permissions/`
- `runtime/knowledge/selinux/`
- `runtime/knowledge/storage/`
- `runtime/knowledge/systemd/`
- `runtime/knowledge/users/`
- `runtime/knowledge/lvm/`
- `runtime/knowledge/podman/`
- `runtime/knowledge/troubleshooting/`
- `runtime/memory/`
- `runtime/obsidian_vault/Evidence/`
- `retrieval/`
- `provenance/`
- `memory/`

## Existing RHCSA/Linux-Related Files

Core runtime retrieval:

- `runtime/knowledge/rhcsa_engine.py`
- `runtime/tools/rhcsa_search.py`
- `runtime/memory/rhcsa_context.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/adaptive_routing/epistemic_kernel.py`

Existing source/canonical/index artifacts:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`
- `runtime/knowledge/canonical/rhcsa_commands.json`
- `runtime/knowledge/raw/rhcsa_raw.txt`
- `runtime/knowledge/parsed/rhcsa_sections.json`
- `runtime/knowledge/index/command_index.json`
- `runtime/knowledge/command_graph.json`
- `runtime/knowledge/context/context_pack.json`
- `runtime/knowledge/injection/injected_context.json`
- `runtime/knowledge/schema/command.schema.json`

Existing docs/reports:

- `runtime/knowledge/README.md`
- `docs/RHCSA_ENGINE_REVIEW.md`
- `docs/LINUX_ENGINEERING_LIBRARY.md`
- `docs/LINUX_ENGINEERING_LIBRARY_REPORT.md`
- `docs/KNOWLEDGE_PACK_RULES.md`
- `docs/KNOWLEDGE_PACK_SPEC.md`
- `AOIA_RUNTIME_MAP.md`
- `AOIA_DEPENDENCY_GRAPH.md`
- `ROUTING_AUTHORITY_ANALYSIS.md`

Existing validation/tests:

- `runtime/knowledge/validator/validation_rules.py`
- `runtime/knowledge/validator/validator.py`
- `runtime/knowledge/validator/validation_report.md`
- `tests/test_rhcsa_retrieval.py`
- `tests/test_knowledge_validator.py`

## Existing Manifests

No dedicated Linux Engineering library manifest was found under `runtime/knowledge/` before this integration. Existing manifest-like files were located in unrelated MHLM/MHSR provider export areas and should not be reused for the RHCSA/Linux runtime knowledge layer.

Created manifest:

- `runtime/knowledge/manifests/library_manifest.yaml`

## Existing Indexes

Existing:

- `runtime/knowledge/index/command_index.json`

Created as a future ingestion template only:

- `runtime/knowledge/index/command_index_template.csv`

No command rows were invented.

## Existing Provenance

Existing provenance foundations:

- `PROVENANCE_FOUNDATION.md`
- `runtime/provenance_registry.json`
- `provenance/README.md`
- `docs/architecture/AOIA_MEMORY_MODEL.md`
- `docs/architecture/FORBIDDEN_MEMORY_FLOWS.md`
- `docs/architecture/MEMORY_LAYER_ACCESS_MATRIX.md`

Created Linux Engineering source policy:

- `runtime/knowledge/provenance/PROVENANCE_POLICY.md`

## Existing PDF/Master Status

Existing older RHCSA source:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`
- SHA256: `b8092eeabbfd80489d9e5ce8b49ba4d822aa83cc360da0a8f3c76276ac21d6b7`

New canonical master source imported safely:

- `runtime/knowledge/source/linux_master_library_v1.pdf`
- SHA256: `7eab9450dd15cc5e1607c29d9fe3b19c4cf9854bb702f113534b6ec34a34dc03`
- Pages: 453
- Encrypted: no

The new PDF is not a byte-for-byte duplicate of the older RHCSA source PDF.

## Possible Duplicates And Overlaps

Potential semantic overlap exists between:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`
- `runtime/knowledge/source/linux_master_library_v1.pdf`
- `runtime/knowledge/canonical/rhcsa_commands.json`
- `runtime/knowledge/index/command_index.json`
- `docs/LINUX_ENGINEERING_LIBRARY.md`

These are not treated as duplicate folder structures. They represent different generations or formats of Linux/RHCSA knowledge. The new PDF is stored as a versioned canonical source, while existing deterministic runtime artifacts are preserved for backward compatibility.

## Safe Merge Path

1. Reuse `runtime/knowledge/` as the canonical runtime knowledge root.
2. Keep the older source PDF and JSON index artifacts intact.
3. Store the new PDF as `runtime/knowledge/source/linux_master_library_v1.pdf`.
4. Store extracted text under `runtime/knowledge/extracted/`.
5. Track source lineage through `runtime/knowledge/manifests/library_manifest.yaml`.
6. Keep generated command indexes append-only and deduplicated.
7. Do not update `runtime/knowledge/canonical/rhcsa_commands.json` until a deterministic parser/index loader phase is run.
8. Keep evidence memory separate from reasoning memory.

## Decision

No duplicate `knowledge/linux-engineering/` tree was created. The existing `runtime/knowledge/` tree was extended because it already contains the live RHCSA source, canonical JSON, parsed sections, command index, retrieval engine, and validation tools.
