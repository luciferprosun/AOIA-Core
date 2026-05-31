# AOIA Memory Model

Status: canonical doctrine for AOIA-Core v0.1
Phase: 1A - Memory Ontology Freeze
Mode: documentation only

## Purpose

AOIA memory is a layered epistemic system, not a single generic store.

Each layer has a distinct authority class, persistence rule, mutability rule, and access boundary. Runtime convenience must never collapse these boundaries. A record may be copied, summarized, indexed, or referenced only when the destination layer explicitly allows that flow.

This document freezes the canonical memory doctrine before implementation.

Reviewer scope note: this doctrine describes authority boundaries and intended
flows. Current enforcement is partial. Generated runtime artifacts such as
`state/`, `memory/`, `logs/`, and `obsidian_vault/` are non-canonical unless
explicitly promoted through governed paths.

## Layer Summary

| Layer | Name | Authority Class |
| --- | --- | --- |
| L0 | Ephemeral Runtime State | continuity only |
| L1 | Operational Logs | procedural audit |
| L2 | Reasoning Traces | inferential audit |
| L3 | Provenance Records | source lineage |
| L4 | Immutable Evidence | factual support artifact |
| L5 | Contradiction Registry | unresolved conflict record |

## L0 Ephemeral Runtime State

Purpose:
- Maintain active session continuity.
- Track volatile runtime context such as current task, current working directory, open browser state, recent outputs, and temporary execution metadata.

Allowed writers:
- Runtime coordinator.
- Execution engine.
- Browser/session adapters.
- Explicit state migration utility in future implementation.

Allowed readers:
- Runtime coordinator.
- Status commands.
- Execution engine.
- Operator-facing diagnostics.

Persistence rules:
- May be persisted for short continuity restoration.
- Must be treated as cache-like runtime state.
- Must not be used as canonical memory authority.

Mutability rules:
- Fully mutable.
- May be overwritten, compacted, rotated, or discarded.
- No append-only requirement.

Retention policy:
- Short retention.
- Session-scoped by default.
- May be cleared without epistemic data loss if higher layers are intact.

Forbidden inputs:
- L2 reasoning traces as state facts.
- L4 evidence bodies copied into state as authority.
- L5 contradiction status collapsed into a simple boolean.
- Cloud planner output stored as trusted state.

Forbidden outputs:
- Direct promotion into L3 provenance.
- Direct promotion into L4 evidence.
- Direct contradiction resolution in L5.
- Source authority decisions.

Contamination risks:
- Temporary state can be mistaken for long-lived truth.
- Recent outputs can bias retrieval or planning if later treated as facts.
- Session state can silently overwrite older context and erase uncertainty.

## L1 Operational Logs

Purpose:
- Record what the runtime did.
- Preserve procedural auditability of actions, commands, browser events, approvals, rejections, and tool results.

Allowed writers:
- Execution engine.
- Runtime coordinator.
- Browser/session adapters.
- System event logger.

Allowed readers:
- Runtime diagnostics.
- Audit tools.
- Operator review tools.
- Future replay tooling for procedural reconstruction.

Persistence rules:
- Append-only preferred.
- Corrections must be represented by later entries.
- Logs may be rotated or archived.

Mutability rules:
- No silent rewrite after emission.
- Redaction is allowed only as a marked derivative artifact.
- Rotation must preserve chronological replay metadata where practical.

Retention policy:
- Medium retention.
- Retain per session or configured audit period.
- May be archived separately from canonical evidence.

Forbidden inputs:
- L2 reasoning traces copied as operational facts.
- L3 provenance records flattened into generic logs without identity.
- L4 evidence bodies copied into logs as substitutes for evidence.
- L5 contradiction records copied as resolved outcomes.

Forbidden outputs:
- Direct promotion into L4 evidence.
- Direct creation of L3 provenance.
- Direct update of L5 contradiction state.
- Retrieval source material.

Contamination risks:
- A successful command can be mistaken for verified truth.
- Shell output can be mistaken for evidence without source lineage.
- Browser events can be mistaken for captured source artifacts.
- Approval rejection logs can be mistaken for user intent or epistemic evidence.

## L2 Reasoning Traces

Purpose:
- Preserve route choice, uncertainty, confidence shaping, fallback rationale, epistemic safeguards, and planner/kernel reasoning.
- Support audit of why AOIA answered, declined, routed locally, routed externally, or emitted unknown.

Allowed writers:
- Epistemic kernel.
- Runtime coordinator.
- Safeguard emitters.
- Future retrieval guard.
- Future planner audit adapter.

