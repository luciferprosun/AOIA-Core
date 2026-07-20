# Epistemic Orchestra Contracts + CPT Stage Binding 1A

## Scope

This step adds inert, deterministic metadata contracts. It does not dispatch a
stage, call a provider, continue a run, write an artifact, mutate a gate, or
grant approval. The Knowledge Context Orchestra Adapter remains a separate
future step.

The source checkpoint is
`33dfeb52263a50e23aa7edabdaab1fc47e60c9b9`. The reference ZIP was inspected
outside the repository and matched SHA-256
`117687947c9d0374fde79f8dc1fdfb50ca7b6b32614fa8328493ec635725524f`.

## Reference-to-runtime mapping

| ZIP concept | Current-runtime disposition |
|---|---|
| Canonical JSON and content hashes | Rebuilt as strict `canonical.py`; unsupported values and non-string object keys fail closed. |
| Topology and stage models | Reduced to `EpistemicRunContract` and `EpistemicStageContract`, with only `SEQUENTIAL_RING_V1`, `INDEPENDENT_PANEL_V1`, `PRIMARY`, and `CRITIC`. |
| Critic report validation | Rebuilt as strict `CriticStagePayload` and `CriticIssue`, including explicit `NO_MATERIAL_ISSUE_FOUND`. |
| Prompt isolation | Rebuilt by reusing the existing `runtime.cpt.transform_prompt`; no ZIP prompt/template was copied. |
| Primary revision prompt | Rebuilt as a deterministic inert compilation whose untrusted data is canonical JSON encoded with base64url. |
| Replay and lineage checks | Rebuilt as run, stage, parent, source-revision, CPT, payload, and compilation hash validation. |
| Provider bindings, credential references and endpoint references | Rejected for this step; they do not enter the run or stage contracts. |
| Planner, provider-call count, executor and state machine | Rejected/deferred; no universal orchestrator, dispatcher, executor, loop, retry, fallback or continuation was added. |
| Filesystem audit writer | Not used; CPT audit append is never invoked automatically. |

## Contracts

- Run identity binds the source request, exact source-prompt hash, optional
  knowledge sentinels, ordered stage IDs/roles, mode, maximum count and policy.
- Stage identity binds the exact run, plan position, role, source revision,
  parent lineage, CPT transformation or explicit no-CPT sentinel, exact critic
  payload set for a PRIMARY revision stage, output kind and policy.
- Independent-panel critics bind one primary source revision and cannot carry
  peer payload hashes.
- Sequential stages bind the immediately preceding stage and its exact source
  revision.
- Critic payload parsing rejects missing, empty, malformed, wrapped, unknown or
  authority-bearing fields. Missing output is never inferred as a successful
  review.
- Truncation is a typed object with exact character counts and before/after
  content hashes. Truncated critic output becomes an explicit blocked revision.
- Revision issue IDs must form an exact accepted/rejected/unresolved partition.
  Rejected and unresolved issue records remain in the encoded revision data.
- `PRESERVE_ORIGINAL` retains the exact source-prompt bytes and remains a draft,
  not approval.

## Authority boundary

All run, stage, payload and compilation records explicitly keep provider,
critic, CPT, revision and multi-model agreement non-authoritative. Execution,
write, dispatch, provider-call, approval and gate mutation flags are false.
Human review is required. Hashes bind evidence but grant no capability.

The new runtime package has no process, network, provider SDK, environment,
browser, Git, filesystem-write, approval, gate or controlled-write imports.

## Validation

The focused offline suite covers deterministic hashes, strict round trips,
both modes, exact parent and source bindings, CPT reuse, explicit no-issue
outcomes, truncation, issue partitioning, prompt-data isolation, stale/replay
rejection and static capability boundaries. Final command results are recorded
in the production handoff report accompanying the commit.
