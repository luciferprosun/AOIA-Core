# Memory And Provenance

Generated: 2026-05-24T18:25:09
Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

# Memory Architecture

Runtime memory implementation and documented memory authority model.

Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

Files in this chunk: 20

## `docs/architecture/AOIA_MEMORY_MODEL.md`

- size: 14412 bytes
- sha256: `498c523af86165c0b49f5e04c96c8ef6038043eaa5b7f085045e6f6f2e2d5c5c`
- category: memory

```markdown
# AOIA Memory Model

Status: canonical doctrine for AOIA-Core v0.1
Phase: 1A - Memory Ontology Freeze
Mode: documentation only

## Purpose

AOIA memory is a layered epistemic system, not a single generic store.

Each layer has a distinct authority class, persistence rule, mutability rule, and access boundary. Runtime convenience must never collapse these boundaries. A record may be copied, summarized, indexed, or referenced only when the destination layer explicitly allows that flow.

This document freezes the canonical memory doctrine before implementation.

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
```

## `docs/architecture/FORBIDDEN_MEMORY_FLOWS.md`

- size: 5776 bytes
- sha256: `b1dcac78701784e03ffeea020d12cf689aa2dfd3eebdeeb894cf308f795b4858`
- category: memory

```markdown
# Forbidden Memory Flows

Status: canonical doctrine for AOIA-Core v0.1
Phase: 1A - Memory Ontology Freeze

## Purpose

This document lists memory flows that AOIA-Core must reject by design. These prohibitions exist to prevent runtime convenience, generated text, or operational traces from becoming epistemic authority.

## Absolute Forbidden Flows

| Source | Destination | Status | Reason |
| --- | --- | --- | --- |
| L0 Ephemeral Runtime State | L3 Provenance Records | forbidden | Runtime state is volatile and cannot define source lineage. |
| L0 Ephemeral Runtime State | L4 Immutable Evidence | forbidden | Session continuity is not factual support. |
| L0 Ephemeral Runtime State | L5 Contradiction Registry | forbidden | Temporary state cannot establish contradiction authority. |
| L1 Operational Logs | L3 Provenance Records | forbidden by default | Logs describe runtime actions, not source identity. |
| L1 Operational Logs | L4 Immutable Evidence | forbidden | Execution traces are procedural records, not evidence. |
| L1 Operational Logs | L5 Contradiction Registry | forbidden by default | Logs do not establish source conflict without evidence promotion policy. |
| L2 Reasoning Traces | L3 Provenance Records | forbidden | Reasoning is generated inference, not source lineage. |
| L2 Reasoning Traces | L4 Immutable Evidence | forbidden | Reasoning must never become evidence. |
| L2 Reasoning Traces | Retrieval Corpus | forbidden | Retrieval over reasoning traces creates self-confirming memory. |
| Cloud Planner Output | L3 Provenance Records | forbidden | Planner output is not an external source. |
| Cloud Planner Output | L4 Immutable Evidence | forbidden without external provenance | Provider text is generated output, not evidence. |
| System-Generated Summaries | L3 Provenance Records | forbidden | Summaries are derivatives, not source identity. |
| System-Generated Summaries | L4 Immutable Evidence | forbidden unless linked to raw evidence as derivative | Summaries can drift from source content. |
| L5 Contradiction Registry | Automatic Resolution | forbidden | Contradictions must not be silently erased. |

## Prohibited Patterns

Reasoning-to-evidence promotion:
- Any direct conversion of L2 reasoning text, model explanation, route rationale, confidence note, or fallback explanation into L4 evidence is forbidden.
- Allowed alternative: create an audit reference to the L2 trace while keeping it outside evidence.

Operational-log evidence promotion:
- Any direct conversion of command output, tool result, approval prompt, browser action, or runtime event into L4 evidence is forbidden.
- Allowed alternative: recapture the underlying artifact through an explicit evidence capture policy with fingerprint and provenance.

Runtime-state authority:
- Any use of current task, recent output, active browser page, open tabs, current working directory, or session state as canonical source authority is forbidden.
- Allowed alternative: treat L0 as continuity context only.

Generated-output provenance:
- Any use of provider output, local planner output, summarizer output, or generated markdown as L3 source provenance is forbidden.
- Allowed alternative: use generated output only as a derivative audit artifact linked to external source provenance.

Contradiction auto-resolution:
- Any automatic deletion, overwrite, downgrade, or resolution of L5 contradiction records is forbidden.
- Allowed alternative: append a new status event with explicit evidence/provenance references and reviewer or policy context.

Retrieval over quarantined layers:
- Retrieval must not index or answer from L0 runtime state, L1 operational logs, or L2 reasoning traces.
- Allowed alternative: retrieval may use L3 provenance and L4 evidence subject to authority policy and contradiction checks.

Unfingerprinted capture:
- Browser text, screenshots, copied snippets, generated extracts, and temporary files must not become L4 evidence without fingerprint, capture time, and source linkage.
- Allowed alternative: store them as quarantined captures until evidence creation policy accepts them.

## Forbidden Output Effects

Forbidden effects on L3:
- Creating provenance from runtime convenience state.
- Replacing prior source identity silently.
- Treating generated summaries as source artifacts.
- Removing old lineage during regeneration without explicit epoch metadata.

Forbidden effects on L4:
- Overwriting existing evidence.
- Storing evidence without content identity.
- Storing evidence without source linkage when the artifact is derived.
- Treating reasoning, logs, or cloud output as evidence.

Forbidden effects on L5:
- Resolving contradictions automatically.
- Deleting contradiction history.
- Creating contradictions from generated disagreement alone.
- Collapsing contradiction status into runtime confidence state.

## Quarantine Requirements

The following must remain quarantined unless a future explicit policy says otherwise:
- L0 runtime state snapshots.
- L1 operational logs and command logs.
- L2 reasoning traces and reasoning summaries.
- Cloud planner output.
- Provider responses.
- System-generated summaries.
- Operator notes not promoted by review.
- Browser captures lacking fingerprint and source linkage.
- Any artifact with unknown source identity.

## Required Promotion Gate

Any future promotion into L3, L4, or L5 must answer:
- What is the source artifact?
- What is the source fingerprint or identity?
- Is the destination layer allowed for this artifact class?
- Is the transformation deterministic or reviewed?
- Is derivative lineage preserved?
- Are contradictions preserved rather than erased?
- Is the promotion recorded as an append-only event?

If any answer is missing, promotion is forbidden.
```

## `docs/architecture/MEMORY_LAYER_ACCESS_MATRIX.md`

- size: 5220 bytes
- sha256: `4f6486f69302dcd5ab1979c20dfc75d4ea0ba6ad53be6d43fbaae0c0f2d4b7db`
- category: memory

```markdown
# Memory Layer Access Matrix

Status: canonical doctrine for AOIA-Core v0.1
Phase: 1A - Memory Ontology Freeze

## Purpose

This matrix defines which AOIA components may write, read, or derive from each memory layer. It is a doctrine document, not an implementation map.

Legend:
- `W`: may write directly
- `R`: may read directly
- `D`: may derive only through explicit policy
- `Q`: quarantined from this component
- `N`: no access

## Layer Access By Component

| Component | L0 Runtime State | L1 Operational Logs | L2 Reasoning Traces | L3 Provenance Records | L4 Immutable Evidence | L5 Contradiction Registry |
| --- | --- | --- | --- | --- | --- | --- |
| Runtime coordinator | W/R | W/R | W/R | R | R | R |
| Execution engine | W/R | W/R | N | N | N | N |
| Browser/session adapter | W/R | W/R | N | D | D | N |
| Epistemic kernel | R | R | W/R | R | R | W/R |
| Knowledge pack builder | N | N | N | W/R | D | D |
| Source ingestion pipeline | N | N | N | W/R | W/R | D |
| Retrieval guard | N | N | Q | R | R | R |
| Answer construction path | R | N | R | R | R | R |
| Audit tooling | R | R | R | R | R | R |
| Human review workflow | R | R | R | W/R | W/R | W/R |
| Authority registry | N | N | N | R | R | R |
| Cloud planner/provider | Q | Q | D | N | N | N |

## Layer Access Rules

L0 Ephemeral Runtime State:
- Direct writes are limited to runtime continuity components.
- Reads are allowed for execution continuity and status inspection.
- L0 must not feed provenance, evidence, or contradiction authority.

L1 Operational Logs:
- Direct writes are limited to procedural event emitters.
- Reads are allowed for audit and diagnostics.
- L1 must not feed retrieval or evidence without a future explicit promotion policy.

L2 Reasoning Traces:
- Direct writes are limited to reasoning, routing, safeguard, and audit emitters.
- Reads are allowed for audit, confidence review, and answer explanation.
- Retrieval guard must treat L2 as quarantined.
- L2 must never feed L4.

L3 Provenance Records:
- Direct writes are limited to source identity builders and reviewed provenance workflows.
- Reads are allowed for retrieval, evidence creation, contradiction tracking, and audit.
- L3 constrains L4 identity and L5 conflict source linkage.

L4 Immutable Evidence:
- Direct writes are limited to evidence capture, source ingestion, and human-reviewed import.
- Reads are allowed for retrieval, answer construction, contradiction detection, and audit.
- L4 objects must be immutable and fingerprinted.

L5 Contradiction Registry:
- Direct writes are limited to contradiction detection, epistemic kernel, and human review.
- Reads are allowed for retrieval guard, answer construction, authority policy, and audit.
- L5 status changes must be append-only events.

## Canonical Flow Matrix

| From | To L0 | To L1 | To L2 | To L3 | To L4 | To L5 |
| --- | --- | --- | --- | --- | --- | --- |
| L0 Runtime State | allowed | allowed as event | allowed as context note | forbidden | forbidden | forbidden |
| L1 Operational Logs | allowed as status | allowed | allowed as audit context | forbidden by default | forbidden | forbidden by default |
| L2 Reasoning Traces | forbidden as authority | allowed as audit event | allowed | forbidden | forbidden | forbidden without evidence/provenance |
| L3 Provenance Records | allowed as runtime reference | allowed as audit event | allowed as reasoning input | allowed | allowed by evidence policy | allowed by contradiction policy |
| L4 Immutable Evidence | allowed as runtime reference | allowed as audit event | allowed as reasoning input | derivative lineage only | allowed as immutable object | allowed by contradiction policy |
| L5 Contradiction Registry | allowed as runtime warning | allowed as audit event | allowed as reasoning constraint | no mutation | no mutation | allowed as append-only status |

## Reader Restrictions

Retrieval:
- May read L3 and L4.
- May read L5 as a confidence and conflict constraint.
- Must not read L0, L1, or L2 as source material.

Answer construction:
- May use L2 as explanation of reasoning process.
- May use L3 and L4 as source-grounded support.
- Must use L5 to preserve uncertainty when contradictions exist.
- Must not use L0 or L1 as factual authority.

Cloud planner/provider:
- May receive selected context generated by policy.
- Must not write L3, L4, or L5 directly.
- Must not be treated as a provenance or evidence source.

Human review:
- May promote artifacts only through explicit review policy.
- Must preserve derivative lineage.
- Must append status changes instead of rewriting authority records.

## Implementation Guard Targets

Future code should enforce:
- L2 quarantine from retrieval indexes.
- CAS-backed L4 evidence writes.
- Append-only L3 provenance events.
- Append-only L5 contradiction events.
- Authority registry checks before answer construction.
- Retrieval guard checks before any source material is selected.
- Explicit promotion policy for any derivative artifact.

## Current Scope

This matrix freezes intended access boundaries for AOIA-Core v0.1.

It does not authorize runtime refactoring, adapter implementation, routing changes, provider changes, or governance runtime changes.
```

