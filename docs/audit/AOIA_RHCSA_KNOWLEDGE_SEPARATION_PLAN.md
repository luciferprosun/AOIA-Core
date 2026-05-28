# AOIA RHCSA Knowledge Separation Plan

Date: 2026-05-28
Scope: analysis only.

## Current Asset Classification

| Class | Current paths | Recommendation |
| --- | --- | --- |
| Canonical runtime knowledge | `runtime/knowledge/canonical/`, topic markdown dirs such as `bash/`, `filesystem/`, `networking/`, `systemd/`, `storage/`, `users/`, `permissions/`, `selinux/`, `lvm/`, `podman/`, `troubleshooting/` | Keep in AOIA-Core if hash-pinned and manifest-backed. |
| Runtime indexes | `runtime/knowledge/index/`, `runtime/knowledge/command_graph.json`, `runtime/knowledge/context/`, `runtime/knowledge/injection/` | Keep only minimal index/context required by runtime retrieval. |
| Manifests and policy | `runtime/knowledge/manifests/`, `runtime/knowledge/provenance/`, `runtime/knowledge/schema/` | Keep manifest/schema/policy in AOIA-Core. |
| Raw inputs | `runtime/knowledge/raw/` | Move to future `aoia-knowledge-rhcsa`. |
| Source PDFs | `runtime/knowledge/source/` | Move to future `aoia-knowledge-rhcsa`. |
| Extracted inputs | `runtime/knowledge/extracted/`, `runtime/knowledge/parsed/` | Move to future `aoia-knowledge-rhcsa`. |
| Candidate outputs | `runtime/knowledge/candidates/` | Move to future `aoia-knowledge-rhcsa` review area. |
| Validator/build pipeline | `runtime/knowledge/tools/`, `runtime/knowledge/validator/` | Move to future `aoia-knowledge-rhcsa`; AOIA-Core consumes packaged output. |
| Generated reports | `runtime/knowledge/reports/` | Move to knowledge repo or archive. |

## Target Split

AOIA-Core should ship only:

- canonical RHCSA knowledge pack
- runtime index
- manifest with hashes
- retrieval facade and engine
- tests proving deterministic retrieval and refusal behavior

Future `aoia-knowledge-rhcsa` should own:

- source PDFs and raw text
- extraction outputs
- parser outputs
- candidate queues
- validator and build pipeline
- generated build reports
- promotion workflows

## Versioning Principle

DVC and lakeFS both reinforce the separation of code from data/versioned artifacts. DVC uses Git-tracked metafiles for data/pipeline versioning, while lakeFS models data repositories with branches and commits. AOIA should borrow only the principle: canonical knowledge packs should be versioned, manifest-hashed, and reproducible, while raw/build artifacts should not pollute the runtime repo.

Reference URLs:

- DVC data pipelines: https://dvc.org/doc/start/data-pipelines/data-pipelines
- DVC user guide: https://dvc.org/doc/user-guide/what-is-dvc
- lakeFS docs: https://docs.lakefs.io/

## Acceptance Criteria For Future Split

- `AOIA-Core` tests pass without `runtime/knowledge/raw`, `source`, `extracted`, `parsed`, `candidates`, `tools`, `validator`, or `reports`.
- Retrieval tests rely on packaged canonical/index fixtures only.
- Knowledge manifest includes file hashes for canonical/index assets.
- Build pipeline can regenerate canonical pack in `aoia-knowledge-rhcsa`.
