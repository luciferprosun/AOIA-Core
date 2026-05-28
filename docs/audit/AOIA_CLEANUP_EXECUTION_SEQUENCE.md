# AOIA Cleanup Execution Sequence

Date: 2026-05-28
Scope: future prompt plan only.

## Prompt 2: Fix Boot Blockers Only

Objective: allow deterministic kernel import/start without initializing broad mutable state or experimental orchestrators.

Files affected: `runtime/main.py`, `runtime/commands/local_commands.py`, `runtime/providers/config.py`, focused tests.

Tests to run:

```bash
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_main tests.test_runtime_router_contract_guard tests.test_routing_boundary
```

Commit message: `fix: isolate deterministic runtime boot path`

Rollback: revert the prompt 2 commit; rerun the same tests.

## Prompt 3: Move Generated Runtime State Out Of Repo

Objective: redirect `runtime/logs`, `runtime/memory`, `runtime/state`, `runtime/obsidian_vault`, and snapshots into an ignored/external runtime home.

Files affected: `runtime/tools/memory.py`, `runtime/providers/config.py`, `.gitignore`, tests.

Tests to run:

```bash
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_memory_layer_isolation_smoke tests.test_evidence_boundary tests.test_evidence_write_contract tests.test_executor_containment tests.test_main
```

Commit message: `fix: move generated runtime state out of source tree`

Rollback: revert commit and restore prior path behavior from git.

## Prompt 4: Archive Stale Docs And Forensic Exports

Objective: move historical reports/PDF/HTML exports out of active runtime repo paths.

Files affected: `reports/forensic_export/`, root phase docs, `docs/forensic-runtime-audit/`, `docs/reports/*.pdf`.

Tests to run:

```bash
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_provenance_readout tests.test_retrieval_facade_contract
```

Commit message: `docs: archive stale forensic and phase reports`

Rollback: revert commit; verify files restored.

## Prompt 5: Remove/Archive Dead Orchestrator, Circadian, Environment Systems

Objective: remove AOIA-Nano non-core orchestration experiments from runtime path after human confirmation.

Files affected: `runtime/orchestrator/`, `runtime/adaptive_routing/circadian_router.py`, `runtime/adaptive_routing/environment/`, command handlers/tests.

Tests to run:

```bash
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_main tests.test_routing_boundary tests.test_runtime_router_contract_guard tests.test_no_direct_rhcsa_search_imports
```

Commit message: `refactor: archive non-core orchestration experiments`

Rollback: revert commit; run import scanner test.

## Prompt 6: Unify ADR Structure

Objective: choose one ADR tree and archive the duplicate.

Files affected: `docs/ADR/`, `docs/adr/`, doc links.

Tests to run:

```bash
git status
rg -n "docs/ADR|docs/adr" docs README.md
```

Commit message: `docs: unify ADR structure`

Rollback: revert commit.

## Prompt 7: Prepare RHCSA Canonical Library Integration

Objective: keep only canonical/index/manifest in AOIA-Core and prepare external `aoia-knowledge-rhcsa` ownership for raw/build artifacts.

Files affected: `runtime/knowledge/`, retrieval tests, manifests.

Tests to run:

```bash
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_rhcsa_retrieval tests.test_linux_retrieval tests.test_retrieval_facade_contract tests.test_knowledge_validator tests.test_candidate_triage
```

Commit message: `refactor: separate RHCSA runtime pack from build artifacts`

Rollback: revert commit; verify retrieval tests.

## Prompt 8: Begin AOIA-Nano Runtime Extraction

Objective: create minimal AOIA-Nano package from provenance, config, router, retrieval facade, and bounded executor.

Files affected: new package path, pyproject, tests, docs.

Tests to run:

```bash
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_append_only_provenance tests.test_provenance_verification tests.test_provenance_readout tests.test_aoia_determinism tests.test_retrieval_facade_contract tests.test_executor_containment
```

Commit message: `feat: extract minimal AOIA-Nano provenance kernel`

Rollback: revert commit; source runtime remains intact.