## `runtime/memory/__init__.py`

- size: 57 bytes
- sha256: `c2ef9fdbc08bcb194c95c560a609399ef9ee595aaf96a735deae11aad489f153`
- category: memory

```python
"""Compatibility memory package for runtime imports."""
```

## `runtime/memory/gemma_worker_memory.py`

- size: 1328 bytes
- sha256: `63ccaa71a3f503017c53d0bbb4e0886ea29fcfd1eaced3c46e2c226f6dc11785`
- category: memory

```python
from __future__ import annotations

from pathlib import Path
from typing import Any


class GemmaWorkerMemory:
    """Small runtime continuity store for the optional Gemma worker path."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.gemini_calls = 0
        self.gemma_calls = 0
        self.steps: list[dict[str, Any]] = []
        self.last_gemini_instruction = ""

    def record_gemini_call(self) -> None:
        self.gemini_calls += 1

    def record_gemma_call(self) -> None:
        self.gemma_calls += 1

    def remember_step(
        self,
        delegated_step: str,
        action: dict[str, Any],
        result: dict[str, Any] | None,
        gemini_instruction: str,
    ) -> None:
        self.last_gemini_instruction = gemini_instruction
        self.steps.append(
            {
                "delegated_step": delegated_step,
                "action": action,
                "result": result,
            }
        )
        self.steps = self.steps[-20:]

    def summarize_worker_state(self) -> dict[str, Any]:
        return {
            "gemini_calls": self.gemini_calls,
            "gemma_calls": self.gemma_calls,
            "last_gemini_instruction": self.last_gemini_instruction,
            "recent_steps": self.steps[-5:],
        }
```

## `runtime/memory/hats/coding.json`

- size: 258 bytes
- sha256: `a61afdddd01d96e609bc3657035ce5db33af47fa3860dee089439dae9e0dd3a0`
- category: memory

```json
{
  "name": "coding",
  "role": "coding agent",
  "instructions": "Focus on small, reviewable code changes. Read relevant files before editing. Prefer existing project patterns and keep execution human-approved.",
  "project_path": "",
  "persistent": true
}
```

## `runtime/memory/hats/linux.json`

- size: 273 bytes
- sha256: `da908e3635f6587e243bd96c1eeaccbb6c3c40c44514e42d15e194d004b27ac6`
- category: memory

```json
{
  "name": "linux",
  "role": "linux operator",
  "instructions": "Treat shell actions as proposed operations. Prefer inspection commands first. Avoid destructive commands and package installs unless the user explicitly asks.",
  "project_path": "",
  "persistent": true
}
```

## `runtime/memory/hats/research.json`

- size: 254 bytes
- sha256: `bcca48fc94a3ff9694ac20306eddfeff1fdc8ee22a7a9063edb01470b18e55ff`
- category: memory

```json
{
  "name": "research",
  "role": "research analyst",
  "instructions": "Separate sourced facts from inference. When browsing, capture relevant text and summarize concisely without inventing missing details.",
  "project_path": "",
  "persistent": true
}
```

## `runtime/memory/rhcsa_context.py`

- size: 1423 bytes
- sha256: `af6f7fcd96568c5f0de7fd1b47da24f4947781a1d206c15e5d5e82fb0a3ed413`
- category: memory

```python
from __future__ import annotations

from typing import Any

from tools.rhcsa_search import retrieve_examples, search_commands


def inject_linux_context(query: str, max_chars: int = 6000) -> str:
    """Return deterministic RHCSA context for prompt injection."""
    commands = retrieve_command_patterns(query, limit=8)
    examples = retrieve_operational_examples(query, limit=4)
    lines: list[str] = []
    if commands:
        lines.append("Command patterns:")
        for item in commands:
            command = item.get("command") or item.get("command_name") or ""
            topic = item.get("topic") or ""
            summary = item.get("summary") or ""
            lines.append(f"- {command} [{topic}] {summary}".strip())
    if examples:
        lines.append("Operational examples:")
        for item in examples:
            topic = item.get("topic") or ""
            summary = item.get("summary") or ""
            commands_text = ", ".join(str(command) for command in item.get("commands", [])[:5])
            lines.append(f"- {topic}: {summary} {commands_text}".strip())
    text = "\n".join(lines).strip()
    return text[:max_chars]


def retrieve_command_patterns(query: str, limit: int = 8) -> list[dict[str, Any]]:
    return search_commands(query, limit=limit)


def retrieve_operational_examples(query: str, limit: int = 3) -> list[dict[str, Any]]:
    return retrieve_examples(query, limit=limit)
```

## `runtime/obsidian_vault/.obsidian/app.json`

- size: 68 bytes
- sha256: `61eb2a61f12a1dd87d47d3c9d414e795f7a7a623efc38d9da1a2dedb257463b3`
- category: runtime

```json
{
  "theme": "obsidian",
  "baseFontSize": 16,
  "accentColor": ""
}
```

## `runtime/obsidian_vault/00_START_HERE.md`

- size: 227 bytes
- sha256: `b91d1c62ced5098f5c182936a2bdb4dc0eaadc460212e597710bd52a21f635e6`
- category: runtime

```markdown
# Obsidian Vault

This vault stores lightweight runtime memory for the local-first agent.

## Layout
- Daily: append-only day notes
- Sessions: append-only JSONL session records
- Inbox: manual captures
- Projects: active notes
```

## `runtime/obsidian_vault/Daily/2026-05-23.md`

- size: 1529 bytes
- sha256: `b6af56d4d2f0f863ea700624169e6c4b8868994b0048383c3d7fbcdb0dd71d26`
- category: runtime

```markdown
# 2026-05-23

## 2026-05-23T20:40:53.498895 - session_start
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: (none)
- note: (empty)
## 2026-05-23T20:41:22.736235 - session_start
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: (none)
- note: (empty)
## 2026-05-23T20:41:42.159148 - action_result
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jkim jestes mdelem ?
- note: (empty)
## 2026-05-23T20:42:09.955967 - action_result
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: whith model llm you are ?>
- note: (empty)
## 2026-05-23T20:44:13.767757 - action_result
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jestes?
- note: (empty)
## 2026-05-23T20:44:27.844518 - session_start
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: (none)
- note: (empty)
## 2026-05-23T20:45:57.589802 - session_start
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: (none)
- note: (empty)
## 2026-05-23T20:46:56.236358 - action_result
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jakim jestes modelem
- note: (empty)
## 2026-05-23T20:56:46.351395 - action_result
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz sprawdzac linki?
- note: (empty)
## 2026-05-23T20:57:24.368970 - action_result
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: co to jest za projekt ?
- note: (empty)
## 2026-05-23T21:08:43.897332 - action_result
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz wlaczac linki?
- note: (empty)
## 2026-05-23T21:17:53.763306 - action_result
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jestes?
- note: (empty)
```

## `runtime/obsidian_vault/Evidence/20260523_204053_498246.md`

- size: 191 bytes
- sha256: `faffb2271d859ddf1bed6e70c58e5a618505b6959b8ffce864dce2477216f72d`
- category: runtime

```markdown
# Evidence 20260523_204053_498246

## 2026-05-23T20:41:40.368881 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: odpowiedz jednym zdaniem: test gemini
- note: (empty)
```

## `runtime/obsidian_vault/Evidence/20260523_204122_715088.md`

- size: 415 bytes
- sha256: `5bb770adaa365f8c25105d6ce91d87914be2a57a03959a9f77830da26967c141`
- category: runtime

```markdown
# Evidence 20260523_204122_715088

## 2026-05-23T20:43:52.781185 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: can you check for me github project ?? https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T20:44:31.153728 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: can you check link https://github.com/luciferprosun/AOIA-Core
- note: (empty)
```

## `runtime/obsidian_vault/Evidence/20260523_204427_843537.md`

- size: 191 bytes
- sha256: `b6d68eb8e94f619b13dac5abb22c2b19a5d5b05013be365ab7112f44752ea802`
- category: runtime

```markdown
# Evidence 20260523_204427_843537

## 2026-05-23T20:44:36.225982 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: odpowiedz jednym zdaniem: test gemini
- note: (empty)
```

## `runtime/obsidian_vault/Evidence/20260523_204557_588315.md`

- size: 1743 bytes
- sha256: `af0590c3807e46eb16b29de7e8ca5663d5e117bf39c35690f1b728f48c56127c`
- category: runtime

```markdown
# Evidence 20260523_204557_588315

## 2026-05-23T20:47:40.522845 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz sprawdzic projekt na github https://github.com/luciferprosun/AOIA-Core i opisac co buduja
- note: (empty)
## 2026-05-23T20:57:16.478675 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: co to jest za projekt ?
- note: (empty)
## 2026-05-23T20:57:35.443076 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: https://github.com/luciferprosun/AOIA-Core co to za projekt
- note: (empty)
## 2026-05-23T20:57:56.167635 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: https://github.com/luciferprosun/AOIA-Core co to
- note: (empty)
## 2026-05-23T21:08:18.610184 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: co to https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T21:09:03.928659 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: otworz link https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T21:13:15.899108 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz opisac co to za projekt ??  https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T21:15:36.887854 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: co to za projekt ??  https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T21:17:44.443246 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: czy mozesz mi podac 100 komend rhcsa ?
- note: (empty)
## 2026-05-23T21:18:01.070400 - aoia_kernel_evidence
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: znasz rhcsa?
- note: (empty)
```

