# AIOA Core Forensic Full Snapshot

Generated: 2026-05-24T18:25:09
Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

This PDF is a navigable forensic packet. Full raw source files are preserved separately in `source_export/` and subsystem markdown chunks.

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


# Repository Tree

```text
AIOA-Core forensic repository tree
Generated: 2026-05-24T18:25:09
Commit: 04adfbdb5a6b34d2969d67ac7e84c704c8e0915a

.
AOIA_CANONICAL_STRUCTURE_PLAN.md
AOIA_CONTAMINATION_REPORT.md
AOIA_DEPENDENCY_GRAPH.md
AOIA_MEMORY_ONTOLOGY.md
AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md
AOIA_RUNTIME_MAP.md
AOIA_TRANSITIONAL_COMPONENTS.md
AUTHORITY_SCOPE.md
CONTRADICTION_SEMANTICS.md
CURRENT_MEMORY_FLOW.md
FILESYSTEM_ONTOLOGY_LAYOUT.md
MEMORY_BOUNDARY_ANALYSIS.md
MEMORY_LAYER_DECOMPOSITION.md
MHLM_MHSR/
  case_studies/
    anti_hallucination_epi_app/
      README.md
      architecture/
        DEPENDENCY_BOUNDARY_ANALYSIS.md
        MEMORY_DOMAIN_SPLIT_PLAN.md
        contracts/
          RUNTIME_SAFETY_CONTRACTS.md
        enforcement/
          ENFORCEMENT_LAYER_DESIGN.md
      archive/
        AOIA_MASTER_LIBRARY/
          AOIA_Master_Library.pdf
          MASTER_INDEX.md
      contradictions/
        CONTRADICTION_TAXONOMY.md
      governance/
        GOVERNANCE_MODEL.md
        audit/
        authority/
        policies/
        review/
        risk_models/
      lineage/
        LINEAGE_POLICY.md
        decisions/
        events/
        sessions/
      prompts/
        PROMPT_ARCHIVE_POLICY.md
        normalized/
        raw/
      provenance/
        PROVENANCE_MODEL_PREP.md
      reports/
        architecture/
        forensic/
        governance/
        normalized/
        raw_provider/
          claude/
            MANIFEST.md
          codex/
            MANIFEST.md
          deepseek/
            MANIFEST.md
          gemini/
            MANIFEST.md
          kimi/
            MANIFEST.md
          unknown/
            MANIFEST.md
        synthesis/
      unclassified/
        UNCLASSIFIED_MANIFEST.md
    lsc_neutrino/
      README.md
      archive/
      contradictions/
      lineage/
        decisions/
        events/
        sessions/
      prompts/
        normalized/
        raw/
      provenance/
      reports/
        normalized/
        raw_provider/
        synthesis/
  docs/
  framework/
    governance/
    methodology/
      contradiction_policy.md
      evidence_policy.md
      inclusion_rules.md
      lineage_policy.md
    schemas/
      artifact.schema.json
      case_study_manifest.schema.json
      lineage_event.schema.json
      provenance_record.schema.json
      report.schema.json
    taxonomy/
      case_studies.yml
      legacy_aliases.yml
      model_aliases.yml
  imports/
    git_bundles/
    provider_exports/
      normalized/
      raw/
    repo_snapshots/
MUTABLE_STATE_ISOLATION_PLAN.md
ORCHESTRATION_REMNANT_AUDIT.md
PROVENANCE_FOUNDATION.md
README.md
ROADMAP.md
ROUTING_AUTHORITY_ANALYSIS.md
archive/
  quarantine/
    README.md
contradictions/
  README.md
docs/
  ADR/
    ADR-001-deterministic-routing.md
    ADR-002-three-depth-model.md
    ADR-003-local-first-execution.md
    ADR-004-no-runtime-learning.md
    ADR-005-fail-fast-philosophy.md
  ARCHITECTURE.md
  CONSTRAINTS.md
  FULL_PROJECT_TREE.txt
  GIT_HISTORY_CONTINUATION_PLAN.md
  KNOWLEDGE_PACK_RULES.md
  KNOWLEDGE_PACK_SPEC.md
  LINEAGE_MAP.md
  LINUX_ENGINEERING_LIBRARY.md
  LINUX_ENGINEERING_LIBRARY_REPORT.md
  NON_GOALS.md
  PHASE1_COMPLETE_REPORT.md
  PHASE1_POSTCHECK.md
  PHASE1_STRUCTURE_REPORT.md
  PHASE2_DUPLICATION_SCAN.md
  PHASE2_MIGRATION_REPORT.md
  PHASE2_UNCLASSIFIED_ITEMS.md
  PHASE3_DEPENDENCY_RISKS.md
  PHASE3_GOVERNANCE_PREP_REPORT.md
  PHASE3_RUNTIME_PREP_STATUS.md
  PRE_PHASE1_CONFLICT_SCAN.md
  README.md
  REPOSITORY_CONSTITUTION.md
  REPOSITORY_STATE_REPORT.md
  REPO_STRUCTURE.md
  RHCSA_ENGINE_REVIEW.md
  RUNTIME_BOUNDARY.md
  TAXONOMY_NORMALIZATION_REPORT.md
  TEST_CONSTITUTION.md
  TRANSFER_CONTENT_REPORT.txt
  adr/
    0001-keep-aoia-isolated.md
    0002-minimal-deterministic-router-skeleton.md
    0003-immutable-startup-configuration.md
    0004-stdout-only-plain-text-logging.md
    0005-test-constitution-determinism-first.md
    README.md
  architecture/
    AOIA_MEMORY_MODEL.md
    FORBIDDEN_MEMORY_FLOWS.md
    MEMORY_LAYER_ACCESS_MATRIX.md
  checkpoints/
    2026-05-23/
      AOIA_DAILY_CHECKPOINT.md
      NEXT_ACTIONS.md
  forensic-runtime-audit/
    CANONICAL_REFACTOR_PREP.md
    CURRENT_RUNTIME_TOPOLOGY.md
    MEMORY_CONTAMINATION_MAP.md
    RUNTIME_BOUNDARY_VIOLATIONS.md
  linux-engineering/
    README.md
  refactor/
    CANONICAL_AUTHORITY_GRAPH.md
    MEMORY_AUTHORITY_BOUNDARIES.md
    MEMORY_CONTAMINATION_GRAPH.md
    MEMORY_DEPENDENCY_GRAPH.md
    MEMORY_SPLIT_PLAN.md
  reports/
    FINAL_URL_HANDOFF_PATCH.md
    PHASE_1A_GIT_VALIDATION.md
    PHASE_2B_ROUTING_BOUNDARY.md
governance/
  README.md
memory/
  README.md
provenance/
  README.md
reports/
  linux-engineering/
    rhcsa_existing_state_audit.md
retrieval/
  README.md
runtime/
  adaptive_routing/
    aoia_config.json
    circadian_router.py
    config_loader.py
    deterministic_router.py
    dvm_research.md
    environment/
      environment_router.py
      network_patterns.md
      traffic_profiles.json
    epistemic_kernel.py
    routing_modes.json
    stdout_logger.py
  commands/
    __init__.py
    base.py
    local_commands.py
  contradiction_registry.json
  install.sh
  knowledge/
    README.md
    __init__.py
    bash/
      README.md
      skrypty-bash-podstawy.md
      wyszukiwanie-i-filtrowanie-tekstu.md
      zaawansowane-narzdzia-tekstowe.md
      zmienne-rodowiskowe-i-powoka.md
    candidates/
      candidate_command_index.json
      candidate_commands.csv
    canonical/
      rhcsa_commands.json
    command_graph.json
    context/
      context_pack.json
    examples/
      ls-command.json
      rm-recursive-force.json
      systemctl-status.json
    extracted/
      linux_master_library_v1.md
      linux_master_library_v1.txt
    filesystem/
      README.md
      archiwizacja-i-kompresja.md
      edytor-vim.md
      nawigacja-po-systemie-plikow.md
      operacje-na-plikach-i-katalogach.md
      przegldanie-zawartoci-plikow.md
      wyszukiwanie-plikow.md
    index/
      command_index.json
      command_index_template.csv
    injection/
      injected_context.json
    lvm/
      README.md
      lvm-logical-volume-manager.md
    manifests/
      library_manifest.yaml
    networking/
      README.md
      nfs-i-autofs.md
      samba-i-nfs-klient.md
      sie-konfiguracja-i-diagnostyka.md
      ssh-i-dostp-zdalny.md
      zapora-ogniowa-firewalld.md
    parsed/
      rhcsa_sections.json
    permissions/
      README.md
      uprawnienia-i-wasno-plikow.md
    podman/
      README.md
      kontenery-podman.md
    provenance/
      PROVENANCE_POLICY.md
    raw/
      rhcsa_raw.txt
    reports/
      category_distribution.md
      deduplication_report.md
      parsing_quality_report.md
      retrieval_engine_report.md
    rhcsa_engine.py
    schema/
      command.schema.json
    selinux/
      README.md
      selinux.md
    source/
      RHCSA_Command_Library (1).pdf
      linux_master_library_v1.pdf
    storage/
      README.md
      przechowywanie-danych-dyski-i-partycje.md
      systemy-plikow-i-montowanie.md
      zarzdzanie-dyskami-raid.md
    systemd/
      README.md
      boot-i-grub.md
      cron-i-harmonogramowanie-zada.md
      systemd-i-zarzdzanie-usugami.md
      zarzdzanie-pakietami-dnf-rpm.md
    tools/
      CANONICAL_BUILDER_README.md
      CONTEXT_PACK_README.md
      INDEX_BUILDER_README.md
      INJECTION_LAYER_README.md
      README.md
      SECTION_PARSER_README.md
      candidate_index_loader.py
      canonical_builder.py
      context_injector.py
      context_pack_builder.py
      index_builder.py
      markdown_kb_builder.py
      pdf_extract.py
      section_parser.py
    troubleshooting/
      README.md
      diagnostyka-i-narzdzia-systemowe.md
      dodatkowe-narzdzia-administracyjne.md
      informacje-o-systemie.md
      logowanie-i-monitorowanie-systemu.md
      zarzdzanie-procesami.md
    users/
      README.md
      zarzdzanie-grupami.md
      zarzdzanie-uytkownikami.md
    validator/
      __init__.py
      validation_report.md
      validation_rules.py
      validator.py
  main.py
  memory/
    __init__.py
    gemma_worker_memory.py
    hats/
      coding.json
      linux.json
      research.json
    rhcsa_context.py
  obsidian_vault/
    .obsidian/
      app.json
    00_START_HERE.md
    Daily/
      2026-05-23.md
    Evidence/
      20260523_204053_498246.md
      20260523_204122_715088.md
      20260523_204427_843537.md
      20260523_204557_588315.md
    Inbox/
    Knowledge/
    Logs/
    Projects/
    Prompts/
    Reasoning/
      20260523_204053_498246.md
      20260523_204122_715088.md
      20260523_204427_843537.md
      20260523_204557_588315.md
    Sessions/
    Templates/
  orchestrator/
    __init__.py
    gemini_gemma.py
    knowledge_router.py
  project_scan.json
  prompts/
    system_prompt.txt
  provenance_registry.json
  providers/
    __init__.py
    aureon_provider.py
    base.py
    config.py
    gemini_provider.py
    gemma_provider.py
    openai_compatible.py
  requirements.txt
  retrieval/
    __init__.py
    linux/
      __init__.py
      provenance_attach.py
      query_normalizer.py
      retrieval_engine.py
      scoring.py
  router/
    __init__.py
    local_router.py
  run.sh
  run_web.sh
  state/
    agent_state.json
    model_config.json
    providers.json
    token_savings_report.json
  tools/
    __init__.py
    browser_tools.py
    build_rhcsa_library.py
    epistemic_registry.py
    executor.py
    filesystem_tools.py
    memory.py
    memory_hats.py
    project_scanner.py
    rhcsa_search.py
    shell_tools.py
    system_info.py
    validator.py
    web_reader.py
  webapp.py
state/
  model_config.json
  providers.json
tests/
  test_aoia_determinism.py
  test_epistemic_kernel.py
  test_epistemic_registry.py
  test_epistemic_safeguards.py
  test_executor_containment.py
  test_knowledge_validator.py
  test_linux_retrieval.py
  test_main.py
  test_rhcsa_retrieval.py
  test_routing_boundary.py
web/

```
