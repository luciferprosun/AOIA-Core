# Start Here: AOIA-Core Architect Handoff

AOIA-Core is a local-first, human-controlled epistemic control system
development prototype. It retains provider review, safety boundaries,
controlled human-gated paths, four knowledge Hats, deterministic offline UNIX
review, tests, and evidence. It is not an autonomous executor.

## Five canonical commands

From an activated Python 3.12 environment in the repository root:

```bash
PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 python -m pip install --no-deps --no-build-isolation -e .
aoia-smoke-test --repository-root .
CI=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test*.py' -q < /dev/null
aoia-offline-prototype --repository-root . --output-root /tmp/aoia-offline-prototype-1a
aoia-verify-artifacts --repository-root .
```

The prototype output path must be new. It creates static files only, starts no
server, and opens no browser.

## Critical invariants

Provider output is never authority. Critic output, `ActionProposal`,
`ArtifactPreview`, knowledge, Hats, routes, retrieval results, scores, audit
records, manifests, and freeze evidence are metadata only. Only the existing
separate canonical human barrier may authorize its exact controlled path.

## Architecture map

- Core runtime and boundaries: `runtime/`
- Provider surfaces: `runtime/providers/`, `runtime/provider_critic/`
- Gate, preview, controlled write, and audit: `runtime/safety/`, `runtime/control_write.py`, `runtime/audit/`
- Linux retrieval: `runtime/retrieval/linux/`
- Bash inspection: `runtime/safety/bash_parser.py`
- Python Hat: `knowledge/hats/hat_003_python/`, `runtime/knowledge/`
- UNIX Hat/routing/prototype: `runtime/memory_hats/unix_hat.py`, `runtime/orchestrator/knowledge_router.py`, `runtime/visible_unix_prototype.py`
- Current retained data: `data/`
- Current freeze: `data/unix_full_validation_freeze_1a_r1/`
- Complete file inventory: `data/architect_handoff_manifest_1a.json`
- Tests: `tests/`

## Limitations and change control

The corpus is bounded, local lexical retrieval can be incomplete, and no score
or evidence record proves correctness. The repository retains compatibility
surfaces that may expose controlled capabilities; do not broaden them, bypass
the human barrier, reinterpret metadata as permission, or alter corpus/index/
freeze bindings without focused review and full regression validation.

Next development step: isolated clean-clone and complete prototype validation.
Commit, push, release archive, and deployment remain separate approvals.
