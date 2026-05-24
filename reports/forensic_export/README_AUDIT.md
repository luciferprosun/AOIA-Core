# AIOA Core Forensic Export

Generated: 2026-05-24T18:25:09  
Repository: `/home/l/Desktop/AOIA-Core`  
Checkpoint commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

## What This Export Is

This is a read-only forensic export snapshot of the AIOA Core application. It is intended for architecture auditing, external model review, forensic archival, reproducibility, future research analysis, and AI safety verification.

## Repository State

```text
## main...origin/main [ahead 1]
```

Latest commit:

```text
04adfbd (HEAD -> main) Checkpoint before forensic export snapshot
```

## How To Navigate

Start here:

1. `architecture_summary.md` for system-level architecture.
2. `module_summaries.md` for module inventory.
3. `repository_tree.txt` for hierarchy.
4. `file_manifest.csv` for file-level metadata.
5. `chunked_markdown/` for subsystem-specific code review.
6. `source_export/` for full text/source file export preserving hierarchy.
7. PDFs for portable review.

## Implemented vs Conceptual

Implemented:

- Runtime coordinator and bounded action loop.
- Structured execution engine with approval gate.
- Local RHCSA/Linux knowledge corpus.
- Canonical Linux PDF source and extraction.
- Candidate command index loader.
- Deterministic Linux retrieval engine v1.
- Retrieval tests.
- Memory/provenance doctrine and governance docs.

Conceptual or deferred:

- Promotion of candidate commands into canonical indexes.
- Feature-flagged runtime hook for the new retrieval engine.
- Unified retrieval facade across kernel, RHCSA search, and Linux retrieval engine.
- Production packaging for repeated forensic exports.

## Known Risks

- Overlapping retrieval paths can diverge unless consolidated.
- Candidate corpus contains malformed/path/PDF artifact records and must not be blindly promoted.
- Runtime logs/state were part of the prior checkpoint; future policy should decide whether they remain versioned or move to archived artifacts.
- External providers are available but must remain lower priority than deterministic local evidence for Linux/RHCSA answers.

## Export Contents

- `repository_tree.txt`
- `file_manifest.csv`
- `architecture_summary.md`
- `module_summaries.md`
- `source_export/`
- `chunked_markdown/`
- `forensic_full_snapshot.pdf`
- `architecture_and_runtime.pdf`
- `retrieval_and_knowledge_layer.pdf`
- `memory_and_provenance.pdf`
