# Module Summaries

Generated: 2026-05-24T18:25:09
Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

## Category Inventory

| Category | Files | Bytes |
| --- | ---: | ---: |
| configuration | 10 | 21482 |
| docs | 50 | 164717 |
| governance | 26 | 301410 |
| knowledge | 88 | 6742375 |
| memory | 22 | 105073 |
| provenance | 6 | 47967 |
| reports | 1 | 5591 |
| repository | 20 | 45291 |
| retrieval | 6 | 19916 |
| runtime | 40 | 124382 |
| tests | 10 | 47266 |
| tooling | 15 | 135684 |

## Primary Modules

- `runtime/main.py`: runtime coordinator, local routes, model planning fallback, safeguards, session logging.
- `runtime/tools/executor.py`: structured action execution, approval gate, shell/filesystem/browser dispatch.
- `runtime/adaptive_routing/epistemic_kernel.py`: deterministic local epistemic control layer over RHCSA evidence.
- `runtime/retrieval/linux/`: deterministic Linux retrieval engine v1 with normalization, scoring, provenance attachment, refusal behavior.
- `runtime/knowledge/`: canonical RHCSA commands, command indexes, source PDF, extracted text, candidate index loader, reports.
- `runtime/memory/`: runtime state, evidence/reasoning trace helpers, RHCSA context injection.
- `docs/architecture/`: memory ontology, forbidden flows, access matrix.
- `MHLM_MHSR/`: governance/archive/taxonomy/case-study scaffolding for anti-hallucination analysis.