## `runtime/obsidian_vault/Reasoning/20260523_204053_498246.md`

- size: 492 bytes
- sha256: `26c56d25e3e6ca8bc076460ff96b17b85727467adf4e80228508d1fb2fe81179`
- category: runtime

```markdown
# Reasoning 20260523_204053_498246

## 2026-05-23T20:41:40.368281 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: odpowiedz jednym zdaniem: test gemini
- note: (empty)
## 2026-05-23T20:41:40.380107 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: odpowiedz jednym zdaniem: test gemini
- note: (empty)
## 2026-05-23T20:41:43.617529 - model_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: odpowiedz jednym zdaniem: test gemini
- note: (empty)
```

## `runtime/obsidian_vault/Reasoning/20260523_204122_715088.md`

- size: 1616 bytes
- sha256: `5590a459b20b758b3f6f9ff48a7cbca29026886e8f721220a91a9126a600fe4c`
- category: runtime

```markdown
# Reasoning 20260523_204122_715088

## 2026-05-23T20:41:39.145372 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jkim jestes mdelem ?
- note: (empty)
## 2026-05-23T20:41:39.156454 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jkim jestes mdelem ?
- note: (empty)
## 2026-05-23T20:41:42.134347 - planner_actions
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jkim jestes mdelem ?
- note: (empty)
## 2026-05-23T20:42:06.372241 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: whith model llm you are ?>
- note: (empty)
## 2026-05-23T20:42:06.382561 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: whith model llm you are ?>
- note: (empty)
## 2026-05-23T20:42:09.932835 - planner_actions
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: whith model llm you are ?>
- note: (empty)
## 2026-05-23T20:43:52.779722 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: can you check for me github project ?? https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T20:44:10.604563 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jestes?
- note: (empty)
## 2026-05-23T20:44:10.644685 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jestes?
- note: (empty)
## 2026-05-23T20:44:13.738331 - planner_actions
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jestes?
- note: (empty)
## 2026-05-23T20:44:31.151045 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: can you check link https://github.com/luciferprosun/AOIA-Core
- note: (empty)
```

## `runtime/obsidian_vault/Reasoning/20260523_204427_843537.md`

- size: 492 bytes
- sha256: `bd5dc08ebf6cc68c30dcea04445946e9c7bea84ca6207f836f0bab83c5308c42`
- category: runtime

```markdown
# Reasoning 20260523_204427_843537

## 2026-05-23T20:44:36.225278 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: odpowiedz jednym zdaniem: test gemini
- note: (empty)
## 2026-05-23T20:44:36.237013 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: odpowiedz jednym zdaniem: test gemini
- note: (empty)
## 2026-05-23T20:44:42.878010 - model_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: odpowiedz jednym zdaniem: test gemini
- note: (empty)
```

## `runtime/obsidian_vault/Reasoning/20260523_204557_588315.md`

- size: 3615 bytes
- sha256: `bf2fd895c5c3d01373b988b46e964a563e894b9ce8f5cd6e6437bf644990e616`
- category: runtime

```markdown
# Reasoning 20260523_204557_588315

## 2026-05-23T20:46:48.685181 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jakim jestes modelem
- note: (empty)
## 2026-05-23T20:46:48.694737 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jakim jestes modelem
- note: (empty)
## 2026-05-23T20:46:54.711268 - model_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jakim jestes modelem
- note: (empty)
## 2026-05-23T20:47:40.520849 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz sprawdzic projekt na github https://github.com/luciferprosun/AOIA-Core i opisac co buduja
- note: (empty)
## 2026-05-23T20:56:41.134359 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz sprawdzac linki?
- note: (empty)
## 2026-05-23T20:56:41.152863 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz sprawdzac linki?
- note: (empty)
## 2026-05-23T20:56:44.004804 - model_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz sprawdzac linki?
- note: (empty)
## 2026-05-23T20:57:16.471533 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: co to jest za projekt ?
- note: (empty)
## 2026-05-23T20:57:16.496673 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: co to jest za projekt ?
- note: (empty)
## 2026-05-23T20:57:18.879020 - planner_actions
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: co to jest za projekt ?
- note: (empty)
## 2026-05-23T20:57:35.419186 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: https://github.com/luciferprosun/AOIA-Core co to za projekt
- note: (empty)
## 2026-05-23T20:57:56.166953 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: https://github.com/luciferprosun/AOIA-Core co to
- note: (empty)
## 2026-05-23T21:08:18.609257 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: co to https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T21:08:41.482918 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz wlaczac linki?
- note: (empty)
## 2026-05-23T21:08:41.497982 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz wlaczac linki?
- note: (empty)
## 2026-05-23T21:08:43.874666 - planner_actions
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz wlaczac linki?
- note: (empty)
## 2026-05-23T21:09:03.901633 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: otworz link https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T21:13:15.896134 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: mozesz opisac co to za projekt ??  https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T21:15:36.887128 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: co to za projekt ??  https://github.com/luciferprosun/AOIA-Core
- note: (empty)
## 2026-05-23T21:17:44.440845 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: czy mozesz mi podac 100 komend rhcsa ?
- note: (empty)
## 2026-05-23T21:17:51.239713 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jestes?
- note: (empty)
## 2026-05-23T21:17:51.254249 - planner_request
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jestes?
- note: (empty)
## 2026-05-23T21:17:53.759104 - planner_actions
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: jestes?
- note: (empty)
## 2026-05-23T21:18:01.069732 - aoia_kernel_decision
- cwd: /home/l/Desktop/AOIA-Core/runtime
- task: znasz rhcsa?
- note: (empty)
```




# Provenance System

Provenance, contradiction, source lineage, and policy artifacts.

Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

Files in this chunk: 12

## `CONTRADICTION_SEMANTICS.md`

- size: 2336 bytes
- sha256: `7a0d4fa28f2f9fbd848cc38216032c94211f9163e0ff6ae6e258f624ce781b52`
- category: repository

```markdown
# Contradiction Semantics

Date: 2026-05-23
Phase: Memory Ontology Foundation

## Principle

Contradictions are not execution errors.
They are epistemic signals that indicate competing claims, duplicate authorities, or unresolved source tension.

## Contradiction Object Model

Recommended conceptual fields:
- `contradiction_id`
- `type`
- `subject`
- `sources`
- `status`
- `detected_at`
- `lineage`
- `notes`
- `fingerprints`

## Current AOIA-Compatible Types

- duplicate command conflicts
- self references
- circular references
- future semantic claim conflicts
- future evidence disagreement records

## Status Model

Recommended statuses:
- `unresolved`
- `acknowledged`
- `superseded`
- `contextualized`

Do not use automatic deletion-oriented statuses.

## Unresolved Contradiction Handling

Rules:
1. unresolved contradictions remain visible
2. unresolved contradictions lower confidence or trigger manual review
3. unresolved contradictions do not block all retrieval by default
4. unresolved contradictions are preserved across sessions

## Contradiction Replay Semantics

Replay must preserve:
- when contradiction first appeared
- what sources triggered it
- what later status changes occurred
- whether later evidence contextualized but did not erase it

Replay must not:
- silently collapse historical contradiction into present resolution

## Contradiction Lineage

Each contradiction should preserve:
- origin sources
- derived status transitions
- linked provenance objects
- related evidence objects where applicable

This makes contradiction a lineage-bearing record, not a temporary warning.

## Persistence Rules

Rules:
- contradiction creation is append-only
- resolution is a new event, not mutation of history
- contradiction identifiers should remain stable across regenerations when source set is stable

## Runtime Role

Contradictions should influence:
- confidence labels
- manual review requirements
- output disclaimers

Contradictions should not:
- auto-delete evidence
- auto-select truth consensus
- trigger autonomous resolution loops

## Current AOIA Mapping

Current concrete form:
- `runtime/contradiction_registry.json`
- duplicate command conflicts already persisted as `unresolved`

Interpretation:
- AOIA already implements the seed of L5, but not yet a full evented contradiction ontology
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/contradictions/CONTRADICTION_TAXONOMY.md`

- size: 1889 bytes
- sha256: `ad980e72270dbf34b18edf3d7b0133256bb4ca850110f35e495d2a7e8146fd00`
- category: governance

```markdown
# Contradiction Taxonomy

Phase: 3 - governance preparation
Status: taxonomy only

## Source Contradictions

Different source artifacts disagree.

Example classes:

- provider audit conflict
- report vs source mismatch
- raw vs normalized mismatch

## Temporal Contradictions

A later artifact conflicts with an earlier artifact.

Review question:

- did the system change, or did interpretation change?

## Logical Contradictions

Two claims cannot both be true under the same assumptions.

Review question:

- are assumptions explicit and shared?

## Confidence Contradictions

Confidence labels conflict with evidence strength.

Example:

- high-confidence claim with weak provenance
- low-confidence claim with strong source grounding

## Provenance Contradictions

Artifact source, provider, timestamp, or derivation chain conflicts.

These should be treated as high-risk because provenance is the safety boundary.

## Runtime Contradictions

Observed runtime behavior conflicts with documented architecture or policy.

Runtime contradictions require code-level verification in a future phase.

## Severity Concepts

- low: documentation inconsistency with no authority effect
- medium: ambiguity affecting classification or interpretation
- high: contradiction affecting provenance, evidence, or domain separation
- critical: contradiction allowing cross-domain contamination or evidence promotion

## Review Concepts

Contradiction review should record:

- affected artifacts
- contradiction type
- severity
- case-study scope
- reviewer
- status

## Quarantine Concepts

Quarantine is required when a contradiction could cross:

- LSC/AOIA boundary
- evidence/reasoning boundary
- runtime/archive boundary
- source/derived boundary

## No Auto-Resolution

No contradiction is resolved by:

- model agreement
- majority vote
- runtime state
- cleanup preference
- naming convention
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/provenance/PROVENANCE_MODEL_PREP.md`

- size: 1637 bytes
- sha256: `cb7354274bffe59e20047529a948866f068ed55425b3debfd2e60d79b7d5c63b`
- category: provenance

