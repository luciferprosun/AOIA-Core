# AOIA Boot Blockers

Date: 2026-05-28
Scope: inspect `runtime/main.py` and entrypoint-adjacent imports only.

## Summary

The runtime can import and pass compile checks, but the boot path still initializes broad mutable runtime surfaces inside the repository tree. For AOIA-Nano, these are blockers because a provenance kernel should be able to start with deterministic config, read-only canonical knowledge, and an externalized run ledger.

| Blocker | File / line | Severity | Recommended fix | Safe for next prompt |
| --- | --- | --- | --- | --- |
| Main runtime imports and initializes memory monolith at startup. | `runtime/main.py:32-34`, `runtime/main.py:157-160` | High | Split runtime state initialization from deterministic kernel boot; allow provenance/router/retrieval checks without creating memory/vault state. | Yes, prompt 2. |
| RHCSA context injection is imported directly into main boot path. | `runtime/main.py:26`, `runtime/main.py:205`, `runtime/main.py:687` | Medium | Keep RHCSA behind `runtime/retrieval/facade.py`; remove direct boot-time coupling from core kernel path. | Yes, prompt 2. |
| Gemini/Gemma orchestrator remains importable from main runtime. | `runtime/main.py:27`, `runtime/main.py:517-527`, `runtime/orchestrator/gemini_gemma.py` | High | Archive or isolate orchestrator behind non-default experimental entrypoint; exclude from AOIA-Nano MVP. | Later, prompt 5. |
| Gemma worker memory remains initialized at runtime startup. | `runtime/main.py:32`, `runtime/main.py:159`, `runtime/memory/gemma_worker_memory.py` | Medium | Move worker memory out of core boot or mark as archived orchestration support. | Later, prompt 5. |
| Runtime state writes into repo tree. | `runtime/tools/memory.py:55-70`, `runtime/tools/memory.py:139-160` | High | Redirect generated state/logs to external runtime home, e.g. `.aoia-runtime/` outside tracked source or ignored local state. | Yes, prompt 3. |
| Obsidian vault generated at runtime inside repo tree. | `runtime/tools/memory.py:73-126`, `runtime/tools/memory.py:261-293` | High | Move vault/session artifacts out of runtime repo; keep only schema/docs if needed. | Yes, prompt 3. |
| Provider manager creates provider config under repo `state`. | `runtime/providers/config.py:79`, `runtime/providers/config.py:198-205` | Medium | Treat provider state as local runtime config outside source repo. | Yes, prompt 3. |
| Hardcoded operator desktop path in command helper. | `runtime/commands/local_commands.py:19` | Medium | Replace with detected desktop path or remove legacy SCEMDA helper from AOIA-Nano. | Yes, prompt 2. |
| Browser/page snapshots write into memory dir. | `runtime/main.py:981-992` | Medium | Route snapshots to external runtime artifact dir and log through single ledger. | Yes, prompt 3. |
| Multiple event sinks fragment provenance. | `runtime/main.py:1010-1029`, `runtime/tools/memory.py:165-224`, `runtime/tools/provenance.py:55-93` | High | Introduce a single event ledger design before implementation; do not change now. | Later, prompt 8. |

## Non-Blockers To Keep

- `runtime/tools/provenance.py` imports cleanly and provides append-only hash chaining.
- `runtime/tools/provenance_readout.py` provides deterministic verification readout.
- `runtime/adaptive_routing/deterministic_router.py` is tiny and deterministic.
- `runtime/adaptive_routing/config_loader.py` returns immutable startup config via `MappingProxyType`.
- `runtime/retrieval/facade.py` is the correct boundary for RHCSA retrieval access.
