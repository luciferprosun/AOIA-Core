# GT2 28.05 Boot Fix Report

Date: 2026-05-28
Repository: `/home/l/Desktop/AOIA-Core`
Canonical URL: `https://github.com/luciferprosun/AOIA-Core`
Branch: `main`
HEAD: `ee6f64a56b69ab87b4b04c2c8e46e312f41711ba`

## Scope

GT2 was a limited stabilization step. No cleanup sweep, archive operation, provenance redesign, RHCSA library expansion, AOIA-Nano extraction, commit, or push was performed.

## Preflight

Initial status:

```text
## main...origin/main
?? docs/audit/
```

The only pre-existing dirty state was the expected untracked `docs/audit/` directory from GT1 analysis reports. No unexpected runtime modifications were present, so GT2 continued.

## Boot Blockers Found

| Blocker | File / line area | Severity | Fix applied | Safe for next prompt |
| --- | --- | --- | --- | --- |
| Runtime state, memory, logs, screenshots, and Obsidian vault initialized inside checkout. | `runtime/tools/memory.py` | High | Redirected generated paths to `AOIA_HOME` or `~/.local/state/aoia/<checkout-id>/runtime`. | Yes |
| Provider model and provider-chain state written under checkout `state/`. | `runtime/providers/config.py` | Medium | Redirected provider state through same runtime state helper. | Yes |
| Knowledge-router token savings report written under checkout `state/`. | `runtime/orchestrator/knowledge_router.py`, `runtime/commands/local_commands.py` | Medium | Redirected report path to runtime state helper and made `/rhcsa savings` read the router path when available. | Yes |
| Memory hats wrote active hat state under checkout `state/` and could create runtime hat files under checkout `memory/`. | `runtime/tools/memory_hats.py` | Medium | Redirected memory hats to runtime state helper. | Yes |
| TUI tests failed import when optional dependency `textual` was absent. | `tests/test_tui_phase1.py`, `tests/test_tui_phase2.py` | Medium | Added module-level `unittest.SkipTest` guard for missing `textual`. | Yes |
| Hardcoded desktop default for SCEMDA zip. | `runtime/commands/local_commands.py` | Low | Changed default to `~/.local/share/aoia/kimi agetn..zip`; tests can still patch it. | Yes |

## Files Modified

| File | Reason | Patch category | Risk | Rollback | Affected tests |
| --- | --- | --- | --- | --- | --- |
| `runtime/runtime_paths.py` | Central compatibility helper for local writable runtime state. | Additive shim | Low | Delete file and revert callers. | Runtime boot, provider, memory tests |
| `runtime/tools/memory.py` | Stop generated memory/log/vault state from writing into checkout by default. | Startup/runtime wiring | Medium | Revert file. | `test_main`, `test_executor_containment`, memory/evidence tests |
| `runtime/providers/config.py` | Stop provider config writes into checkout. | Runtime state isolation | Medium | Revert file. | provider manager tests |
| `runtime/orchestrator/knowledge_router.py` | Stop token report writes into checkout. | Runtime state isolation | Low | Revert file. | router contract tests |
| `runtime/tools/memory_hats.py` | Stop active hat/runtime hat writes into checkout. | Runtime state isolation | Low | Revert file. | main/status/hat-adjacent tests |
| `runtime/commands/local_commands.py` | Remove hardcoded Desktop default and read token report from runtime state. | Compatibility patch | Low | Revert file. | `test_main`, retrieval facade contract |
| `tests/test_tui_phase1.py` | Treat missing `textual` as optional dependency skip. | Test environment guard | Low | Revert file. | TUI phase 1 tests |
| `tests/test_tui_phase2.py` | Treat missing `textual` as optional dependency skip. | Test environment guard | Low | Revert file. | TUI phase 2 tests |
| `tests/test_main.py` | Assert provider config through manager path, not repo-local state. | Test update matching state isolation | Low | Revert file. | provider model switch test |

## Tests Executed

```bash
python -m compileall -q runtime tests
python3 -m compileall -q runtime tests
PYTHONPATH=runtime:. python -m pytest -v
PYTHONPATH=runtime:. python3 -m pytest -v
PYTHONPATH=runtime:. python3 -m unittest discover -s tests -v
PYTHONPATH=runtime:. python3 -m unittest -v \
  tests.test_append_only_provenance \
  tests.test_provenance_verification \
  tests.test_provenance_readout \
  tests.test_aoia_determinism \
  tests.test_retrieval_facade_contract \
  tests.test_rhcsa_retrieval \
  tests.test_executor_containment \
  tests.test_evidence_write_contract
```

Results:

- `python`: unavailable (`/bin/bash: line 1: python: command not found`)
- `python3 -m compileall -q runtime tests`: PASS
- `pytest`: unavailable (`No module named pytest`)
- Full `unittest` fallback: PASS, 145 tests, 4 skipped
- Focused core suite: PASS, 52 tests

Skipped tests:

- 2 Playwright browser tests because Playwright is not installed.
- 2 TUI modules because optional dependency `textual` is not installed.

## Deterministic Behavior Impact

Deterministic router, immutable config loader, RHCSA retrieval, provenance chain verification, validator protections, and executor containment all remain passing. Runtime state directory naming now includes a hash of the checkout path so parallel clones and temp test checkouts do not collide under `~/.local/state/aoia`.

## Runtime Behavior Impact

Generated runtime state now defaults to:

```text
~/.local/state/aoia/<checkout-name>-<path-hash>/runtime/
```

Operators may override this with:

```text
AOIA_HOME=/custom/path
```

No provenance implementation, RHCSA canonical assets, retrieval logic, router logic, governance doctrine, or NON_GOALS doctrine was changed.

## Core Survival Check

| Core area | Status |
| --- | --- |
| Provenance append-only logic | PASS |
| Provenance verification/readout | PASS |
| Deterministic router | PASS |
| Immutable config loader | PASS |
| RHCSA retrieval | PASS |
| Validator/evidence protections | PASS |
| Bounded execution rules | PASS |
| NON_GOALS doctrine | Unchanged |

## Remaining Risks

- `python` command is absent; this environment requires `python3` or a symlink/venv outside this patch.
- `pytest` is absent; project validation currently relies on `unittest` fallback.
- Playwright remains optional and unavailable in this environment.
- `textual` remains optional and unavailable; tests now skip cleanly instead of failing import.
- Existing tracked runtime artifacts still remain in the repo until GT3/GT4; GT2 only prevents new default writes into the checkout.
- Orchestrator/Gemini/Gemma code remains present by design; GT2 did not archive or remove it.

## Next Recommended GT Phase

`GT3 28.05 - Move Generated Runtime State Out Of Repo And Update .gitignore`

GT3 should address tracked/generated runtime artifacts and ignore policy. It should not archive stale docs or split RHCSA yet unless explicitly scoped.