```markdown
# Provenance Model Preparation

Phase: 3 - governance preparation
Status: preparation only

## Provenance Inheritance

Derived artifacts inherit provenance from their input artifacts.

Inheritance should preserve:

- source artifact IDs
- import events
- normalization events
- provider attribution
- case-study scope

## Provenance Decay

Confidence in provenance should decay as chain depth increases or as transformations become less direct.

Decay triggers:

- missing raw source
- unknown provider
- inferred timestamp
- manual summary without source links
- cross-case references

## Replay Constraints

Replay requires:

- append-only events
- stable artifact references
- explicit source paths
- no silent mutation
- recorded normalization steps

Replay reconstructs lineage. It does not prove claims.

## Chain-Depth Concepts

Suggested conceptual levels:

- depth 0: raw artifact
- depth 1: normalized artifact
- depth 2: derived summary
- depth 3: synthesis or recommendation

Higher depth should require stronger review.

## Append-Only Assumptions

Provenance records should be append-only.

Corrections should create new records that supersede old ones without deleting them.

## Planner Exclusion Concepts

Planner outputs must not become provenance sources.

Planner outputs may reference provenance only when provided by a validated retrieval or review path.

## Non-Authoritative Trace Rules

Reasoning traces:

- may document process
- may support replay context
- may reveal contamination

Reasoning traces must not:

- become evidence
- become provenance sources
- override source artifacts
- resolve contradictions
```

## `MHLM_MHSR/framework/methodology/contradiction_policy.md`

- size: 814 bytes
- sha256: `ab409b2b9e3150d34ecbcc43109db625ddb8463bdd18668038076af82ebd4853`
- category: governance

```markdown
# Contradiction Policy

## Purpose

Define how contradictions should be preserved without forcing premature resolution.

## Contradiction Rules

- Contradictions must be recorded, not erased.
- Contradictions must not be auto-resolved by runtime state or model output.
- Contradiction records should identify affected artifacts and case study scope.
- LSC contradictions and AOIA contradictions must remain separated unless explicitly cross-referenced.

## Evidence Boundary

A contradiction record is a review object. It is not automatically evidence and does not replace the source artifacts it references.

## Resolution Status

Allowed status values for future contradiction records:

- open
- under_review
- resolved_with_evidence
- rejected
- superseded

Phase 1 does not implement contradiction resolution.
```

## `MHLM_MHSR/framework/schemas/provenance_record.schema.json`

- size: 440 bytes
- sha256: `c43d5f4e2da92e53eff410fbb7c9a6a48c24c84aba2bc2c4d81301ae05c82b98`
- category: provenance

```json
{
  "schema_name": "provenance_record",
  "version": "0.1",
  "status": "placeholder",
  "required_fields": [
    "provenance_id",
    "source_type",
    "source_ref",
    "case_study",
    "artifact_ref"
  ],
  "allowed_source_types": [
    "provider_export",
    "repository_snapshot",
    "source_document",
    "session_export",
    "manual_record"
  ],
  "notes": "Initial placeholder only. Do not treat as final validation schema."
}
```

## `PROVENANCE_FOUNDATION.md`

- size: 2349 bytes
- sha256: `df1f72e945e016ec5bcb524da13453de8e81b71ff6e5de2b2adc09fe2a57d93a`
- category: provenance

```markdown
# Provenance Foundation

Date: 2026-05-23
Phase: Memory Ontology Foundation

## Purpose

Provenance is the identity layer that makes evidence replayable and contradictions meaningful.

Without provenance:
- evidence cannot be trusted structurally
- contradiction sources cannot be traced
- retrieval cannot be replayed deterministically

## Source Identity

A provenance object should identify:
- artifact path
- artifact type
- metadata
- internal references
- command count where relevant
- content fingerprint
- generation timestamp or version epoch

Current AOIA basis:
- `runtime/provenance_registry.json`

## Retrieval Metadata

Required metadata classes:
- retrieval path used
- topic filter used
- matching score
- confidence context
- result rank

Current AOIA gap:
- retrieval metadata is produced at runtime but not formalized as a dedicated provenance event layer

## Evidence Fingerprints

Every evidence object should carry:
- content hash or equivalent fingerprint
- source reference
- capture timestamp
- source type

Rule:
- no evidence without fingerprint or source linkage should be treated as canonical evidence

## Trust Versioning

Recommended trust versioning principles:
- provenance schema version
- source snapshot version
- retrieval logic version
- contradiction policy version when relevant

Purpose:
- allow replay to distinguish source change from retrieval change

## Append-Only Lineage

Provenance history should be append-only at the record level.

Allowed:
- new source snapshots
- new fingerprints
- supersession markers

Not allowed:
- silent replacement of prior source identity records

## Replay Compatibility

Replay should be able to answer:
- what artifact was used
- what exact fingerprint it had
- what references it exposed
- which evidence objects were derived from it
- which contradictions were associated with it

## Relationship to Other Layers

- L3 provenance constrains L4 evidence identity
- L3 provenance anchors L5 contradiction sources
- L3 provenance must outrank L2 reasoning in structural authority

## Current AOIA Judgment

AOIA already has a viable provenance seed:
- artifact identity
- metadata
- references
- content hashes

What is still missing:
- formal replay versioning
- explicit evidence object linkage
- append-only provenance evolution semantics across knowledge rebuilds
```

## `contradictions/README.md`

- size: 305 bytes
- sha256: `00a0aa5200b775d21d33a25a1a890d507fa4b5c517ce1209cbe014c73376d881`
- category: repository

```markdown
# Contradictions

Prepared canonical boundary for AOIA contradiction authority.

This directory is intentionally created without migration in this phase.
Current contradiction source remains under:
- `runtime/contradiction_registry.json`
- contradiction logic inside `runtime/tools/epistemic_registry.py`
```

## `provenance/README.md`

- size: 265 bytes
- sha256: `b555b95809c03e93ff5f45765bd02efa93b3d33e7b9caaf8082ced426e36ab6e`
- category: provenance

```markdown
# Provenance

Prepared canonical boundary for AOIA provenance authority.

This directory is intentionally created without migration in this phase.
Current provenance source remains under:
- `runtime/provenance_registry.json`
- `runtime/tools/epistemic_registry.py`
```

## `runtime/contradiction_registry.json`

- size: 6987 bytes
- sha256: `bc29d1392a2dfbb79e6c4f260186659b40d3fd0c3c5ca516fbb60ea5247f2e42`
- category: runtime

```json
{
  "generated_at": "2026-05-23T02:22:03.897193",
  "root": "knowledge",
  "policy": {
    "automatic_resolution": false,
    "note": "Contradictions and epistemic conflicts are reported only. No automatic resolution is performed."
  },
  "summary": {
    "self_reference_count": 0,
    "circular_reference_count": 0,
    "duplicate_command_count": 3,
    "duplicate_artifact_count": 0
  },
  "reference_graph": {
    "knowledge/README.md": [
      "knowledge/canonical/rhcsa_commands.json",
      "knowledge/parsed/rhcsa_sections.json"
    ],
    "knowledge/bash/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/bash/skrypty-bash-podstawy.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/bash/wyszukiwanie-i-filtrowanie-tekstu.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/bash/zaawansowane-narzdzia-tekstowe.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/bash/zmienne-rodowiskowe-i-powoka.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/canonical/rhcsa_commands.json": [],
    "knowledge/command_graph.json": [],
    "knowledge/context/context_pack.json": [],
    "knowledge/examples/ls-command.json": [],
    "knowledge/examples/rm-recursive-force.json": [],
    "knowledge/examples/systemctl-status.json": [],
    "knowledge/filesystem/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/filesystem/archiwizacja-i-kompresja.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/filesystem/edytor-vim.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/filesystem/nawigacja-po-systemie-plikow.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/filesystem/operacje-na-plikach-i-katalogach.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/filesystem/przegldanie-zawartoci-plikow.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/filesystem/wyszukiwanie-plikow.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/index/command_index.json": [],
    "knowledge/injection/injected_context.json": [],
    "knowledge/lvm/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/lvm/lvm-logical-volume-manager.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/networking/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/networking/nfs-i-autofs.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/networking/samba-i-nfs-klient.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/networking/sie-konfiguracja-i-diagnostyka.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/networking/ssh-i-dostp-zdalny.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/networking/zapora-ogniowa-firewalld.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/parsed/rhcsa_sections.json": [],
    "knowledge/permissions/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/permissions/uprawnienia-i-wasno-plikow.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/podman/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/podman/kontenery-podman.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/schema/command.schema.json": [],
    "knowledge/selinux/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/selinux/selinux.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/storage/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/storage/przechowywanie-danych-dyski-i-partycje.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/storage/systemy-plikow-i-montowanie.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/storage/zarzdzanie-dyskami-raid.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/systemd/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/systemd/boot-i-grub.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/systemd/cron-i-harmonogramowanie-zada.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/systemd/systemd-i-zarzdzanie-usugami.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/systemd/zarzdzanie-pakietami-dnf-rpm.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/tools/CANONICAL_BUILDER_README.md": [],
    "knowledge/tools/CONTEXT_PACK_README.md": [],
    "knowledge/tools/INDEX_BUILDER_README.md": [],
    "knowledge/tools/INJECTION_LAYER_README.md": [],
    "knowledge/tools/README.md": [],
    "knowledge/tools/SECTION_PARSER_README.md": [
      "knowledge/parsed/rhcsa_sections.json"
    ],
    "knowledge/troubleshooting/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/troubleshooting/diagnostyka-i-narzdzia-systemowe.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/troubleshooting/dodatkowe-narzdzia-administracyjne.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/troubleshooting/informacje-o-systemie.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/troubleshooting/logowanie-i-monitorowanie-systemu.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/troubleshooting/zarzdzanie-procesami.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/users/README.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/users/zarzdzanie-grupami.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/users/zarzdzanie-uytkownikami.md": [
      "knowledge/canonical/rhcsa_commands.json"
    ],
    "knowledge/validator/validation_report.md": []
  },
  "self_references": [],
  "circular_references": [],
  "duplicate_commands": [
    {
      "type": "duplicate_command",
      "command": "ls",
      "sources": [
        "knowledge/examples/ls-command.json",
        "knowledge/filesystem/nawigacja-po-systemie-plikow.md"
      ],
      "status": "unresolved"
    },
    {
      "type": "duplicate_command",
      "command": "ls -la",
      "sources": [
        "knowledge/examples/ls-command.json",
        "knowledge/filesystem/nawigacja-po-systemie-plikow.md"
      ],
      "status": "unresolved"
    },
    {
      "type": "duplicate_command",
      "command": "systemctl status",
      "sources": [
        "knowledge/examples/systemctl-status.json",
        "knowledge/systemd/systemd-i-zarzdzanie-usugami.md"
      ],
      "status": "unresolved"
    }
  ],
  "duplicate_artifacts": []
}
```

