# AOIA-Nano Core Mapping

Date: 2026-05-28
Scope: define target structure only; do not create it.

## Target Structure

```text
aoia_nano/
├── __init__.py
├── cli.py
├── config.py
├── router.py
├── retrieval/
├── provenance/
├── executor.py
├── providers/
│   ├── deterministic_mock.py
│   └── one_real_provider.py
tests/
docs/
pyproject.toml
```

## Current To Future Mapping

| Current path | Future AOIA-Nano role |
| --- | --- |
| `runtime/tools/provenance.py` | `aoia_nano/provenance/ledger.py` |
| `runtime/tools/provenance_readout.py` | `aoia_nano/provenance/readout.py` and CLI subcommand |
| `tests/test_append_only_provenance.py` | `tests/test_provenance_ledger.py` |
| `tests/test_provenance_verification.py` | `tests/test_provenance_verification.py` |
| `tests/test_provenance_readout.py` | `tests/test_provenance_readout.py` |
| `runtime/adaptive_routing/config_loader.py` | `aoia_nano/config.py` |
| `runtime/adaptive_routing/deterministic_router.py` | `aoia_nano/router.py` |
| `runtime/retrieval/facade.py` | `aoia_nano/retrieval/facade.py` |
| `runtime/retrieval/linux/` | `aoia_nano/retrieval/rhcsa/` |
| `runtime/knowledge/canonical/` | `aoia_nano/retrieval/rhcsa/canonical/` or packaged data |
| `runtime/knowledge/index/` | `aoia_nano/retrieval/rhcsa/index/` or packaged data |
| `runtime/knowledge/manifests/` | `aoia_nano/retrieval/rhcsa/manifests/` |
| `runtime/tools/executor.py` | `aoia_nano/executor.py` after narrowing to bounded operations |
| `runtime/providers/aureon_provider.py` | Candidate for `one_real_provider.py`, only after MVP decision |
| `runtime/providers/base.py` | Provider protocol/interface |
| `runtime/providers/config.py` | Not core as-is; extract minimal provider config without repo writes |
| `runtime/main.py` | Do not port wholesale; mine only CLI orchestration patterns after state pollution is fixed |
| `runtime/tools/memory.py` | Do not port as core; replace with single ledger and external runtime state |
| `runtime/orchestrator/` | Exclude from AOIA-Nano MVP |
| `runtime/adaptive_routing/circadian_router.py` | Exclude/archive |
| `runtime/adaptive_routing/environment/` | Exclude/archive |
| `tui/`, `web/` | Exclude from AOIA-Nano MVP; optional later clients |

## Minimal Kernel Responsibilities

AOIA-Nano should provide:

- deterministic config load
- deterministic routing decision
- canonical RHCSA retrieval with refusal behavior
- operator approval boundary
- append-only provenance ledger
- replay verification of ledger integrity
- one deterministic mock provider for tests
- optionally one real provider adapter after MVP

It should not include orchestration loops, multi-agent delegation, circadian routing, environment routing, Obsidian vault writes, or raw knowledge build pipelines.
