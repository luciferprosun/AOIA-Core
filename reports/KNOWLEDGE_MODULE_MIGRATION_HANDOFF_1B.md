# Knowledge Module Migration Handoff 1B

This handoff records deferred compatibility work only. German Law is the sole production registration in Control Plane 1B.

## UNIX Hat

The existing UNIX Hat can later expose its current descriptor and bounded retrieval through a logical `KnowledgeModuleDescriptor`, a reviewed local `KnowledgeModuleInstanceDescriptor`, and an adapter implementing `verify()` plus the generic `query_plan()` boundary. Its current routing, corpus, and retrieval behavior should remain behind that adapter; it must not be copied into generic profile or planning logic.

## Linux knowledge

Linux knowledge can later become an independently versioned Knowledge Pack and logical module. A migration should pin its current corpus/index evidence to an instance, translate existing retrieval output into `KnowledgeEvidenceBundle`, and preserve current Linux source provenance and budgets.

## Python knowledge

Python knowledge can later use the same instance boundary. Its source inventory, validation evidence, and retrieval adapter should remain independently removable and disabled by default, with Python-specific filters handled only by its adapter.

## Legacy adapters retained

- `KnowledgeHub1A`, `KnowledgeModuleSelection`, and `KnowledgeModuleQuery` remain compatibility contracts.
- `aoia-knowledge-query` remains the one-module German Law compatibility CLI.
- Existing UNIX, Linux, and Python routing/retrieval adapters are unchanged.
- `GermanLawModuleAdapter` remains the only production external-process adapter.

## Intentionally deferred

- UNIX, Linux, and Python production-module registration.
- Persistent profile storage and final checkbox UI.
- Provider context construction and provider integration.
- Remote service transport, networking, failover, retries, async workers, and background loops.
- Semantic cross-module deduplication, ranking, contradiction detection, and conflict resolution.