## `runtime/knowledge/provenance/PROVENANCE_POLICY.md`

- size: 1725 bytes
- sha256: `ae556822e087e0657987a07118159063eccb6563f17776f159f00578679955de`
- category: provenance

```markdown
# Linux Engineering Provenance Policy

This policy governs the RHCSA/RHCE/Linux Engineering knowledge layer stored under `runtime/knowledge/`.

## Rules

- No silent overwrites.
- No duplicate master files.
- Every future update needs a changelog.
- Source lineage must be preserved.
- Evidence memory must remain separate from reasoning memory.
- Extracted files must trace back to the canonical PDF or another explicit source artifact.

## Canonical Source

Current canonical source:

- `runtime/knowledge/source/linux_master_library_v1.pdf`

Legacy source retained for backward compatibility:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`

## Extraction Lineage

Extracted artifacts must record or infer their source from:

- `runtime/knowledge/manifests/library_manifest.yaml`
- the canonical source filename
- the source hash where available

Current extracted artifacts:

- `runtime/knowledge/extracted/linux_master_library_v1.txt`
- `runtime/knowledge/extracted/linux_master_library_v1.md`

## Memory Boundary

Evidence memory and reasoning memory are separate authority layers:

- evidence memory may preserve source-backed observations and fingerprints
- reasoning memory may preserve derived analysis or session reasoning
- reasoning memory must not become source provenance
- runtime outputs must not silently promote themselves into canonical evidence

## Future Update Requirements

Every future source update must:

