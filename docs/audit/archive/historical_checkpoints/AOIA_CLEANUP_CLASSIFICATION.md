# AOIA Cleanup Classification

Date: 2026-05-28
Scope: classify only; no removal.

## A. Must Keep

| Path | Reason | Evidence | Risk | Recommended action | Tests affected |
| --- | --- | --- | --- | --- | --- |
| `runtime/tools/provenance.py` | Append-only provenance kernel. | Provenance tests pass; hash chain implemented. | Low | Keep and make AOIA-Nano core. | `test_append_only_provenance`, `test_provenance_verification` |
| `runtime/tools/provenance_readout.py` | Deterministic verification CLI. | Readout tests pass. | Low | Keep. | `test_provenance_readout` |
| `tests/test_append_only_provenance.py` | Protects append-only behavior. | Passes. | Low | Keep. | N/A |
| `tests/test_provenance_verification.py` | Protects tamper detection. | Passes. | Low | Keep. | N/A |
| `tests/test_provenance_readout.py` | Protects readout behavior. | Passes. | Low | Keep. | N/A |
| `runtime/adaptive_routing/deterministic_router.py` | Deterministic local routing primitive. | Tiny pure function; tests pass. | Low | Keep. | `test_aoia_determinism` |
| `runtime/adaptive_routing/config_loader.py` | Immutable startup config loader. | Frozen dataclass and `MappingProxyType`. | Low | Keep. | `test_aoia_determinism` |
| `runtime/retrieval/facade.py` | Read-only RHCSA retrieval boundary. | Facade contract tests pass. | Low | Keep. | `test_retrieval_facade_contract` |
| `runtime/retrieval/linux/` | Canonical retrieval implementation. | Retrieval tests pass. | Medium | Keep and narrow public API through facade. | RHCSA/retrieval tests |
| `runtime/knowledge/canonical/` | Canonical RHCSA runtime knowledge. | Retrieval uses canonical commands. | Low | Keep in AOIA-Core. | RHCSA tests |
| `runtime/knowledge/index/` | Runtime index. | Retrieval depends on index. | Low | Keep in AOIA-Core. | RHCSA tests |
| `runtime/knowledge/manifests/` | Knowledge manifest. | Required for hash-pinned future plan. | Low | Keep in AOIA-Core. | Knowledge tests |
| `runtime/knowledge/schema/` | Runtime schema contract. | Validator and knowledge structure depend on schema. | Low | Keep. | `test_knowledge_validator` |
| `runtime/tools/executor.py` | Bounded execution rules. | Executor containment tests pass. | Medium | Keep, then narrow to AOIA-Nano executor. | `test_executor_containment` |
| `docs/governance/` | Governance contracts and test policy. | Matches current passing contracts. | Low | Keep. | Governance/provenance tests |
| `docs/NON_GOALS.md` | Non-goals doctrine. | Required public boundary. | Low | Keep. | Documentation only |
| `tests/test_no_direct_rhcsa_search_imports.py` | Protects retrieval boundary. | Passes. | Low | Keep. | N/A |

Must-keep count: 17.

## B. Safe To Archive

| Path | Reason | Evidence | Risk | Recommended action | Tests affected |
| --- | --- | --- | --- | --- | --- |
| `reports/forensic_export/` | Generated PDF/HTML/source export snapshot inside repo. | Contains duplicate `source_export` and PDFs/HTML. | Medium | Archive outside runtime repo. | None expected. |
| `docs/forensic-runtime-audit/` | Historical audit reports. | Already finalized Phase 0 records. | Low | Move to archive docs package. | None expected. |
| `runtime/reports/` | Generated runtime reports. | Stabilization/checkpoint outputs, not runtime code. | Low | Archive. | None expected. |
| Root `AOIA_*`, `MEMORY_*`, `ROUTING_*`, `PROVENANCE_FOUNDATION.md` reports | Stale phase/root reports. | Duplicate docs live under `docs/` and forensic export. | Medium | Archive after inventory. | None expected. |
| `docs/PHASE*.md`, `docs/PRE_PHASE1_CONFLICT_SCAN.md` | Phase reports. | Historical cleanup docs. | Low | Archive under dated history. | None expected. |
| `docs/reports/AOIA_RESTART_PRODUCTION_REPORT.pdf` | Binary export in docs. | Generated PDF. | Low | Archive externally. | None expected. |

## C. Safe To Remove After Confirmation

