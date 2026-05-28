# AOIA Memory Ontology

Date: 2026-05-23
Phase: Memory Ontology Foundation

## Doctrine

Memory is not one store.
It is a layered epistemic system with different authority, mutability, and replay rules.

AOIA foundational layers:
- L0 Ephemeral Runtime State
- L1 Operational Logs
- L2 Reasoning Traces
- L3 Provenance Records
- L4 Evidence Store
- L5 Contradiction Records

## L0 — Ephemeral Runtime State

Purpose:
- support active runtime continuity during a session

Authority level:
- lowest epistemic authority

Mutability rules:
- fully mutable
- replaceable
- expected to drift during execution

Retention policy:
- short-lived
- may be rotated or overwritten

Access policy:
- runtime internal
- status inspection allowed

Contamination risks:
- if promoted into evidence, transient state becomes false memory

Replay requirements:
- replay not required for strict epistemic history
- useful only for short continuity restoration

## L1 — Operational Logs

Purpose:
- record what the runtime did

Authority level:
- procedural authority, not truth authority

Mutability rules:
- append-only preferred
- correction by later append, not silent rewrite

Retention policy:
- medium retention
- may be archived by session or by period

Access policy:
- operator-readable
- audit-usable

Contamination risks:
- command traces can be mistaken for verified evidence
- execution success can be mistaken for factual truth

Replay requirements:
- must support chronological replay of actions

## L2 — Reasoning Traces

Purpose:
- preserve epistemic rationale, uncertainty, route choice, and review triggers

Authority level:
- inferential authority, below evidence and provenance

Mutability rules:
- append-only
- never silently edited in place after emission

Retention policy:
- retain for audit and debugging
- may be sampled for summaries, but raw trace should remain replayable

Access policy:
- restricted runtime/audit use
- not to be treated as truth source

Contamination risks:
- reasoning can be mistaken for evidence
- summaries can drift away from exact reasoning state

Replay requirements:
- replayable by session and event order

## L3 — Provenance Records

Purpose:
- identify source origin, artifact identity, references, and fingerprints

Authority level:
- structural truth about source lineage

Mutability rules:
- append-only or versioned regeneration
- no silent mutation of prior source identity

Retention policy:
- long retention
- must survive retrieval and archive transitions

Access policy:
- runtime readable
- audit readable

Contamination risks:
- stale registries can misrepresent current source state
- generated records can be mistaken for source content itself

Replay requirements:
- deterministic regeneration compatibility required

## L4 — Evidence Store

Purpose:
- preserve factual support objects used in local answer formation or external inspection

Authority level:
- higher than logs and reasoning, below provenance-backed source identity if evidence is derived

Mutability rules:
- immutable once captured
- corrections require new evidence object, not overwrite

Retention policy:
- long retention when referenced in reasoning or outcomes

Access policy:
- runtime and audit use
- careful exposure in user-visible summaries

Contamination risks:
- logs or summaries may be promoted as evidence without validation
- browser snapshots may include noisy or partial captures

Replay requirements:
- evidence object must retain fingerprint, capture time, and source linkage

## L5 — Contradiction Records

Purpose:
- preserve unresolved epistemic conflicts as signals

Authority level:
- meta-epistemic authority

Mutability rules:
- append-only conflict history
- resolution creates a new state entry, not erasure

Retention policy:
- long retention
- contradictions must remain visible even after later interpretation

Access policy:
- runtime readable
- audit critical

Contamination risks:
- contradictions may be incorrectly treated as errors to delete
- automated resolution may erase epistemic pressure

Replay requirements:
- contradiction emergence and later status changes must be replayable

## Ordering Principle

Recommended trust ordering:
- source provenance and fingerprinting constrain evidence identity
- evidence constrains reasoning
- reasoning constrains output
- contradictions constrain confidence
- operational logs never outrank evidence
- ephemeral state never outranks any persisted epistemic layer

## Core Rule

L1 is not L4.
L2 is not L4.
L5 is not failure.
