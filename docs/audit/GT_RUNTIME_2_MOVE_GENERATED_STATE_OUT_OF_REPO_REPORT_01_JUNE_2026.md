# GT-RUNTIME-2 Move Generated Runtime State Out Of Repo Report

Date: 2026-06-01

## Checkpoint

- Starting commit: `170e5d0 fix: reduce runtime boot side effects`
- GT-RUNTIME-1 tag: `gt-runtime-1-fix-boot-blockers-2026-06-01`
- Previous safepoint tag: `gt-runtime-restart-safepoint-2026-06-01`
- Working branch: `dev/gt-runtime-2-move-generated-state`
- Scope: Move Generated Runtime State Out Of Repo

## Files Inspected

- `runtime/runtime_paths.py`
- `runtime/tools/memory.py`
- `runtime/tools/memory_hats.py`
- `runtime/providers/config.py`
- `runtime/main.py`
- `runtime/tools/project_scanner.py`
- `runtime/tools/web_reader.py`
- `runtime/tools/executor.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/commands/local_commands.py`
- `.gitignore`
- `tests/test_memory_layer_isolation_smoke.py`
- `tests/test_evidence_boundary.py`
- `tests/test_evidence_write_contract.py`
- `tests/test_executor_containment.py`
- `tests/test_main.py`

## Files Changed

- `.gitignore`
- `runtime/tools/project_scanner.py`
- `runtime/tools/web_reader.py`
- `tests/test_main.py`
- `docs/audit/GT_RUNTIME_2_MOVE_GENERATED_STATE_OUT_OF_REPO_REPORT_01_JUNE_2026.md`

## Generated-State Paths Found

Current active runtime paths already use `runtime_state_dir(project_dir)`, which resolves to:

- `AOIA_HOME/<project-name>-<hash>/runtime/...` when `AOIA_HOME` is set
- `~/.local/state/aoia/<project-name>-<hash>/runtime/...` by default

Active generated-state paths found:

- runtime state: `runtime_state_dir(project_dir) / "state"`
- memory JSONL: `runtime_state_dir(project_dir) / "memory"`
- command logs: `runtime_state_dir(project_dir) / "logs" / "commands"`
- browser logs: `runtime_state_dir(project_dir) / "logs" / "browser"`
- session logs: `runtime_state_dir(project_dir) / "logs" / "sessions"`
- error logs: `runtime_state_dir(project_dir) / "logs" / "errors"`
- screenshots: `runtime_state_dir(project_dir) / "screenshots"`
- Obsidian projection: `runtime_state_dir(project_dir) / "obsidian_vault"`
- provider config: `runtime_state_dir(project_dir) / "state" / "model_config.json"`
- provider chain config: `runtime_state_dir(project_dir) / "state" / "providers.json"`
- token savings report: `runtime_state_dir(project_dir) / "state" / "token_savings_report.json"`
- memory hats: `runtime_state_dir(project_dir) / "memory" / "hats"`

Source-tree generated artifacts also exist as legacy ignored data:

- `runtime/logs/`
- `runtime/memory/*.jsonl`
- `runtime/memory/hats/*.json`
- `runtime/state/`
- `runtime/obsidian_vault/`
- `runtime/screenshots/`
- `runtime/project_scan.json`

## Path Redirections Made

1. Redirected project scan reports.
   - Before: `scan_project()` wrote `project_scan.json` into the scanned project root.
   - After: `scan_project()` writes to `runtime_state_dir(scanned_root) / "state" / "project_scan.json"`.
   - The returned `scan_report_path` behavior is preserved, but the file is no longer created in the scanned source tree.
2. Redirected web reader cache.
   - Before: `web_reader.py` created `cache/web` at import time relative to the current working directory.
   - After: cache files are created lazily under `aoia_state_home() / "web_cache"` only when `fetch_page()` requests a cache file.
3. Added ignore rules for local runtime/cache overrides.
   - `/.aoia_state/`
   - `/cache/`

## Tests Added

- `test_runtime_state_paths_follow_aoia_home`
- `test_agent_runtime_boot_does_not_create_source_tree_state_dirs`
- `test_scan_project_report_uses_runtime_state_not_project_root`
- `test_provider_manager_paths_follow_aoia_home`

These tests prove:

- Memory, state, logs, screenshots, and vault paths follow `AOIA_HOME`.
- Runtime boot does not create broad generated state directories inside the project source tree.
- Provider config paths follow the local runtime state home.
- Project scan reports are written to runtime state, not to the scanned project root.

## Intentionally Not Changed

- No existing runtime state directories were deleted.
- No legacy files under `runtime/logs`, `runtime/memory`, `runtime/state`, `runtime/obsidian_vault`, `runtime/screenshots`, or `runtime/project_scan.json` were removed.
- No provider API behavior was changed.
- No executor policy was changed.
- No provenance hash formats were changed.
- No RHCSA canonical data was changed.
- No command grammar data was changed.
- No Memory Hats semantics were changed.
- No GUI, TUI, or web features were added.
- No AOIA-Nano extraction was attempted.
- No package installs were run.
- No merge to `main` was performed.
- No push was performed.

## Validation Results

Baseline before changes:

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest -v tests.test_main tests.test_memory_layer_isolation_smoke tests.test_evidence_boundary tests.test_evidence_write_contract tests.test_executor_containment`: PASS, 41 tests run, 2 skipped
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 332 tests run, 4 skipped

After changes:

- `python3 -m compileall runtime tests`: PASS
- `PYTHONPATH=runtime:. python3 -m unittest -v tests.test_main tests.test_memory_layer_isolation_smoke tests.test_evidence_boundary tests.test_evidence_write_contract tests.test_executor_containment`: PASS, 45 tests run, 2 skipped
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: PASS, 336 tests run, 4 skipped

## Remaining Risks

- Legacy generated artifacts remain on disk in the source tree because this task explicitly avoided deletion. They are ignored and documented, but a later cleanup task should decide whether to archive or remove them.
- Some historical reports mention old `runtime/memory` and `runtime/obsidian_vault` paths. Those references were not rewritten because this task avoided docs cleanup and archive work.
- Knowledge-building tools still intentionally write knowledge corpus outputs under `runtime/knowledge` when explicitly run. That is outside runtime generated-state redirection and was not changed.

## Rollback Instructions

To roll back before commit, discard changes to the files listed in this report. To roll back after commit, revert the GT-RUNTIME-2 commit. Do not delete existing runtime state directories as part of rollback.

## Next Recommended Task

GT-RUNTIME-3 - Respond-message shell safety filter