1. Preserve the previous canonical source.
2. Add a versioned new source file.
3. Record source hash and lineage in the manifest.
4. Add a changelog or audit report.
5. Rebuild indexes deterministically.
6. Deduplicate command entries without deleting historical source artifacts.
```

## `runtime/provenance_registry.json`

- size: 41551 bytes
- sha256: `d7eedca193d1a2664acdb80a3e164d77f9134a08c44e45d71e660ff94f42a0f9`
- category: provenance

```json
{
  "generated_at": "2026-05-23T02:22:03.840007",
  "root": "knowledge",
  "artifact_count": 62,
  "records": [
    {
      "artifact": "knowledge/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "knowledge"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json",
        "knowledge/parsed/rhcsa_sections.json"
      ],
      "command_count": 0,
      "content_hash": "5b8c73e1184b61b7b2ee474ce4f2fd1c9c41e8cf84e2b5c482a4362f5aa111e8"
    },
    {
      "artifact": "knowledge/bash/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "bash"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "0ede11b4fdc0359f45642cfee4539d007637090815fafcd97470ce86c2ef0a17"
    },
    {
      "artifact": "knowledge/bash/skrypty-bash-podstawy.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Skrypty bash — podstawy",
        "topic": "bash",
        "source_section": "Skrypty bash — podstawy",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "bash",
          "break",
          "chmod",
          "continue",
          "do",
          "done",
          "echo",
          "else",
          "esac",
          "fi",
          "linux",
          "mktemp",
          "rhcsa",
          "skrypty-bash-podstawy",
          "then"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 25,
      "content_hash": "bf38c89257112f90f7305bd52aa576bcde2f82b72306da2a2195d640ce4e83e9"
    },
    {
      "artifact": "knowledge/bash/wyszukiwanie-i-filtrowanie-tekstu.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Wyszukiwanie i filtrowanie tekstu",
        "topic": "bash",
        "source_section": "Wyszukiwanie i filtrowanie tekstu",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "awk",
          "bash",
          "file",
          "grep",
          "linux",
          "rhcsa",
          "wyszukiwanie-i-filtrowanie-tekstu"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 30,
      "content_hash": "9576ba68147d6541d1eb97b947142c584dbe0c43c895f8a40883f4f5b60ad789"
    },
    {
      "artifact": "knowledge/bash/zaawansowane-narzdzia-tekstowe.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Zaawansowane narz■dzia tekstowe",
        "topic": "bash",
        "source_section": "Zaawansowane narz■dzia tekstowe",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "bash",
          "cat",
          "date",
          "echo",
          "gpg",
          "hwclock",
          "linux",
          "rhcsa",
          "zaawansowane-narzdzia-tekstowe"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 11,
      "content_hash": "1d52cff9b59f7ae03ba50c11e67dc77fa955a2a5ccd383225d79782bbd4f51a0"
    },
    {
      "artifact": "knowledge/bash/zmienne-rodowiskowe-i-powoka.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Zmienne ■rodowiskowe i pow■oka",
        "topic": "bash",
        "source_section": "Zmienne ■rodowiskowe i pow■oka",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "alias",
          "bash",
          "cat",
          "complete",
          "ctrl+r",
          "echo",
          "env",
          "false",
          "hash",
          "history",
          "linux",
          "ls",
          "printenv",
          "rhcsa",
          "set",
          "source",
          "true",
          "zmienne-rodowiskowe-i-powoka"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 35,
      "content_hash": "9cf79632f711d2cc0a8cc6a8ba2cf86b724d4fbfae8bd9ee812994cfc19102cc"
    },
    {
      "artifact": "knowledge/canonical/rhcsa_commands.json",
      "artifact_type": "json_index",
      "metadata": {
        "id": "rhcsa_commands",
        "category": "canonical",
        "risk": "",
        "tags": []
      },
      "references": [],
      "command_count": 940,
      "content_hash": "637a4ae1d03ba9b04e41cf1a566be97d88994bf9f3cfe0c5520b2e41bac73c85"
    },
    {
      "artifact": "knowledge/command_graph.json",
      "artifact_type": "json_document",
      "metadata": {
        "id": "command_graph",
        "category": "",
        "risk": "",
        "tags": []
      },
      "references": [],
      "command_count": 0,
      "content_hash": "ee66ed8e6af4795feb86dde840fe4fdd36a4bfea66e95a44be3fca850592f842"
    },
    {
      "artifact": "knowledge/context/context_pack.json",
      "artifact_type": "json_index",
      "metadata": {
        "id": "context_pack",
        "category": "context",
        "risk": "",
        "tags": []
      },
      "references": [],
      "command_count": 3,
      "content_hash": "fc6464e3cc23407afec3dd8256798c3672058276a6144ef2ccbbcb8b7b0107cf"
    },
    {
      "artifact": "knowledge/examples/ls-command.json",
      "artifact_type": "json_example",
      "metadata": {
        "id": "ls-command",
        "category": "filesystem",
        "risk": "low",
        "tags": [
          "directory-listing",
          "read-only"
        ]
      },
      "references": [],
      "command_count": 2,
      "content_hash": "42d4bc928ee4ef2c15a961c8d17885ea917bbd64be0ce498e30865e215d1a176"
    },
    {
      "artifact": "knowledge/examples/rm-recursive-force.json",
      "artifact_type": "json_example",
      "metadata": {
        "id": "rm-recursive-force",
        "category": "filesystem",
        "risk": "critical",
        "tags": [
          "destructive",
          "recursive-delete"
        ]
      },
      "references": [],
      "command_count": 2,
      "content_hash": "ff6400c227c917e4fdcb7cf211c175861563dff1536e35bad6bee66be7bd25d0"
    },
    {
      "artifact": "knowledge/examples/systemctl-status.json",
      "artifact_type": "json_example",
      "metadata": {
        "id": "systemctl-status",
        "category": "service",
        "risk": "low",
        "tags": [
          "read-only",
          "service-status"
        ]
      },
      "references": [],
      "command_count": 2,
      "content_hash": "dd0ed5761bd48c9a90cba7600bb807f8d0c25762a1610d4caa63285e05da41c4"
    },
    {
      "artifact": "knowledge/filesystem/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "filesystem"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "b1a3251dfdc7d1d80808a1bd92625bf9405b4e75bb428808ccad82e9e91d2958"
    },
    {
      "artifact": "knowledge/filesystem/archiwizacja-i-kompresja.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Archiwizacja i kompresja",
        "topic": "filesystem",
        "source_section": "Archiwizacja i kompresja",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "archive.tar.bz2",
          "archive.tar.gz",
          "archive.tar.xz",
          "archiwizacja-i-kompresja",
          "filesystem",
          "find",
          "linux",
          "newfile",
          "rhcsa",
          "tar"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 23,
      "content_hash": "a1790486b17e69965fe65b0933634e69a0002b6fedac27fb65363e31031a5380"
    },
    {
      "artifact": "knowledge/filesystem/edytor-vim.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Edytor Vim",
        "topic": "filesystem",
        "source_section": "Edytor Vim",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "a",
          "b",
          "cat",
          "cc",
          "ctrl+b",
          "ctrl+d",
          "ctrl+f",
          "ctrl+r",
          "ctrl+u",
          "ctrl+v",
          "cw",
          "d",
          "d0",
          "dd",
          "dw",
          "e",
          "edytor-vim",
          "esc",
          "filesystem",
          "g",
          "gg",
          "gt",
          "gu",
          "i",
          "linux",
          "n",
          "o",
          "p",
          "q",
          "qa",
          "r",
          "rhcsa",
          "u",
          "v",
          "vim",
          "x",
          "yy",
          "zq",
          "zz"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 60,
      "content_hash": "b63bad518761f1a624ab831eb5877d0ceca6169fe5282b5653a56de7dea7b7af"
    },
    {
      "artifact": "knowledge/filesystem/nawigacja-po-systemie-plikow.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Nawigacja po systemie plików",
        "topic": "filesystem",
        "source_section": "Nawigacja po systemie plików",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "basename",
          "cd",
          "dirname",
          "dirs",
          "echo",
          "filesystem",
          "linux",
          "ls",
          "nawigacja-po-systemie-plikow",
          "popd",
          "pwd",
          "rhcsa",
          "tree"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 26,
      "content_hash": "bb5e3365bd9e1565634f053e56fc9f561829809fbd72419a9e0f2712b86ea554"
    },
    {
      "artifact": "knowledge/filesystem/operacje-na-plikach-i-katalogach.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Operacje na plikach i katalogach",
        "topic": "filesystem",
        "source_section": "Operacje na plikach i katalogach",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cp",
          "filesystem",
          "linux",
          "mkdir",
          "nadpisaniem",
          "operacje-na-plikach-i-katalogach",
          "rhcsa",
          "rm",
          "rsync",
          "touch"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 27,
      "content_hash": "a3c2d08d8401ec6f6ba8c7ef0963cc79cca5615df5a0e142cded335993901156"
    },
    {
      "artifact": "knowledge/filesystem/przegldanie-zawartoci-plikow.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Przegl■danie zawarto■ci plików",
        "topic": "filesystem",
        "source_section": "Przegl■danie zawarto■ci plików",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "filesystem",
          "linux",
          "przegldanie-zawartoci-plikow",
          "rhcsa"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 4,
      "content_hash": "3bee5e9ad124d446843c13e8d9d7ac0c8c9a0b6f86d62264a85a8389b1c2f83c"
    },
    {
      "artifact": "knowledge/filesystem/wyszukiwanie-plikow.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Wyszukiwanie plików",
        "topic": "filesystem",
        "source_section": "Wyszukiwanie plików",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "filesystem",
          "find",
          "linux",
          "reference_file",
          "rhcsa",
          "updatedb",
          "wyszukiwanie-plikow"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 47,
      "content_hash": "415130ede8a660f67260b6e32f617c649e5a2153b2cde99d43a13235f611e427"
    },
    {
      "artifact": "knowledge/index/command_index.json",
      "artifact_type": "json_document",
      "metadata": {
        "id": [
          "id"
        ],
        "category": "",
        "risk": "",
        "tags": []
      },
      "references": [],
      "command_count": 1,
      "content_hash": "055d70472f22deebb929a659c9c3321df3eb4d1298aae3dc837dcbed1d1e66fe"
    },
    {
      "artifact": "knowledge/injection/injected_context.json",
      "artifact_type": "json_index",
      "metadata": {
        "id": "injected_context",
        "category": "injection",
        "risk": "",
        "tags": []
      },
      "references": [],
      "command_count": 0,
      "content_hash": "66cf4fd7c08590cefe6af64ddb9ed90581e7b9999d76b3ff606168ad28e7e1c6"
    },
    {
      "artifact": "knowledge/lvm/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "lvm"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "42a87388664e11e3a511741820ab50239feff10f0ca47922a8f1115ba8989137"
    },
    {
      "artifact": "knowledge/lvm/lvm-logical-volume-manager.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "LVM — Logical Volume Manager",
        "topic": "lvm",
        "source_section": "LVM — Logical Volume Manager",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "linux",
          "lvdisplay",
          "lvm",
          "lvm-logical-volume-manager",
          "lvmdiskscan",
          "lvremove",
          "lvs",
          "lvscan",
          "newname",
          "pvdisplay",
          "pvs",
          "pvscan",
          "rhcsa",
          "vgdisplay",
          "vgs",
          "vgscan"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 15,
      "content_hash": "8a630a9fcd450aaaba99cf21d247bb8aa74367630aaf797726368d31f66a9b6c"
    },
    {
      "artifact": "knowledge/networking/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "networking"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "e2b83637740505d7107bee7223adacf117942644575865ca887f04e64b9f88b8"
    },
    {
      "artifact": "knowledge/networking/nfs-i-autofs.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "NFS i Autofs",
        "topic": "networking",
        "source_section": "NFS i Autofs",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "exportfs",
          "firewall-cmd",
          "linux",
          "ls",
          "mount",
          "networking",
          "nfs-i-autofs",
          "nfs-server",
          "nfsstat",
          "rhcsa"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 14,
      "content_hash": "d0119593a840d2d52ffbf85d70dc1e22e6a1b0702c35b660fa491898fccba574"
    },
    {
      "artifact": "knowledge/networking/samba-i-nfs-klient.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Samba i NFS (klient)",
        "topic": "networking",
        "source_section": "Samba i NFS (klient)",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "grep",
          "linux",
          "mount",
          "networking",
          "rhcsa",
          "samba-i-nfs-klient",
          "smbclient",
          "testparm"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 6,
      "content_hash": "bae608de9b12eed297e23d6f89c47f0163c977e2677b2e3996a029b7bf16c29b"
    },
    {
      "artifact": "knowledge/networking/sie-konfiguracja-i-diagnostyka.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Sie■ — konfiguracja i diagnostyka",
        "topic": "networking",
        "source_section": "Sie■ — konfiguracja i diagnostyka",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "curl",
          "established",
          "hostname",
          "ip",
          "linux",
          "networking",
          "nmcli",
          "nmtui",
          "pid",
          "procesami",
          "rhcsa",
          "sie-konfiguracja-i-diagnostyka"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 37,
      "content_hash": "2251c1dbbc3d074414c34582bfaf5aebdffdfb2f9dd91630bb158ae81f5faeb6"
    },
    {
      "artifact": "knowledge/networking/ssh-i-dostp-zdalny.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "SSH i dost■p zdalny",
        "topic": "networking",
        "source_section": "SSH i dost■p zdalny",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "chmod",
          "ed25519",
          "horized_keys",
          "linux",
          "networking",
          "rhcsa",
          "rsync",
          "scp",
          "ssh",
          "ssh-add",
          "ssh-copy-id",
          "ssh-i-dostp-zdalny"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 39,
      "content_hash": "099ff2ae2228859628c3501f394ebf676057276e130b0839dd145cc76e2447e4"
    },
    {
      "artifact": "knowledge/networking/zapora-ogniowa-firewalld.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Zapora ogniowa (firewalld)",
        "topic": "networking",
        "source_section": "Zapora ogniowa (firewalld)",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "firewall-cmd",
          "firewalld",
          "linux",
          "networking",
          "rhcsa",
          "zapora-ogniowa-firewalld"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 25,
      "content_hash": "ed795b68cd50a2da83e7c750a3b232bc04804c40724b649c4129b8f6f963910e"
    },
    {
      "artifact": "knowledge/parsed/rhcsa_sections.json",
      "artifact_type": "json_index",
      "metadata": {
        "id": "rhcsa_sections",
        "category": "parsed",
        "risk": "",
        "tags": []
      },
      "references": [],
      "command_count": 940,
      "content_hash": "03615be0cd88162c1758d3fd6028d19aaa64efca7898298895b0c1f669fda9f6"
    },
    {
      "artifact": "knowledge/permissions/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "permissions"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "1bc493d9869441a987d4800ef93c0b84b2ea006d2b6b571d6a439f6d3ecbbcfe"
    },
    {
      "artifact": "knowledge/permissions/uprawnienia-i-wasno-plikow.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Uprawnienia i w■asno■■ plików",
        "topic": "permissions",
        "source_section": "Uprawnienia i w■asno■■ plików",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "chmod",
          "chown",
          "find",
          "katalogu",
          "linux",
          "ls",
          "permissions",
          "rhcsa",
          "umask",
          "uprawnienia-i-wasno-plikow"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 31,
      "content_hash": "9a2ccb62ebe795c2ad4765e378879c95715a3d073d25ab19a529aeb3c4a47361"
    },
    {
      "artifact": "knowledge/podman/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "podman"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "affea5c5d83a9cc8577d0e347d412b53a00bb780d3783e958b872cb577fe75a4"
    },
    {
      "artifact": "knowledge/podman/kontenery-podman.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Kontenery Podman",
        "topic": "podman",
        "source_section": "Kontenery Podman",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "container",
          "dst:tag",
          "file.tar",
          "image",
          "image:tag",
          "kontenery-podman",
          "linux",
          "podman",
          "rhcsa"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 109,
      "content_hash": "35b2138379678d249cf29b77051382ce981ebbc9257697ec6d8a8ac998b8d891"
    },
    {
      "artifact": "knowledge/schema/command.schema.json",
      "artifact_type": "json_document",
      "metadata": {
        "id": "command.schema",
        "category": "",
        "risk": "",
        "tags": []
      },
      "references": [],
      "command_count": 0,
      "content_hash": "8af744dada5d8a7d863cf2980e657109f998a9fcb0faa90e2bc052e9d2e49f24"
    },
    {
      "artifact": "knowledge/selinux/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "selinux"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "7db0c2e67b2046063a1c1d8fb95fda8ee26b4efdd8b705cb466da521bfccd736"
    },
    {
      "artifact": "knowledge/selinux/selinux.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "SELinux",
        "topic": "selinux",
        "source_section": "SELinux",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "getenforce",
          "grep",
          "httpd_sys_content_t",
          "journalctl",
          "linux",
          "ls",
          "matchpathcon",
          "restorecon",
          "rhcsa",
          "selinux",
          "semanage",
          "sestatus",
          "setsebool",
          "touch"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 36,
      "content_hash": "1cbbde7010c41440aa1651de04fb76ef60a288e2242260de2f379700f06c12c9"
    },
    {
      "artifact": "knowledge/storage/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "storage"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "a2a042efa09df4588bb2cc15d97504b8b31d6e6bb377eb889fa64efba0de2a96"
    },
    {
      "artifact": "knowledge/storage/przechowywanie-danych-dyski-i-partycje.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Przechowywanie danych — dyski i partycje",
        "topic": "storage",
        "source_section": "Przechowywanie danych — dyski i partycje",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "blkid",
          "linux",
          "lsblk",
          "partprobe",
          "print",
          "przechowywanie-danych-dyski-i-partycje",
          "rhcsa",
          "storage"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 5,
      "content_hash": "e7d4aee0363e0d1a978e04bc1733d302605062c8388c550472291d08c20b7855"
    },
    {
      "artifact": "knowledge/storage/systemy-plikow-i-montowanie.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Systemy plików i montowanie",
        "topic": "storage",
        "source_section": "Systemy plików i montowanie",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "findmnt",
          "linux",
          "montowania",
          "mount",
          "rhcsa",
          "storage",
          "systemy-plikow-i-montowanie"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 17,
      "content_hash": "58c842ba2f67f0931b8e3998d65af8b05c42021084fd4aac2ea29cb96b4c0f7d"
    },
    {
      "artifact": "knowledge/storage/zarzdzanie-dyskami-raid.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Zarz■dzanie dyskami RAID",
        "topic": "storage",
        "source_section": "Zarz■dzanie dyskami RAID",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "linux",
          "mdadm",
          "rhcsa",
          "storage",
          "zarzdzanie-dyskami-raid"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 7,
      "content_hash": "1c55fcd6b1352a3c08567657b63c6033b9baf0b6eae05677377d2e4c196e713a"
    },
    {
      "artifact": "knowledge/systemd/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "systemd"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "b5f461f9c876c01cb3a1db42829f3d51ae87535d811a785431e0bf662d981635"
    },
    {
      "artifact": "knowledge/systemd/boot-i-grub.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Boot i GRUB",
        "topic": "systemd",
        "source_section": "Boot i GRUB",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "boot-i-grub",
          "cat",
          "dnf",
          "echo",
          "grub",
          "grub2-install",
          "grub2-set-default",
          "halt",
          "insmod",
          "kernel",
          "linux",
          "ls",
          "lsmod",
          "poweroff",
          "reboot",
          "rhcsa",
          "rpm",
          "sync",
          "sysctl",
          "systemctl",
          "systemd"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 29,
      "content_hash": "cf875b0cd42f80c340ca9d661dbaee281a71e584a0108a63d8c2824ab33f2ceb"
    },
    {
      "artifact": "knowledge/systemd/cron-i-harmonogramowanie-zada.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Cron i harmonogramowanie zada■",
        "topic": "systemd",
        "source_section": "Cron i harmonogramowanie zada■",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "atq",
          "batch",
          "cat",
          "cron-i-harmonogramowanie-zada",
          "linux",
          "list-timers",
          "ls",
          "myapp.timer",
          "rhcsa",
          "run-parts",
          "systemd",
          "systemd-run",
          "timer-name.timer"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 21,
      "content_hash": "f4bbb4d0e10d95f42772864ce1d8c846d495d6587203c819baf80f896c94fe7d"
    },
    {
      "artifact": "knowledge/systemd/systemd-i-zarzdzanie-usugami.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Systemd i zarz■dzanie us■ugami",
        "topic": "systemd",
        "source_section": "Systemd i zarz■dzanie us■ugami",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "daemon-reexec",
          "daemon-reload",
          "emergency.target",
          "get-default",
          "hostnamectl",
          "journalctl",
          "linux",
          "list-dependencies",
          "list-unit-files",
          "localectl",
          "loginctl",
          "rescue.target",
          "rhcsa",
          "service",
          "set-default",
          "systemctl",
          "systemd",
          "systemd-analyze",
          "systemd-i-zarzdzanie-usugami",
          "timedatectl"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 54,
      "content_hash": "a168c358e68695f79003d8531d35470237c96f101f5707abc03d831748e5b907"
    },
    {
      "artifact": "knowledge/systemd/zarzdzanie-pakietami-dnf-rpm.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Zarz■dzanie pakietami (DNF/RPM)",
        "topic": "systemd",
        "source_section": "Zarz■dzanie pakietami (DNF/RPM)",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "aktualizacjami",
          "dnf",
          "linux",
          "package",
          "rhcsa",
          "rpm",
          "subscription-manager",
          "systemd",
          "zarzdzanie-pakietami-dnf-rpm"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 70,
      "content_hash": "6adcd793530a2a432ab7f90c80ee099ee814d382f17367cc1b2d90e233643ba4"
    },
    {
      "artifact": "knowledge/tools/CANONICAL_BUILDER_README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "CANONICAL_BUILDER_README",
        "topic": "tools"
      },
      "references": [],
      "command_count": 0,
      "content_hash": "26a7397b2a2ba425b49af4787183cc0ed1c6474f2a227d4a242faf9cf66edab6"
    },
    {
      "artifact": "knowledge/tools/CONTEXT_PACK_README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "CONTEXT_PACK_README",
        "topic": "tools"
      },
      "references": [],
      "command_count": 0,
      "content_hash": "aacc55273625a3baca980426a834a8e1eaf7fad9102d6221a32e12a13c3ccd49"
    },
    {
      "artifact": "knowledge/tools/INDEX_BUILDER_README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "INDEX_BUILDER_README",
        "topic": "tools"
      },
      "references": [],
      "command_count": 0,
      "content_hash": "3e4481d439c3192634d8ce63a162c0d85baeac2c222cebe8754c747eda2c0d36"
    },
    {
      "artifact": "knowledge/tools/INJECTION_LAYER_README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "INJECTION_LAYER_README",
        "topic": "tools"
      },
      "references": [],
      "command_count": 0,
      "content_hash": "f5695bb07f06bcb800487fb1c06a383cddb2412e9d3cf3eb08016b92da73fc38"
    },
    {
      "artifact": "knowledge/tools/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "tools"
      },
      "references": [],
      "command_count": 0,
      "content_hash": "fe489096261209a2a4ac1bd99a8c6c5c7ba8b4c520d964e87a354c16cc7599c2"
    },
    {
      "artifact": "knowledge/tools/SECTION_PARSER_README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "SECTION_PARSER_README",
        "topic": "tools"
      },
      "references": [
        "knowledge/parsed/rhcsa_sections.json"
      ],
      "command_count": 0,
      "content_hash": "af990c3f853e9839f97eaa2ee234e6b41b62b8f797f450c4206db4ff9ef40a68"
    },
    {
      "artifact": "knowledge/troubleshooting/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "troubleshooting"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "b90c3dc0c1134dc6e85523fd5836970e3863d6aeb5213feff1ac818f039a1a56"
    },
    {
      "artifact": "knowledge/troubleshooting/diagnostyka-i-narzdzia-systemowe.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Diagnostyka i narz■dzia systemowe",
        "topic": "troubleshooting",
        "source_section": "Diagnostyka i narz■dzia systemowe",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "bonnie++",
          "cat",
          "cmd",
          "diagnostyka-i-narzdzia-systemowe",
          "fio",
          "ip",
          "kdump",
          "linux",
          "rhcsa",
          "troubleshooting",
          "valgrind"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 15,
      "content_hash": "7aa0f052225cde7a95ee97763db4e5b5c9dcce30d28974f986ee23bbd4214faf"
    },
    {
      "artifact": "knowledge/troubleshooting/dodatkowe-narzdzia-administracyjne.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Dodatkowe narz■dzia administracyjne",
        "topic": "troubleshooting",
        "source_section": "Dodatkowe narz■dzia administracyjne",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "alternatives",
          "authselect",
          "bash",
          "cat",
          "dodatkowe-narzdzia-administracyjne",
          "fips-mode-setup",
          "ip",
          "linux",
          "ls",
          "memory:mygroup",
          "mygroup",
          "ntsysv",
          "rhcsa",
          "scap-workbench",
          "systemd-cgls",
          "systemd-cgtop",
          "troubleshooting",
          "update-alternatives",
          "update-crypto-polici",
          "wireshark"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 24,
      "content_hash": "b795b3136e658e380c3d1cf2c6f8c79369ef9156bfbbcd2311d6052dd97d7b0f"
    },
    {
      "artifact": "knowledge/troubleshooting/informacje-o-systemie.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Informacje o systemie",
        "topic": "troubleshooting",
        "source_section": "Informacje o systemie",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "baseboard",
          "cat",
          "informacje-o-systemie",
          "iostat",
          "linux",
          "lscpu",
          "lshw",
          "lsmem",
          "lsnuma",
          "lspci",
          "lsusb",
          "nproc",
          "rhcsa",
          "sensors",
          "sensors-detect",
          "troubleshooting",
          "vmstat"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 17,
      "content_hash": "a3a850b66b574e6148e931685a71f07226d2547d22d25045bd7a483f7cda265e"
    },
    {
      "artifact": "knowledge/troubleshooting/logowanie-i-monitorowanie-systemu.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Logowanie i monitorowanie systemu",
        "topic": "troubleshooting",
        "source_section": "Logowanie i monitorowanie systemu",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "aureport",
          "cat",
          "dmesg",
          "grep",
          "journalctl",
          "linux",
          "logowanie-i-monitorowanie-systemu",
          "ls",
          "rhcsa",
          "troubleshooting",
          "udit.log"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 16,
      "content_hash": "bf8236778fe0e41f0f12b1e0d0d03100d2fa5d37e0d789753b773bc1138a4643"
    },
    {
      "artifact": "knowledge/troubleshooting/zarzdzanie-procesami.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Zarz■dzanie procesami",
        "topic": "troubleshooting",
        "source_section": "Zarz■dzanie procesami",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "ctrl+c",
          "ctrl+d",
          "ctrl+z",
          "htop",
          "jobs",
          "linux",
          "lsof",
          "ps",
          "pstree",
          "rhcsa",
          "top",
          "troubleshooting",
          "uptime",
          "wait",
          "zarzdzanie-procesami"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 16,
      "content_hash": "152c55739440bf1044828cd7e32a24d55e721f087f371fcdf000d4e642f3cfa1"
    },
    {
      "artifact": "knowledge/users/README.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "README",
        "topic": "users"
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 0,
      "content_hash": "dd521b7f7a4da905c14814ffa4884519c7bd373de2808a538e5ad82498aca364"
    },
    {
      "artifact": "knowledge/users/zarzdzanie-grupami.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Zarz■dzanie grupami",
        "topic": "users",
        "source_section": "Zarz■dzanie grupami",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "group",
          "linux",
          "rhcsa",
          "usermod",
          "users",
          "zarzdzanie-grupami"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 3,
      "content_hash": "4ab3e9e0eeea2b2099f33862557dd003696bc7c781688fa0ef1a3040bba5c7b3"
    },
    {
      "artifact": "knowledge/users/zarzdzanie-uytkownikami.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "Zarz■dzanie u■ytkownikami",
        "topic": "users",
        "source_section": "Zarz■dzanie u■ytkownikami",
        "source_pdf": "knowledge/source/RHCSA_Command_Library (1).pdf",
        "generated_from": "knowledge/canonical/rhcsa_commands.json",
        "tags": [
          "cat",
          "dniach",
          "grpck",
          "id",
          "last",
          "lastb",
          "lastlog",
          "linux",
          "lslogins",
          "pwck",
          "rhcsa",
          "user",
          "useradd",
          "usermod",
          "users",
          "vigr",
          "vipw",
          "visudo",
          "w",
          "who",
          "whoami",
          "zalogowanego",
          "zarzdzanie-uytkownikami"
        ]
      },
      "references": [
        "knowledge/canonical/rhcsa_commands.json"
      ],
      "command_count": 46,
      "content_hash": "c3474eb64d5f661160cb9aed5b2f0b9449d9a5f4cdb76fe0f792616637c086d0"
    },
    {
      "artifact": "knowledge/validator/validation_report.md",
      "artifact_type": "markdown",
      "metadata": {
        "title": "validation_report",
        "topic": "validator"
      },
      "references": [],
      "command_count": 0,
      "content_hash": "7f8800f37b822121f9a6d840c26e81abc891ab471bfa90923080d6b296c63ea9"
    }
  ]
}
```

## `runtime/tools/epistemic_registry.py`

- size: 13781 bytes
- sha256: `1fae84f5d3258b52f32a2b377f79ef67e1cee77732ae802dab71609650e478d1`
- category: tooling

```python
#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"
PROVENANCE_REGISTRY_PATH = PROJECT_ROOT / "provenance_registry.json"
CONTRADICTION_REGISTRY_PATH = PROJECT_ROOT / "contradiction_registry.json"

