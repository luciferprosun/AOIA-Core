# GT-RUNTIME-1 Fix Boot Blockers Report

Date: 2026-06-01

## Checkpoint

- Starting commit: `5d76697 docs: add runtime restart safepoint`
- Safepoint tag: `gt-runtime-restart-safepoint-2026-06-01`
- Working branch: `dev/gt-runtime-1-fix-boot-blockers`
- Scope: Fix Boot Blockers Only

## Files Inspected

- `runtime/main.py`
- `runtime/commands/local_commands.py`
- `runtime/providers/config.py`
- `runtime/tools/memory.py`
- `runtime/tools/memory_hats.py`
- `runtime/memory/gemma_worker_memory.py`
- `runtime/runtime_paths.py`
- `tests/test_main.py`
- `tests/test_runtime_router_contract_guard.py`
- `tests/test_routing_boundary.py`
- `tests/test_aoia_determinism.py`

## Files Changed

- `runtime/main.py`
- `runtime/commands/local_commands.py`
- `runtime/providers/config.py`
- `runtime/tools/memory.py`
- `runtime/tools/memory_hats.py`
- `tests/test_main.py`
- `docs/audit/GT_RUNTIME_1_FIX_BOOT_BLOCKERS_REPORT_01_JUNE_2026.md`

## Boot Blockers Found

1. `AgentRuntime.__init__` eagerly initialized `MemoryStore` with default behavior, which created Obsidian vault artifacts, persisted `agent_state.json`, and appended a session-start vault note during runtime construction.
2. `AgentRuntime.__init__` eagerly initialized `MemoryHatStore` with default behavior, which created default memory hat files and active-hat state directories during boot.
3. `ProviderManager.__init__` created the runtime state config directory and wrote a default provider-chain file when `providers.json` was missing.
4. The experimental orchestrator path was already lazy: `AgentRuntime` sets `self.orchestrator = None`, and orchestration is only created by explicit `enable_orchestrator()` usage.
5. No hardcoded operator desktop path was changed in this pass. The inspected SCEMDA archive path points under user-local application data and was not a GT-RUNTIME-1 boot blocker.

## Changes Made

1. Added lazy Obsidian vault initialization support to `MemoryStore`.
   - New constructor flags: `initialize_vault`, `persist_on_init`, and `record_session_start`.
   - Default behavior remains unchanged for direct `MemoryStore(...)` construction.
   - Added `ensure_obsidian_vault()` for explicit vault creation before vault writes.
2. Updated `AgentRuntime` boot path to construct `MemoryStore` without vault initialization, initial persistence, or session-start vault note.
3. Updated `/vault` command to explicitly initialize the vault before returning the vault path.
4. Added lazy default initialization support to `MemoryHatStore`.
   - Default behavior remains unchanged for direct `MemoryHatStore(...)` construction.
   - `AgentRuntime` now constructs it with `initialize_defaults=False`.
   - Hat operations initialize defaults when actually used.
5. Removed boot-time provider state writes from `ProviderManager`.
   - Missing `providers.json` now uses the default provider chain in memory without writing the file.
   - `model_config.json` parent directories are created only when `switch_model()` persists a model selection.
6. Added focused tests for the new boot contract.
   - Runtime boot no longer creates the Obsidian vault until `/vault` is invoked.
   - Provider manager boot no longer writes state files, while explicit model switching still persists `model_config.json`.

## Intentionally Not Changed

- No runtime state directory migration was done.
- No `runtime/logs`, `runtime/memory`, `runtime/state`, or `obsidian_vault` paths were moved.
- No provider semantics were changed.
- No executor policy was changed.
- No provenance hash formats were changed.
- No RHCSA canonical data was changed.
- No command grammar corpus expansion was done.
- No GUI, TUI, or web features were added.
- No AOIA-Nano extraction was attempted.
- No package installs were run.
- No merge to `main` was performed.
- No push was performed.

## Validation Results

Baseline before changes:

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest -v tests.test_main tests.test_runtime_router_contract_guard tests.test_routing_boundary tests.test_aoia_determinism`: PASS, 47 tests run, 2 skipped
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 330 tests run, 4 skipped

After changes:

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest -v tests.test_main tests.test_runtime_router_contract_guard tests.test_routing_boundary tests.test_aoia_determinism`: PASS, 49 tests run, 2 skipped
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 332 tests run, 4 skipped

## Remaining Risks

- Runtime path construction still points at the existing generated-state layout. Moving generated runtime state out of the repository is intentionally deferred to GT-RUNTIME-2.
- Explicit memory, evidence, reasoning, and vault commands still initialize and write vault/runtime artifacts by design.
- Boot construction may still create directories through other runtime subsystems not changed in this prompt. This pass only removed the identified broad mutable state and provider writes from the deterministic boot path.

## Rollback Instructions

To roll back this work before commit, discard the working-tree changes for the files listed in this report. To roll back after commit, revert the GT-RUNTIME-1 commit. Do not delete runtime state directories as part of rollback.

## Next Recommended Task

GT-RUNTIME-2 - Move Generated Runtime State Out Of Repo
