# Filesystem Ontology Layout

Date: 2026-05-23
Phase: Memory Ontology Foundation

## Canonical Ontology-Aware Layout

```text
/runtime_state
/operational_logs
/reasoning
/provenance
/evidence
/contradictions
/archive
/retrieval_cache
```

## `/runtime_state`

Purpose:
- L0 ephemeral session continuity

May persist:
- active session state
- current cwd
- active browser state
- active model selection

Must expire:
- old transient state snapshots
- stale session continuity state

Must remain immutable:
- none

Must never enter canonical evidence:
- transient browser state
- current task labels
- short-term UI state

## `/operational_logs`

Purpose:
- L1 action chronology

May persist:
- command logs
- session logs
- browser event logs
- error logs

Must expire:
- optionally rotated raw debug logs

Must remain immutable:
- appended event records once written

Must never enter canonical evidence:
- execution success by itself
- approval prompts
- routine navigation traces

## `/reasoning`

Purpose:
- L2 inferential trace

May persist:
- route decisions
- confidence reasoning
- manual review triggers
- unknown-response rationale

Must expire:
- no forced expiry by default; archive instead

Must remain immutable:
- raw reasoning events once emitted

Must never enter canonical evidence:
- speculative inference
- confidence labels alone

## `/provenance`

Purpose:
- L3 source identity and lineage

May persist:
- source fingerprints
- artifact metadata
- internal reference graphs
- trust version identifiers

Must expire:
- none; supersession should be versioned

Must remain immutable:
- previous provenance snapshots once published

Must never enter canonical evidence:
- convenience summaries without source fingerprint

## `/evidence`

Purpose:
- L4 immutable support objects

May persist:
- captured page text snapshots
- retrieved artifact references
- validated local evidence objects

Must expire:
- unpromoted temporary captures

Must remain immutable:
- evidence objects after capture and fingerprint assignment

Must never enter canonical evidence:
- raw operational logs
- daily vault summaries
- user-facing paraphrases without source linkage

## `/contradictions`

Purpose:
- L5 epistemic conflict registry

May persist:
- unresolved contradictions
- duplicate-command conflicts
- status transitions
- contradiction lineage

Must expire:
- none automatically

Must remain immutable:
- contradiction creation records

Must never enter canonical evidence:
- auto-resolved or silently suppressed conflicts

## `/archive`

Purpose:
- preserved prior snapshots and retired layer outputs

May persist:
- old ontology snapshots
- retired but preserved logs
- lineage-preserving exports

Must expire:
- nothing automatically; operator policy driven

Must remain immutable:
- archived records after sealing

Must never enter canonical evidence:
- archive indexes alone without object linkage

## `/retrieval_cache`

Purpose:
- acceleration layer only

May persist:
- deterministic indexes
- derived lookup tables
- search caches

Must expire:
- stale cache artifacts after source change

Must remain immutable:
- no; cache may be rebuilt

Must never enter canonical evidence:
- cache hits by themselves

## Core Rule

Only `/evidence`, `/provenance`, and `/contradictions` may carry high epistemic persistence.

`/runtime_state`, `/operational_logs`, and `/retrieval_cache` support execution, not truth authority.