FRONTMATTER_KEYS = {
    "title",
    "topic",
    "source_section",
    "source_pdf",
    "generated_from",
    "tags",
}


@dataclass(frozen=True)
class KnowledgeArtifact:
    path: Path
    artifact_type: str
    metadata: dict[str, Any]
    references: tuple[str, ...]
    commands: tuple[str, ...]
    content_hash: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_command(value: str) -> str:
    return " ".join(value.strip().split())


def _file_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return path.as_posix()


def _parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    payload: dict[str, Any] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip()
    return payload


def _parse_tags(value: str) -> list[str]:
    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [item.strip() for item in text.split(",") if item.strip()]


def _extract_markdown_commands(text: str) -> list[str]:
    return [match.strip() for match in re.findall(r"^### `([^`]+)`", text, flags=re.MULTILINE) if match.strip()]


def _extract_example_commands(payload: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    command = str(payload.get("command", "")).strip()
    if command:
        commands.append(command)
    for example in payload.get("examples", []):
        if isinstance(example, dict):
            sample = str(example.get("input", "")).strip()
            if sample:
                commands.append(sample)
    return commands


def _extract_generic_json_commands(payload: Any) -> list[str]:
    commands: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"command", "commands", "related_commands"}:
                    if isinstance(value, str):
                        cleaned = value.strip()
                        if cleaned:
                            commands.append(cleaned)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and item.strip():
                                commands.append(item.strip())
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return commands