| Path | Reason | Evidence | Risk | Recommended action | Tests affected |
| --- | --- | --- | --- | --- | --- |
| `__pycache__/` directories | Generated Python bytecode. | Recreated by compile/tests. | Low | Remove after confirmation and ensure ignored. | None. |
| `runtime/project_scan.json` | Generated scan artifact. | Project scanner writes reports. | Low | Remove after confirmation if reproducible. | None expected. |
| Duplicate `state/model_config.json` and `state/providers.json` | Top-level mutable state duplicates runtime state. | Runtime also has `runtime/state`. | Medium | Remove or move after state policy. | Provider tests may need fixtures updated. |
| `runtime/knowledge/reports/` | Generated build reports. | Build pipeline outputs. | Low | Move to knowledge repo or remove after archive. | None expected. |

## D. Move Out Of Runtime Repo

| Path | Reason | Evidence | Risk | Recommended action | Tests affected |
| --- | --- | --- | --- | --- | --- |
| `runtime/logs/` | Generated session/command/error logs. | Created by `MemoryStore` and executor. | High | Move to external local runtime home. | Memory/executor tests need temp path update. |
| `runtime/memory/*.jsonl` | Mutable runtime memory. | `MemoryStore` writes JSONL at runtime. | High | Move out; leave schema/tests only. | Memory/evidence tests. |
| `runtime/obsidian_vault/` | Runtime-generated Obsidian projection. | `MemoryStore` creates vault and notes. | High | Move out or derive from ledger. | `test_memory_store_initializes_obsidian_vault`. |
| `runtime/state/agent_state.json` | Generated runtime state. | `MemoryStore.save()` writes it. | High | Move out. | Memory tests. |
| `runtime/state/token_savings_report.json` | Generated router metrics. | Knowledge router report path. | Medium | Move out or fold into ledger. | Router tests if path asserted. |
| `runtime/knowledge/raw/` | Raw source input. | Knowledge build artifact. | Medium | Move to `aoia-knowledge-rhcsa`. | None if canonical kept. |
| `runtime/knowledge/extracted/` | Extracted input. | Build pipeline artifact. | Medium | Move to knowledge repo. | None if canonical kept. |
| `runtime/knowledge/source/` | Source PDFs. | Binary knowledge inputs. | Medium | Move to knowledge repo. | None if canonical kept. |
| `runtime/knowledge/parsed/` | Parser output. | Build pipeline artifact. | Medium | Move to knowledge repo. | None if canonical kept. |
| `runtime/knowledge/candidates/` | Candidate outputs/review queues. | Triage artifacts. | Medium | Move to knowledge repo or review area. | Candidate triage tests need fixture strategy. |
| `runtime/knowledge/tools/` | Build pipeline tooling. | Builders/extractors/promoters. | Medium | Move to knowledge repo. | Knowledge validator/build tests. |
| `runtime/knowledge/validator/` | Build validator. | Source pipeline component. | Medium | Move to knowledge repo after AOIA-Core consumes packaged manifest. | `test_knowledge_validator`. |

## E. Needs Human Review

| Path | Reason | Evidence | Risk | Recommended action | Tests affected |
| --- | --- | --- | --- | --- | --- |
| `MHLM_MHSR/` | MHLM content inside AOIA-Core runtime repo boundary. | Separate theory/archive domain. | High | Human review; likely move out. | None expected but provenance docs may cite. |
| `runtime/orchestrator/` | Dead or experimental Gemini/Gemma delegation. | Main can enable orchestrator, but default is off. | High | Human review; archive if not core. | Orchestrator/local command tests may need update. |
| `runtime/adaptive_routing/circadian_router.py` and `dvm_research.md` | Circadian/DVM routing experiments. | Not AOIA-Nano core. | Medium | Human review; archive. | Determinism tests likely unaffected. |
| `runtime/adaptive_routing/environment/` | Environment routing experiments. | Network/traffic profile files. | Medium | Human review; archive. | None expected. |
| `docs/ADR/` and `docs/adr/` | Duplicated ADR trees. | Two ADR directory conventions. | Medium | Choose one canonical ADR path. | Docs only. |
| `runtime/providers/gemini_provider.py`, `gemma_provider.py`, `openai_compatible.py` | Provider adapters exceed deterministic kernel. | Provider manager supports cloud providers. | Medium | Keep only one real provider after MVP; archive extras. | Provider tests. |
| `web/` and `tui/` | UI surfaces outside provenance kernel. | TUI tests fail without optional `textual`. | Medium | Human review; exclude from AOIA-Nano core package initially. | TUI tests. |

Cleanup candidate count: 31.
