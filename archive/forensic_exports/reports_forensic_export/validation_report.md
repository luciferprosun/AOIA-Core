# Forensic Export Validation Report

Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

## Git Status At Validation

```text
## main...origin/main [ahead 1]
?? reports/forensic_export/
```

## Required Artifacts

- `repository_tree.txt`: OK (9938 bytes)
- `file_manifest.csv`: OK (36156 bytes)
- `architecture_summary.md`: OK (4797 bytes)
- `README_AUDIT.md`: OK (2368 bytes)
- `module_summaries.md`: OK (1385 bytes)

## PDF Exports

| PDF | Exists | Size bytes | Pages | Encrypted |
| --- | --- | ---: | ---: | --- |
| `forensic_full_snapshot.pdf` | OK | 115341 | 13 | no |
| `architecture_and_runtime.pdf` | OK | 305586 | 71 | no |
| `retrieval_and_knowledge_layer.pdf` | OK | 718748 | 480 | no |
| `memory_and_provenance.pdf` | OK | 264150 | 66 | no |

## Markdown Chunks

Total chunked markdown files: 8

- `chunked_markdown/docs_and_governance.md` (250739 bytes)
- `chunked_markdown/knowledge_layer.md` (653634 bytes)
- `chunked_markdown/memory_architecture.md` (43427 bytes)
- `chunked_markdown/provenance_system.md` (76483 bytes)
- `chunked_markdown/retrieval_system.md` (50416 bytes)
- `chunked_markdown/runtime_core.md` (139258 bytes)
- `chunked_markdown/tests_and_validation.md` (58255 bytes)
- `chunked_markdown/tooling_and_execution.md` (95587 bytes)

## Source Export

Total exported source files: 291
Source export size: 7.0M
Total export size: 17M

## Notes

- Runtime logic was not modified.
- Canonical indexes were not modified.
- PDF inputs were ASCII-sanitized for LaTeX compatibility only; original markdown and source export preserve original text.
- Runtime logs and cache directories were excluded from source export.