def _extract_internal_references(text: str, current_path: Path, known_paths: set[str]) -> list[str]:
    refs: set[str] = set()
    markdown_link_matches = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    code_path_matches = re.findall(r"`([^`\n]*knowledge/[^`\n]+)`", text)
    frontmatter_path_matches = re.findall(r"(?m)^(?:source_pdf|generated_from):\s+(.+)$", text)
    candidates = markdown_link_matches + code_path_matches + frontmatter_path_matches

    for candidate in candidates:
        raw = candidate.strip().strip("<>").strip()
        if not raw:
            continue
        normalized = raw.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if normalized.startswith("../"):
            resolved = (current_path.parent / normalized).resolve()
            try:
                normalized = str(resolved.relative_to(PROJECT_ROOT)).replace("\\", "/")
            except ValueError:
                continue
        if normalized in known_paths:
            refs.add(normalized)
    return sorted(refs)


def _build_artifact(path: Path, known_paths: set[str]) -> KnowledgeArtifact:
    text = _read_text(path)
    if path.suffix == ".md":
        frontmatter = _parse_frontmatter(text)
        metadata = {key: value for key, value in frontmatter.items() if key in FRONTMATTER_KEYS}
        if "tags" in metadata:
            metadata["tags"] = _parse_tags(str(metadata["tags"]))
        metadata.setdefault("title", path.stem)
        metadata.setdefault("topic", path.parent.name)
        commands = tuple(dict.fromkeys(_extract_markdown_commands(text)))
        references = tuple(_extract_internal_references(text, path, known_paths))
        return KnowledgeArtifact(
            path=path,
            artifact_type="markdown",
            metadata=metadata,
            references=references,
            commands=commands,
            content_hash=_file_hash(text),
        )

    payload = json.loads(text)
    if isinstance(payload, dict):
        metadata = {
            "id": payload.get("id", path.stem),
            "category": payload.get("category", ""),
            "risk": payload.get("risk", ""),
            "tags": [str(item).strip() for item in payload.get("tags", []) if str(item).strip()],
        }
        commands = tuple(dict.fromkeys(_extract_example_commands(payload)))
        artifact_type = "json_example" if path.parent.name == "examples" else "json_document"
    else:
        metadata = {
            "id": path.stem,
            "category": path.parent.name,
            "risk": "",
            "tags": [],
        }
        commands = tuple(dict.fromkeys(_extract_generic_json_commands(payload)))
        artifact_type = "json_index"
    references = tuple(_extract_internal_references(text, path, known_paths))
    return KnowledgeArtifact(
        path=path,
        artifact_type=artifact_type,
        metadata=metadata,
        references=references,
        commands=commands,
        content_hash=_file_hash(text),
    )


def discover_knowledge_artifacts(root: Path = KNOWLEDGE_ROOT) -> tuple[KnowledgeArtifact, ...]:
    candidate_paths = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".md", ".json"}:
            continue
        if "__pycache__" in path.parts:
            continue
        candidate_paths.append(path)
    known_paths = {str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") for path in candidate_paths}
    artifacts = [_build_artifact(path, known_paths) for path in sorted(candidate_paths)]
    return tuple(artifacts)


def build_reference_graph(artifacts: tuple[KnowledgeArtifact, ...]) -> dict[str, list[str]]:
    return {
        _display_path(artifact.path): list(artifact.references)
        for artifact in artifacts
    }


def detect_self_references(graph: dict[str, list[str]]) -> list[dict[str, Any]]:
    findings = []
    for node, refs in sorted(graph.items()):
        if node in refs:
            findings.append(
                {
                    "type": "self_reference",
                    "artifact": node,
                    "reference": node,
                    "status": "unresolved",
                }
            )
    return findings


def detect_circular_references(graph: dict[str, list[str]]) -> list[dict[str, Any]]:
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str, path: list[str]) -> None:
        for neighbor in graph.get(node, []):
            if neighbor not in graph:
                continue
            if neighbor in path:
                cycle = path[path.index(neighbor):] + [neighbor]
                normalized_cycle = _normalize_cycle(cycle)
                cycles.add(normalized_cycle)
                continue
            visit(neighbor, path + [neighbor])

    for node in sorted(graph):
        visit(node, [node])

    findings = []
    for cycle in sorted(cycles):
        findings.append(
            {
                "type": "circular_reference",
                "cycle": list(cycle),
                "status": "unresolved",
            }
        )
    return findings


def _normalize_cycle(cycle: list[str]) -> tuple[str, ...]:
    if len(cycle) <= 1:
        return tuple(cycle)
    ring = cycle[:-1]
    rotations = [tuple(ring[index:] + ring[:index] + [ring[index]]) for index in range(len(ring))]
    return min(rotations)


def detect_duplicate_commands(artifacts: tuple[KnowledgeArtifact, ...]) -> list[dict[str, Any]]:
    command_map: dict[str, list[str]] = defaultdict(list)
    for artifact in artifacts:
        if artifact.artifact_type not in {"markdown", "json_example"}:
            continue
        rel_path = _display_path(artifact.path)
        for command in artifact.commands:
            normalized = _normalize_command(command)
            if normalized:
                command_map[normalized].append(rel_path)

    findings = []
    for command, sources in sorted(command_map.items()):
        unique_sources = sorted(dict.fromkeys(sources))
        if len(unique_sources) > 1:
            findings.append(
                {
                    "type": "duplicate_command",
                    "command": command,
                    "sources": unique_sources,
                    "status": "unresolved",
                }
            )
    return findings


def detect_duplicate_artifacts(artifacts: tuple[KnowledgeArtifact, ...]) -> list[dict[str, Any]]:
    hash_map: dict[str, list[str]] = defaultdict(list)
    for artifact in artifacts:
        rel_path = _display_path(artifact.path)
        hash_map[artifact.content_hash].append(rel_path)

    findings = []
    for content_hash, sources in sorted(hash_map.items()):
        unique_sources = sorted(dict.fromkeys(sources))
        if len(unique_sources) > 1:
            findings.append(
                {
                    "type": "duplicate_content",
                    "content_hash": content_hash,
                    "sources": unique_sources,
                    "status": "unresolved",
                }
            )
    return findings


def build_provenance_registry(artifacts: tuple[KnowledgeArtifact, ...]) -> dict[str, Any]:
    records = []
    for artifact in artifacts:
        rel_path = _display_path(artifact.path)
        record = {
            "artifact": rel_path,
            "artifact_type": artifact.artifact_type,
            "metadata": artifact.metadata,
            "references": list(artifact.references),
            "command_count": len(artifact.commands),
            "content_hash": artifact.content_hash,
        }
        records.append(record)
    return {
        "generated_at": dt.datetime.now().isoformat(),
        "root": "knowledge",
        "artifact_count": len(records),
        "records": records,
    }


def build_contradiction_registry(artifacts: tuple[KnowledgeArtifact, ...]) -> dict[str, Any]:
    graph = build_reference_graph(artifacts)
    self_references = detect_self_references(graph)
    circular_references = detect_circular_references(graph)
    duplicate_commands = detect_duplicate_commands(artifacts)
    duplicate_artifacts = detect_duplicate_artifacts(artifacts)
    return {
        "generated_at": dt.datetime.now().isoformat(),
        "root": "knowledge",
        "policy": {
            "automatic_resolution": False,
            "note": "Contradictions and epistemic conflicts are reported only. No automatic resolution is performed.",
        },
        "summary": {
            "self_reference_count": len(self_references),
            "circular_reference_count": len(circular_references),
            "duplicate_command_count": len(duplicate_commands),
            "duplicate_artifact_count": len(duplicate_artifacts),
        },
        "reference_graph": graph,
        "self_references": self_references,
        "circular_references": circular_references,
        "duplicate_commands": duplicate_commands,
        "duplicate_artifacts": duplicate_artifacts,
    }


def write_registries(
    provenance_path: Path = PROVENANCE_REGISTRY_PATH,
    contradiction_path: Path = CONTRADICTION_REGISTRY_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifacts = discover_knowledge_artifacts()
    provenance = build_provenance_registry(artifacts)
    contradictions = build_contradiction_registry(artifacts)
    provenance_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    contradiction_path.write_text(json.dumps(contradictions, indent=2, ensure_ascii=False), encoding="utf-8")
    return provenance, contradictions


def main() -> int:
    provenance, contradictions = write_registries()
    print(
        json.dumps(
            {
                "provenance_registry": str(PROVENANCE_REGISTRY_PATH.relative_to(PROJECT_ROOT)),
                "contradiction_registry": str(CONTRADICTION_REGISTRY_PATH.relative_to(PROJECT_ROOT)),
                "artifact_count": provenance["artifact_count"],
                "duplicate_command_count": contradictions["summary"]["duplicate_command_count"],
                "circular_reference_count": contradictions["summary"]["circular_reference_count"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```



