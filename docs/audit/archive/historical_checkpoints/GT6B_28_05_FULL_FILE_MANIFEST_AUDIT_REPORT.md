# GT6B 28.05 Full File Manifest Audit Report

Date: 2026-05-28
Repository: `/home/l/Desktop/AOIA-Core`
Canonical GitHub: `https://github.com/luciferprosun/AOIA-Core`
Mode: read-only manifest audit

## Current Git State

- Current branch: `main`
- Current HEAD: `8cc67e4640de2ba2f430874fbf47dd44da5022e1`
- Recent commits:

```text
8cc67e4 docs: add GT6 authority audit
4ae93d6 fix: ignore generated runtime state
742555b checkpoint: deadline save1
ee6f64a docs: close Phase 0E provenance readout
b059fcc feat: add provenance integrity readout
```

Current status:

```text
## main...origin/main
?? docs/audit/GT6_28_05_COMMIT_PUSH_FINAL_REPORT.md
?? docs/audit/GT7_28_05_HANDOFF_REPORT.md
```

## Full Manifest Summary

- Total manifest files inspected: `723`
- Excluded local/cache/private candidates: `6493`
- Git tracked files in manifest: `679`
- Git untracked files in manifest: `44`
- RHCSA/RHP/Linux knowledge-related files found: `254`

## Total File Count By Extension

| Key | Count |
| --- | ---: |
| `(none)` | 2 |
| `.css` | 1 |
| `.csv` | 5 |
| `.html` | 5 |
| `.js` | 1 |
| `.json` | 79 |
| `.jsonl` | 11 |
| `.md` | 411 |
| `.pdf` | 8 |
| `.py` | 172 |
| `.sh` | 7 |
| `.txt` | 13 |
| `.yaml` | 2 |
| `.yml` | 6 |

## Classification Counts

| Key | Count |
| --- | ---: |
| `binary-or-rendered` | 1 |
| `canonical` | 14 |
| `external-model-output` | 328 |
| `generated-runtime` | 52 |
| `historical` | 29 |
| `knowledge-asset` | 94 |
| `quarantine` | 1 |
| `source-code` | 67 |
| `stale` | 18 |
| `tests` | 26 |
| `unknown-needs-review` | 93 |

## Tracked / Untracked Summary

| Key | Count |
| --- | ---: |
| `no` | 44 |
| `yes` | 679 |

## Markdown Authority Summary

Root markdown authority is still broad. Canonical candidates exist, but many root-level planning/audit documents should not be interpreted as current doctrine without human review.

Canonical documentation candidates:

- `AUTHORITY_SCOPE.md` (canonical, keep canonical)
- `README.md` (canonical, keep canonical)
- `ROADMAP.md` (canonical, keep canonical)
- `docs/ADR/ADR-001-deterministic-routing.md` (canonical, keep canonical)
- `docs/ADR/ADR-002-three-depth-model.md` (canonical, keep canonical)
- `docs/ADR/ADR-003-local-first-execution.md` (canonical, keep canonical)
- `docs/ADR/ADR-004-no-runtime-learning.md` (canonical, keep canonical)
- `docs/ADR/ADR-005-fail-fast-philosophy.md` (canonical, keep canonical)
- `docs/governance/APPEND_ONLY_PROVENANCE_CONTRACT.md` (canonical, keep canonical)
- `docs/governance/EVIDENCE_WRITE_CONTRACT.md` (canonical, keep canonical)
- `docs/governance/GOVERNANCE_IMPLEMENTATION_STATUS.md` (canonical, keep canonical)
- `docs/governance/PROVENANCE_VERIFICATION_CONTRACT.md` (canonical, keep canonical)
- `docs/governance/TEST_ENVIRONMENT_POLICY.md` (canonical, keep canonical)
- `docs/stabilization/PHASE_0E_CLOSURE_REPORT.md` (canonical, keep canonical)

## docs/ADR vs docs/adr Final Risk Assessment

Risk level: HIGH.

`docs/ADR/` appears to be the preferred current canonical ADR tree. `docs/adr/` contains older accepted ADRs with earlier terminology and isolation-era assumptions. Physical archive/move is not yet performed in GT6B; GT7 should resolve this only after human review.

