# PHASE 0C - RUNTIME ROUTER CONTRACT GUARD REPORT

## 1. Feature Flag Behavior

Flag:

```text
AIOA_ENABLE_LINUX_RETRIEVAL_V1
```

Implemented in:

- `runtime/retrieval/feature_flags.py`

Behavior:

- Default: OFF
- Activation: explicit only
- Accepted true values: `1`, `true`, `yes`, `on`
- Accepted false values: `0`, `false`, `no`, `off`, empty string
- Invalid values do not activate retrieval
- `linux_retrieval_boundary()` returns `None` when OFF
- `linux_retrieval_boundary()` returns `retrieve_linux_knowledge` when ON

Important scope note:

The feature flag helper is intentionally not wired into `runtime/main.py` in Phase 0C. This avoids global runtime activation and keeps the router hook unchanged. The helper establishes a testable contract for the future runtime hook.

## 2. Modules Audited

Audited coordinator/router/runtime modules:

- `runtime/main.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/commands/local_commands.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/memory/rhcsa_context.py`

Checked for direct imports of:

- `tools.rhcsa_search`
- `knowledge.rhcsa_engine`
- deprecated retrieval APIs

Result:

- No direct deprecated retrieval imports found in audited coordinator/runtime modules.
- `runtime/main.py` does not import `retrieve_linux_knowledge`.
- `runtime/main.py` does not reference `AIOA_ENABLE_LINUX_RETRIEVAL_V1`.

## 3. Direct Imports Removed / Blocked

No new direct low-level imports were introduced.

Current canonical coordinator path:

```text
coordinator/router layer
  -> runtime.retrieval.facade.retrieve_linux_knowledge()
  -> runtime.retrieval.linux.retrieval_engine.LinuxRetrievalEngine
  -> runtime.tools.rhcsa_search internal low-level adapter
```

`runtime/tools/rhcsa_search.py` remains internal-only.

`runtime/knowledge/rhcsa_engine.py` remains a deprecated compatibility wrapper.

## 4. Contract Enforcement Status

Implemented:

- `runtime/retrieval/feature_flags.py`
- `runtime/tools/check_no_direct_retrieval_imports.py`
- `tests/test_runtime_router_contract_guard.py`

The import scanner checks coordinator/runtime modules for direct deprecated retrieval imports and fails with a non-zero exit code if violations are found.

Manual scanner result:

```bash
PYTHONPATH=runtime runtime/.venv/bin/python runtime/tools/check_no_direct_retrieval_imports.py
```

Result:

```text
No direct deprecated retrieval imports found.
```

## 5. Remaining Unresolved Bypass Risks

Remaining by design:

- `runtime/retrieval/linux/retrieval_engine.py` still imports `tools.rhcsa_search` as its internal deterministic index adapter.
- `runtime/retrieval/facade.py` still contains compatibility helpers that internally call `tools.rhcsa_search`.
- `runtime/tools/rhcsa_search.py` still contains the low-level search implementation.
- `runtime/knowledge/rhcsa_engine.py` still exists for backward compatibility.

Mitigated in this phase:

- `KnowledgeRouter(..., engine=...)` still works for compatibility, but now emits a `DeprecationWarning`.
- `KnowledgeRouter(..., retriever=...)` still works for tests/controlled compatibility, but now emits a `DeprecationWarning`.

Not solved in this phase:

- Runtime router feature-flag hook is not yet integrated.
- `memory.py` remains a transitional monolith.
- Candidate promotion remains blocked.

## 6. Tests Added

Created:

- `tests/test_runtime_router_contract_guard.py`

Test coverage:

- feature flag defaults OFF
- feature flag ON returns canonical facade boundary only
- invalid flag values do not activate retrieval
- `runtime/main.py` does not import flag or facade directly
- `KnowledgeRouter` default path uses facade
- legacy engine injection emits warning and is not silent
- refusal behavior is preserved
- provenance behavior is preserved
- facade retrieval does not write evidence memory
- coordinator modules do not import low-level retrieval modules
- import scanner passes for coordinator modules

## 7. Tests Passed / Failed

Commands run:

```bash
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest tests.test_linux_retrieval -v
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest tests.test_retrieval_facade_contract -v
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest tests.test_runtime_router_contract_guard -v
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest tests.test_no_direct_rhcsa_search_imports -v
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest tests.test_memory_layer_isolation_smoke -v
```

Results:

- `tests.test_linux_retrieval`: PASS, 7 tests
- `tests.test_retrieval_facade_contract`: PASS, 8 tests
- `tests.test_runtime_router_contract_guard`: PASS, 11 tests
- `tests.test_no_direct_rhcsa_search_imports`: PASS, 1 test
- `tests.test_memory_layer_isolation_smoke`: PASS, 1 test

Total: PASS, 28 tests.

Failed: 0.

## 8. Retrieval Boundary Stability

Status: STABLE FOR CURRENT PHASE.

What is stable:

- Coordinator modules do not directly import deprecated low-level retrieval modules.
- The canonical facade is the coordinator-facing retrieval boundary.
- Deprecated engine injection is no longer silent.
- Feature-flag behavior is explicit and testable.
- Refusal and provenance behavior are preserved.
- Retrieval calls do not write to evidence memory.

What is not yet complete:

- The runtime feature-flag hook is not wired into `runtime/main.py`.
- Runtime-wide refusal semantics remain local to retrieval/kernel behavior.
- Candidate promotion is still blocked pending runtime hook contract completion.

## 9. Canonical Index Safety

Verified untouched:

- `runtime/knowledge/canonical/rhcsa_commands.json`
- `runtime/knowledge/index/command_index.json`
- `runtime/knowledge/candidates/candidate_command_index.json`

Validation command:

```bash
git diff -- runtime/knowledge/canonical/rhcsa_commands.json runtime/knowledge/index/command_index.json runtime/knowledge/candidates/candidate_command_index.json
```

Result: no diff.

## 10. Scope Compliance

COMPLIANT.

Forbidden actions check:

- Canonical index modification: NO
- Candidate promotion: NO
- Candidate record modification: NO
- Runtime retrieval global activation: NO
- Runtime architecture rewrite: NO
- `memory.py` rewrite: NO
- Embeddings added: NO
- Vector DB added: NO
- Agents added: NO
- Autonomous loops added: NO
- Orchestrator redesign: NO
- Compatibility wrappers removed: NO

## 11. Recommended Next Phase

Recommended next phase:

Phase 0D - Feature-Flagged Runtime Hook Dry Run.

Technical reason:

Phase 0C established the contract boundary and explicit flag helper but intentionally did not wire the flag into `runtime/main.py`. The next safe step is a dry-run hook that proves `AIOA_ENABLE_LINUX_RETRIEVAL_V1=1` routes through the canonical facade while `AIOA_ENABLE_LINUX_RETRIEVAL_V1` unset keeps current runtime behavior unchanged. Candidate promotion should remain blocked until that runtime hook is proven by tests.
