# GT3 28.05 Runtime State Gitignore Report

Date: 2026-05-28
Repository: `/home/l/Desktop/AOIA-Core`
Canonical URL: `https://github.com/luciferprosun/AOIA-Core`
Branch: `main`
HEAD: `742555b checkpoint: deadline save1`

## Scope

This GT3 pass only isolates generated runtime state from the checkout and updates ignore rules. It does not change provenance logic, retrieval logic, router behavior, memory architecture, or RHCSA canonical assets.

## Git Status Before

Initial state for this pass:

```text
## main...origin/main [ahead 1]
M  .gitignore
D  runtime/contradiction_registry.json
D  runtime/logs/commands/20260523_204142_154127.json
D  runtime/logs/commands/20260523_204209_952302.json
D  runtime/logs/commands/20260523_204413_761373.json
D  runtime/logs/commands/20260523_204656_215481.json
D  runtime/logs/commands/20260523_205646_331909.json
D  runtime/logs/commands/20260523_205724_366915.json
D  runtime/logs/commands/20260523_210843_894310.json
D  runtime/logs/commands/20260523_211753_760018.json
D  runtime/logs/errors/error_20260523_204143_602420.json
D  runtime/logs/errors/error_20260523_204146_642444.json
D  runtime/logs/errors/error_20260523_204442_849021.json
D  runtime/logs/errors/error_20260523_204446_308012.json
D  runtime/logs/sessions/session_20260523_204053_498246.jsonl
D  runtime/logs/sessions/session_20260523_204122_715088.jsonl
D  runtime/logs/sessions/session_20260523_204427_843537.jsonl
D  runtime/logs/sessions/session_20260523_204557_588315.jsonl
D  runtime/memory/evidence_memory.jsonl
D  runtime/memory/hats/coding.json
D  runtime/memory/hats/linux.json
D  runtime/memory/hats/research.json
D  runtime/memory/history.jsonl
D  runtime/memory/reasoning_trace.jsonl
D  runtime/obsidian_vault/.obsidian/app.json
D  runtime/obsidian_vault/00_START_HERE.md
D  runtime/obsidian_vault/Daily/2026-05-23.md
D  runtime/obsidian_vault/Evidence/20260523_204053_498246.md
D  runtime/obsidian_vault/Evidence/20260523_204122_715088.md
D  runtime/obsidian_vault/Evidence/20260523_204427_843537.md
D  runtime/obsidian_vault/Evidence/20260523_204557_588315.md
D  runtime/obsidian_vault/Reasoning/20260523_204053_498246.md
D  runtime/obsidian_vault/Reasoning/20260523_204122_715088.md
D  runtime/obsidian_vault/Reasoning/20260523_204427_843537.md
D  runtime/obsidian_vault/Reasoning/20260523_204557_588315.md
D  runtime/obsidian_vault/Sessions/20260523_204053_498246.jsonl
D  runtime/obsidian_vault/Sessions/20260523_204122_715088.jsonl
D  runtime/obsidian_vault/Sessions/20260523_204427_843537.jsonl
D  runtime/obsidian_vault/Sessions/20260523_204557_588315.jsonl
D  runtime/project_scan.json
D  runtime/state/agent_state.json
D  runtime/state/model_config.json
D  runtime/state/providers.json
D  runtime/state/token_savings_report.json
```

## Generated Artifact Inventory

Tracked generated runtime artifacts found in the checkout:

| Group | Count | Examples |
| --- | ---: | --- |
| Runtime logs | 16 | `runtime/logs/commands/*.json`, `runtime/logs/errors/*.json`, `runtime/logs/sessions/*.jsonl` |
| Runtime memory data | 6 | `runtime/memory/evidence_memory.jsonl`, `runtime/memory/history.jsonl`, `runtime/memory/reasoning_trace.jsonl` |
| Memory hats | 3 | `runtime/memory/hats/coding.json`, `runtime/memory/hats/linux.json`, `runtime/memory/hats/research.json` |
| Obsidian vault projection | 15 | `runtime/obsidian_vault/.obsidian/app.json`, `runtime/obsidian_vault/Evidence/*`, `runtime/obsidian_vault/Reasoning/*` |
| State JSON | 4 | `runtime/state/agent_state.json`, `runtime/state/model_config.json`, `runtime/state/providers.json`, `runtime/state/token_savings_report.json` |
| Scan artifact | 1 | `runtime/project_scan.json` |
| Registry artifact | 1 | `runtime/contradiction_registry.json` |

Ignored but not tracked:

- `runtime/.venv/`
- `runtime/**/__pycache__/`
- `scripts/**/__pycache__/`
- `tests/**/__pycache__/`

## .gitignore Changes

Added ignore rules only for generated local/runtime artifacts:

```gitignore
/runtime/logs/
/runtime/obsidian_vault/
/runtime/screenshots/
/runtime/state/
/runtime/project_scan.json
/runtime/contradiction_registry.json
/runtime/memory/*.jsonl
/runtime/memory/hats/*.json
```

## Tracked Artifacts And Index Handling

The tracked generated files were identified as safe runtime outputs, not source. The worktree was restored after the earlier removal pass so the files remain on disk.

The exact untrack-only command that would perform the same index cleanup without touching disk is:

```bash
git rm --cached -r runtime/contradiction_registry.json runtime/logs runtime/memory/evidence_memory.jsonl runtime/memory/hats runtime/memory/history.jsonl runtime/memory/reasoning_trace.jsonl runtime/obsidian_vault runtime/project_scan.json runtime/state
```

Current index state already reflects removals for the same generated files, and no source files were changed.

## Validation

Commands run:

```bash
python3 -m compileall -q runtime tests
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_memory_layer_isolation_smoke tests.test_evidence_boundary tests.test_evidence_write_contract tests.test_executor_containment tests.test_main
```

Results:

- `compileall`: PASS
- `unittest`: PASS, `38` tests run, `2` skipped
- `Playwright`-backed tests: skipped because Playwright is not installed in this environment

## Safety Confirmation

- No runtime source code was rewritten.
- No provenance implementation was changed.
- No retrieval layer was redesigned.
- No RHCSA canonical assets were modified.
- No commit or push was performed.
- Runtime files remain on disk; only the repository index is being cleaned up for generated artifacts.

## Remaining Blockers

None for this GT3 scope.

The only remaining non-issue is that the cleanup is not committed yet, so the repository history still needs a later commit if you want the untracking to become permanent.

## Rollback

To undo the ignore-rule change and restore the previous index behavior:

```bash
git restore --staged .gitignore
git checkout -- .gitignore
```

To restore the generated runtime files into the index again:

```bash
git checkout -- runtime/contradiction_registry.json runtime/logs runtime/memory/evidence_memory.jsonl runtime/memory/hats runtime/memory/history.jsonl runtime/memory/reasoning_trace.jsonl runtime/obsidian_vault runtime/project_scan.json runtime/state
```

## Recommended Next GT Step

`GT4 28.05 - Archive Stale Docs And Forensic Exports`

That step is separate from boot/runtime stabilization and should not be mixed into this pass.