## Root-Level Markdown Assessment

Root-level markdown contains a mix of canonical, historical, stale, and unknown authority roles. The strongest candidates for root retention are `README.md`, `ROADMAP.md`, and `AUTHORITY_SCOPE.md`. Many other root markdowns are planning or audit artifacts and should be reviewed for relocation in GT7.

## reports/ Assessment

`reports/forensic_export/` contains rendered and duplicated forensic exports. It should remain excluded from evidence/canonical ingestion. `reports/linux-engineering/` is useful historical Linux/RHCSA audit material but is not the canonical runtime knowledge pack.

## Runtime Generated-State Assessment

Generated runtime zones remain present on disk, but GT3/GT4 removed them from Git authority. They include `runtime/logs/`, `runtime/memory/*.jsonl`, `runtime/obsidian_vault/`, `runtime/state/*.json`, `runtime/project_scan.json`, and `runtime/contradiction_registry.json`. These should not feed future Evidence Memory by path alone.

## RHCSA/RHP/Linux Knowledge Asset Assessment

RHCSA/RHP/Linux knowledge-related files found: `254`.

Relevant examples:

- `docs/KNOWLEDGE_PACK_RULES.md` (unknown-needs-review, review before GT7 move/archive decisions)
- `docs/KNOWLEDGE_PACK_SPEC.md` (unknown-needs-review, review before GT7 move/archive decisions)
- `docs/LINUX_ENGINEERING_LIBRARY.md` (unknown-needs-review, review before GT7 move/archive decisions)
- `docs/LINUX_ENGINEERING_LIBRARY_REPORT.md` (unknown-needs-review, review before GT7 move/archive decisions)
- `docs/RHCSA_ENGINE_REVIEW.md` (unknown-needs-review, review before GT7 move/archive decisions)
- `docs/audit/AOIA_RHCSA_KNOWLEDGE_SEPARATION_PLAN.md` (historical, keep as historical audit record)
- `docs/linux-engineering/README.md` (unknown-needs-review, review before GT7 move/archive decisions)
- `reports/forensic_export/chunked_markdown/knowledge_layer.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/chunked_markdown/retrieval_system.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/pdf_inputs/retrieval_and_knowledge_layer.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/retrieval_and_knowledge_layer.html` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/retrieval_and_knowledge_layer.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/retrieval_and_knowledge_layer.pdf` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/docs/KNOWLEDGE_PACK_RULES.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/docs/KNOWLEDGE_PACK_SPEC.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/docs/LINUX_ENGINEERING_LIBRARY.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/docs/LINUX_ENGINEERING_LIBRARY_REPORT.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/docs/RHCSA_ENGINE_REVIEW.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/docs/linux-engineering/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/reports/linux-engineering/rhcsa_existing_state_audit.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/retrieval/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/commands/__init__.py` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/commands/base.py` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/commands/local_commands.py` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/__init__.py` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/bash/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/bash/skrypty-bash-podstawy.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/bash/wyszukiwanie-i-filtrowanie-tekstu.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/bash/zaawansowane-narzdzia-tekstowe.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/bash/zmienne-rodowiskowe-i-powoka.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/candidates/candidate_command_index.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/candidates/candidate_commands.csv` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/canonical/rhcsa_commands.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/command_graph.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/context/context_pack.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/examples/ls-command.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/examples/rm-recursive-force.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/examples/systemctl-status.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/extracted/linux_master_library_v1.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/extracted/linux_master_library_v1.txt` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/filesystem/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/filesystem/archiwizacja-i-kompresja.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/filesystem/edytor-vim.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/filesystem/nawigacja-po-systemie-plikow.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/filesystem/operacje-na-plikach-i-katalogach.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/filesystem/przegldanie-zawartoci-plikow.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/filesystem/wyszukiwanie-plikow.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/index/command_index.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/index/command_index_template.csv` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/injection/injected_context.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/lvm/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/lvm/lvm-logical-volume-manager.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/manifests/library_manifest.yaml` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/networking/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/networking/nfs-i-autofs.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/networking/samba-i-nfs-klient.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/networking/sie-konfiguracja-i-diagnostyka.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/networking/ssh-i-dostp-zdalny.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/networking/zapora-ogniowa-firewalld.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/parsed/rhcsa_sections.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/permissions/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/permissions/uprawnienia-i-wasno-plikow.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/podman/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/podman/kontenery-podman.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/provenance/PROVENANCE_POLICY.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/raw/rhcsa_raw.txt` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/reports/category_distribution.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/reports/deduplication_report.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/reports/parsing_quality_report.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/reports/retrieval_engine_report.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/rhcsa_engine.py` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/schema/command.schema.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/selinux/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/selinux/selinux.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/storage/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/storage/przechowywanie-danych-dyski-i-partycje.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/storage/systemy-plikow-i-montowanie.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/storage/zarzdzanie-dyskami-raid.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/runtime/knowledge/systemd/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- ... 174 additional entries in JSON inventory

Assessment: `runtime/knowledge/` contains the active knowledge and retrieval asset set, including canonical command data, indexes, examples, schemas, source PDFs, extraction outputs, validation reports, and tooling. Later review should separate runtime-consumed canonical packs from raw/build/report assets.

## Stale Candidates

- `AOIA_CANONICAL_STRUCTURE_PLAN.md` (stale, candidate for GT7 planning/archive review)
- `AOIA_CONTAMINATION_REPORT.md` (stale, candidate for GT7 planning/archive review)
- `AOIA_DEPENDENCY_GRAPH.md` (stale, candidate for GT7 planning/archive review)
- `AOIA_ENVIRONMENT_AUDIT.md` (stale, candidate for GT7 planning/archive review)
- `AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md` (stale, candidate for GT7 planning/archive review)
- `AOIA_TRANSITIONAL_COMPONENTS.md` (stale, candidate for GT7 planning/archive review)
- `CURRENT_MEMORY_FLOW.md` (stale, candidate for GT7 planning/archive review)
- `MEMORY_BOUNDARY_ANALYSIS.md` (stale, candidate for GT7 planning/archive review)
- `MEMORY_LAYER_DECOMPOSITION.md` (stale, candidate for GT7 planning/archive review)
- `MUTABLE_STATE_ISOLATION_PLAN.md` (stale, candidate for GT7 planning/archive review)
- `ORCHESTRATION_REMNANT_AUDIT.md` (stale, candidate for GT7 planning/archive review)
- `ROUTING_AUTHORITY_ANALYSIS.md` (stale, candidate for GT7 planning/archive review)
- `docs/adr/0001-keep-aoia-isolated.md` (stale, review before GT7 ADR consolidation)
- `docs/adr/0002-minimal-deterministic-router-skeleton.md` (stale, review before GT7 ADR consolidation)
- `docs/adr/0003-immutable-startup-configuration.md` (stale, review before GT7 ADR consolidation)
- `docs/adr/0004-stdout-only-plain-text-logging.md` (stale, review before GT7 ADR consolidation)
- `docs/adr/0005-test-constitution-determinism-first.md` (stale, review before GT7 ADR consolidation)
- `docs/adr/README.md` (stale, review before GT7 ADR consolidation)

## Quarantine Candidates

- `archive/quarantine/README.md` (quarantine, keep quarantined)
- `docs/audit/AOIA_CLEANUP_PHASE1_WEB_INFORMED_MASTER_REPORT.md` (external-model-output, do not treat as canonical doctrine)
- `docs/reports/AOIA_RESTART_PRODUCTION_REPORT.pdf` (external-model-output, exclude from evidence/canonical ingestion)
- `docs/reports/AOIA_TUI_PHASE1_REPORT.md` (external-model-output, exclude from evidence/canonical ingestion)
- `docs/reports/AOIA_TUI_PHASE2_REPORT.md` (external-model-output, exclude from evidence/canonical ingestion)
- `docs/reports/FINAL_URL_HANDOFF_PATCH.md` (external-model-output, exclude from evidence/canonical ingestion)
- `docs/reports/PHASE_1A_GIT_VALIDATION.md` (external-model-output, exclude from evidence/canonical ingestion)
- `docs/reports/PHASE_2B_ROUTING_BOUNDARY.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/README_AUDIT.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/architecture_and_runtime.html` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/architecture_and_runtime.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/architecture_and_runtime.pdf` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/architecture_summary.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/chunked_markdown/docs_and_governance.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/chunked_markdown/knowledge_layer.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/chunked_markdown/memory_architecture.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/chunked_markdown/provenance_system.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/chunked_markdown/retrieval_system.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/chunked_markdown/runtime_core.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/chunked_markdown/tests_and_validation.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/chunked_markdown/tooling_and_execution.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/export_metadata.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/file_manifest.csv` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/forensic_full_snapshot.html` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/forensic_full_snapshot.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/forensic_full_snapshot.pdf` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/memory_and_provenance.html` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/memory_and_provenance.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/memory_and_provenance.pdf` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/module_summaries.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/pdf_inputs/architecture_and_runtime.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/pdf_inputs/forensic_full_snapshot.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/pdf_inputs/memory_and_provenance.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/pdf_inputs/retrieval_and_knowledge_layer.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/repository_tree.txt` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/retrieval_and_knowledge_layer.html` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/retrieval_and_knowledge_layer.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/retrieval_and_knowledge_layer.pdf` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/AOIA_CANONICAL_STRUCTURE_PLAN.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/AOIA_CONTAMINATION_REPORT.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/AOIA_DEPENDENCY_GRAPH.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/AOIA_MEMORY_ONTOLOGY.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/AOIA_RUNTIME_MAP.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/AOIA_TRANSITIONAL_COMPONENTS.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/AUTHORITY_SCOPE.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/CONTRADICTION_SEMANTICS.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/CURRENT_MEMORY_FLOW.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/FILESYSTEM_ONTOLOGY_LAYOUT.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MEMORY_BOUNDARY_ANALYSIS.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MEMORY_LAYER_DECOMPOSITION.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/DEPENDENCY_BOUNDARY_ANALYSIS.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/MEMORY_DOMAIN_SPLIT_PLAN.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/contracts/RUNTIME_SAFETY_CONTRACTS.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/enforcement/ENFORCEMENT_LAYER_DESIGN.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/archive/AOIA_MASTER_LIBRARY/MASTER_INDEX.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/contradictions/CONTRADICTION_TAXONOMY.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/governance/GOVERNANCE_MODEL.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/lineage/LINEAGE_POLICY.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/prompts/PROMPT_ARCHIVE_POLICY.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/provenance/PROVENANCE_MODEL_PREP.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/claude/MANIFEST.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/codex/MANIFEST.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/deepseek/MANIFEST.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/gemini/MANIFEST.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/kimi/MANIFEST.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/unknown/MANIFEST.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/anti_hallucination_epi_app/unclassified/UNCLASSIFIED_MANIFEST.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/case_studies/lsc_neutrino/README.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/methodology/contradiction_policy.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/methodology/evidence_policy.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/methodology/inclusion_rules.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/methodology/lineage_policy.md` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/schemas/artifact.schema.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/schemas/case_study_manifest.schema.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/schemas/lineage_event.schema.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/schemas/provenance_record.schema.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/schemas/report.schema.json` (external-model-output, exclude from evidence/canonical ingestion)
- `reports/forensic_export/source_export/MHLM_MHSR/framework/taxonomy/case_studies.yml` (external-model-output, exclude from evidence/canonical ingestion)
- ... 301 additional entries in JSON inventory

## GT7 Readiness Assessment

GT7 physical archive/move is conditionally ready but still needs human approval. The manifest is now complete enough to support relocation decisions, but this audit does not itself authorize moving files.

## Safety Confirmation

No source code, runtime architecture, provenance implementation, Evidence Memory, Contradiction Registry, or RHCSA/RHP knowledge assets were modified by this audit. Only audit/export artifacts were created.

## Recommended Next Step

Human review of GT6B manifest and Master Library. After that, decide whether a controlled GT7 archive/move is safe. Do not start Phase 1A Evidence Memory before GT7 scope is approved.