Allowed readers:
- Audit tools.
- Runtime diagnostics.
- Confidence and safeguard review paths.
- Human review workflows.

Persistence rules:
- Append-only.
- Event ordered.
- Must remain separate from evidence and provenance stores.

Mutability rules:
- No silent edits.
- Corrections require a new trace event.
- Summaries are derivatives and must not replace raw traces.

Retention policy:
- Long enough for audit and replay.
- May be archived by session.
- Must remain quarantined from retrieval evidence sources.

Forbidden inputs:
- L4 evidence bodies transformed into reasoning-only summaries without preserving source references.
- L5 contradiction records treated as resolved reasoning conclusions.
- Cloud planner output stored as evidence-like trace.

Forbidden outputs:
- Promotion into L4 evidence.
- Promotion into L3 provenance.
- Retrieval corpus input.
- Authority registry input.
- Direct contradiction resolution.

Contamination risks:
- Reasoning may be mistaken for factual evidence.
- Model-generated explanations may be treated as source truth.
- Summaries can drift from the raw trace.
- Retrieval over reasoning traces can create recursive self-confirmation.

## L3 Provenance Records

Purpose:
- Preserve source identity, lineage, fingerprints, source metadata, and replay constraints.
- Anchor evidence identity and contradiction source relationships.

Allowed writers:
- Provenance registry builder.
- Source ingestion pipeline.
- Knowledge pack build pipeline.
- Future append-only provenance log.
- Future authority registry with explicit schema.

Allowed readers:
- Retrieval guard.
- Epistemic kernel.
- Evidence store.
- Contradiction registry.
- Audit tools.
- Human review workflows.

Persistence rules:
- Append-only or versioned regeneration.
- Prior source identity must remain reconstructable.
- Every provenance record must include a schema version or equivalent generation context.

Mutability rules:
- No silent mutation of existing source identity.
- Supersession must be represented explicitly.
- Regenerated registries must preserve previous lineage or be marked as a new epoch.

Retention policy:
- Long retention.
- Must survive archive transitions.
- Must remain available for evidence replay and contradiction review.

Forbidden inputs:
- L0 runtime state.
- L1 operational logs unless explicitly converted by a source ingestion rule.
- L2 reasoning traces.
- Cloud planner output without external source identity.
- System-generated summaries as source identity.

Forbidden outputs:
- Direct answer content without evidence or retrieval policy.
- Automatic contradiction resolution.
- Mutable runtime state authority.

Contamination risks:
- Generated registry records can be mistaken for source content.
- Stale fingerprints can misrepresent current source state.
- Source lineage can collapse if regeneration overwrites prior identity.

## L4 Immutable Evidence

Purpose:
- Preserve factual support artifacts used for local answer formation, audit, retrieval explanation, or external inspection.
- Store evidence as immutable objects tied to provenance.

Current implementation note:
- The present evidence boundary is a controlled write path and audit-support
  mechanism. A complete content-addressed immutable evidence store remains
  roadmap work.

Allowed writers:
- Evidence capture pipeline.
- Retrieval pipeline only through explicit evidence creation policy.
- Source ingestion pipeline.
- Human-reviewed evidence import.
- Future CAS evidence store.

Allowed readers:
- Retrieval guard.
- Epistemic kernel.
- Answer construction paths.
- Contradiction registry.
- Audit tools.
- Human review workflows.

Persistence rules:
- Immutable once captured.
- Must include content fingerprint or content-addressed identity.
- Must link to L3 provenance when derived from a source artifact.
- Must include capture time, source reference, and evidence type.

Mutability rules:
- No overwrite.
- Corrections create a new evidence object.
- Redactions create a derivative object with explicit lineage.

Retention policy:
- Long retention.
- Evidence referenced by reasoning, answers, provenance, or contradictions must remain available.
- Deletion requires explicit retention policy and tombstone metadata.

Forbidden inputs:
- L0 runtime state.
- L1 operational logs.
- L2 reasoning traces.
- Cloud planner output without external provenance.
- System-generated summaries without source artifact linkage.
- Unfingerprinted browser text or screenshots.

Forbidden outputs:
- Direct mutation of L3 provenance.
- Automatic contradiction resolution in L5.
- Runtime state authority.
- Unqualified answer claims without retrieval/context policy.

Contamination risks:
- Logs can be promoted as evidence because they contain command output.
- Reasoning can be promoted as evidence because it appears coherent.
- Browser captures can be partial, stale, or noisy.
- Evidence without fingerprinting cannot be replayed.

## L5 Contradiction Registry

