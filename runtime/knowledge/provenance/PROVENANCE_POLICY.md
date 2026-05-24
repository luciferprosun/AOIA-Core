# Linux Engineering Provenance Policy

This policy governs the RHCSA/RHCE/Linux Engineering knowledge layer stored under `runtime/knowledge/`.

## Rules

- No silent overwrites.
- No duplicate master files.
- Every future update needs a changelog.
- Source lineage must be preserved.
- Evidence memory must remain separate from reasoning memory.
- Extracted files must trace back to the canonical PDF or another explicit source artifact.

## Canonical Source

Current canonical source:

- `runtime/knowledge/source/linux_master_library_v1.pdf`

Legacy source retained for backward compatibility:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`

## Extraction Lineage

Extracted artifacts must record or infer their source from:

- `runtime/knowledge/manifests/library_manifest.yaml`
- the canonical source filename
- the source hash where available

Current extracted artifacts:

- `runtime/knowledge/extracted/linux_master_library_v1.txt`
- `runtime/knowledge/extracted/linux_master_library_v1.md`

## Memory Boundary

Evidence memory and reasoning memory are separate authority layers:

- evidence memory may preserve source-backed observations and fingerprints
- reasoning memory may preserve derived analysis or session reasoning
- reasoning memory must not become source provenance
- runtime outputs must not silently promote themselves into canonical evidence

## Future Update Requirements

Every future source update must:

1. Preserve the previous canonical source.
2. Add a versioned new source file.
3. Record source hash and lineage in the manifest.
4. Add a changelog or audit report.
5. Rebuild indexes deterministically.
6. Deduplicate command entries without deleting historical source artifacts.
