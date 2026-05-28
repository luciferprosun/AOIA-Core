# Linux Engineering Knowledge Layer

The Linux Engineering knowledge layer is the local RHCSA/RHCE/Linux command corpus used by AIOA Core for deterministic, local-first technical retrieval.

## Why It Exists

AIOA Core already has a deterministic RHCSA retrieval path in `runtime/knowledge/`, `runtime/tools/rhcsa_search.py`, and `runtime/knowledge/rhcsa_engine.py`. This layer keeps Linux administration knowledge available without relying on a cloud model for every operational question.

The layer supports:

- RHCSA/RHCE study and command lookup
- local-first Linux administration answers
- deterministic retrieval over known source artifacts
- future command indexing toward a 10,000+ utility archive
- provenance-aware source handling

## Current Source Layout

The repository already had an RHCSA knowledge tree, so the integration reuses it instead of creating a duplicate `knowledge/linux-engineering/` tree.

Canonical source:

- `runtime/knowledge/source/linux_master_library_v1.pdf`

Legacy source retained:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`

Manifest:

- `runtime/knowledge/manifests/library_manifest.yaml`

Extracted text:

- `runtime/knowledge/extracted/linux_master_library_v1.txt`
- `runtime/knowledge/extracted/linux_master_library_v1.md`

Index template:

- `runtime/knowledge/index/command_index_template.csv`

## Deterministic Local-First Retrieval

Future retrieval should use deterministic preprocessing:

1. extract text from the canonical PDF
2. parse commands and examples into structured records
3. deduplicate against existing `rhcsa_commands.json`
4. preserve source page and source hash metadata
5. write versioned indexes
6. validate schema and category consistency
7. only then update runtime retrieval surfaces

No retrieval update should silently overwrite existing indexes.

## Future 10,000+ Command Updates

Future expansion should be append-only and versioned:

- add each new source as a versioned artifact
- record source hash in the manifest
- extract into `runtime/knowledge/extracted/`
- generate candidate rows into a review index
- deduplicate by command, subcommand, alias, package family, and ecosystem
- preserve deprecated commands and aliases as explicit metadata
- rebuild deterministic indexes only after validation

Do not mix evidence memory with reasoning memory. Extracted source text and command records belong to the knowledge/provenance layer; runtime reasoning traces remain separate.