Purpose:
- Preserve unresolved epistemic conflicts, source disagreements, evidence conflicts, and authority collisions.
- Keep contradiction pressure visible instead of auto-erasing it.

Allowed writers:
- Contradiction detector.
- Epistemic kernel.
- Human review workflow.
- Future contradiction registry adapter.

Allowed readers:
- Epistemic kernel.
- Retrieval guard.
- Answer construction paths.
- Audit tools.
- Human review workflows.
- Authority registry.

Persistence rules:
- Append-only conflict history.
- Contradiction events must preserve linked L3 provenance and L4 evidence references when available.
- Status changes must be explicit new entries, not rewrites.

Mutability rules:
- No automatic deletion.
- No silent resolution.
- Resolution, supersession, rejection, or downgrade must be represented as new registry events.

Retention policy:
- Long retention.
- Contradictions remain visible after later interpretation.
- Resolved contradictions remain replayable.

Forbidden inputs:
- Pure L2 reasoning without evidence/provenance anchor.
- L1 operational logs without explicit evidence promotion policy.
- Cloud planner disagreement without external source reference.
- Runtime confidence state as contradiction proof.

Forbidden outputs:
- Automatic deletion of evidence.
- Automatic rewriting of provenance.
- Automatic answer suppression without policy.
- Direct mutation of runtime authority state.

Contamination risks:
- Contradictions can be treated as bugs and removed.
- Automated resolution can erase epistemic pressure.
- A conflict between generated outputs can be mistaken for a source contradiction.
- Missing provenance can make a contradiction unreplayable.

## Absolute Prohibitions

- L2 reasoning traces must never be promoted to L4 immutable evidence.
- System-generated outputs must not become L3 provenance sources.
- L1 operational logs must not become L4 evidence.
- L5 contradiction records must not be auto-resolved.
- L0 runtime state must not persist as authority.
- Cloud planner output must not become L4 evidence without external provenance.
- Retrieval must not access L2 reasoning traces as source material.
- Runtime state must not define canonical source authority.
- Evidence without fingerprint or provenance linkage must not be treated as canonical.
- Generated summaries must not replace raw source, evidence, provenance, or contradiction records.

## Canonical Data Flow

May flow into L3:
- Source artifact identity from knowledge pack ingestion.
- Source file metadata, reference metadata, and content fingerprints.
- Versioned source registry output from deterministic build tooling.
- Human-reviewed source identity records.
- Supersession and lineage events.

May flow into L4:
- Fingerprinted source excerpts linked to L3 provenance.
- Content-addressed evidence captures.
- Human-reviewed evidence imports with source identity.
- Retrieval artifacts that satisfy evidence creation policy.
- External captures with source URL/path, capture time, and content hash.

May flow into L5:
- Conflicts between L4 evidence objects.
- Conflicts between L3 provenance records.
- Conflicts between evidence and authority registry policy.
- Human-reviewed contradiction reports.
- Kernel-detected contradictions with evidence/provenance references.

Must remain quarantined:
- L0 runtime state.
- L1 operational logs.
- L2 reasoning traces.
- Cloud planner output.
- Generated summaries.
- Browser text or screenshots without fingerprint and source linkage.
- Provider responses without external provenance.
- Operator notes that are not explicitly promoted by a review policy.

## Future Implementation Targets

L2 quarantine:
- Physically separate reasoning traces from retrieval sources.
- Enforce read guards preventing retrieval from indexing L2.
- Mark reasoning summaries as derivatives.

CAS evidence store:
- Store L4 evidence by content hash.
- Require fingerprint, source linkage, capture time, and evidence type.
- Preserve derivative lineage for redaction or normalization.

Append-only provenance log:
- Record source identity events as append-only entries.
- Support supersession and source epoch changes.
- Preserve deterministic replay metadata.

Contradiction registry:
- Represent contradictions as durable events.
- Preserve status changes as append-only updates.
- Require provenance/evidence references whenever available.

Authority registry:
- Define which source classes are allowed for which answer domains.
- Separate authority policy from runtime state.
- Version authority policy decisions.

Retrieval guard:
- Enforce layer access before retrieval.
- Block L0, L1, and L2 from retrieval corpora.
- Require L3/L4 linkage for evidence-backed claims.
- Surface L5 contradictions as confidence constraints.

## Implementation Freeze

This phase does not authorize code changes.

No runtime refactor, adapter implementation, routing change, provider change, or governance runtime change is implied by this document. Implementation may begin only after this doctrine is reviewed and accepted as the canonical AOIA-Core v0.1 memory model.
