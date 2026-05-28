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

