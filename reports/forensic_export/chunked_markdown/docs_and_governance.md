# Docs And Governance

Architecture doctrine, ADRs, governance/archive material, and phase reports.

Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

Files in this chunk: 81

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/README.md`

- size: 740 bytes
- sha256: `6006cfb45af9ab4d95df29b2176e884a184e29bc487054cf211ff93dda7b8bf0`
- category: governance

```markdown
# AOIA Anti-Hallucination Engineering Case Study

This case study is reserved for AOIA anti-hallucination engineering, provenance boundaries, deterministic runtime behavior, and epistemic framework design.

## Scope

Allowed future material:

- AOIA runtime architecture reports
- anti-hallucination and provenance policies
- deterministic routing and retrieval boundary documents
- provider export reviews specific to AOIA
- lineage records for AOIA engineering review

## Boundary

This case study is not evidence for LSC scientific claims.

LSC scientific anomaly material must stay in the `lsc_neutrino` case study unless a future cross-case reference policy is approved.

## Phase 1 Status

Skeleton only. No files have been migrated.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/DEPENDENCY_BOUNDARY_ANALYSIS.md`

- size: 2230 bytes
- sha256: `6e15acd381d7cb11f6cb1436d49532ca1e14d4b183fdfb5d31537ce376dbcb7e`
- category: governance

```markdown
# Dependency Boundary Analysis

Phase: 3 - governance preparation
Status: analysis only

## Purpose

Identify future dependency risks without modifying dependencies.

## Cross-Domain Contamination Risks

- AOIA engineering documents mention LSC separation and could be mistaken for LSC scientific evidence.
- Shared archive language can blur framework authority and runtime authority.
- Provider reports can mix recommendations, audits, and claims without source boundaries.

## Runtime To Archive Risks

- Runtime may accidentally read archive material as live policy.
- Archive reports may be treated as runtime configuration.
- Review notes may be mistaken for enforced constraints.

## Archive To Runtime Risks

- Governance design could be copied into runtime without enforcement tests.
- Provider audit recommendations could be implemented as code without provenance review.
- Derived summaries could override source reports.

## LSC To AOIA Contamination Vectors

- mixed-root historical reports
- shared MHLM/MHSR terminology
- old `LST` aliases
- documents describing repository separation

## AOIA To LSC Contamination Vectors

- AOIA anti-hallucination claims used as credibility support for LSC
- model/provider consensus treated as scientific validation
- runtime provenance concepts applied to scientific evidence without domain review

## Shared Utility Risks

Future shared utilities may create risk if they:

- read both case studies without explicit case scope
- write shared provenance records
- normalize prompts across domains
- collapse provider aliases globally

## Dependency Creep Risks

- temporary bridge modules becoming permanent
- planner fallback depending on archive summaries
- retrieval code importing governance review data
- provider adapters gaining authority logic

## Split-Brain Routing Risks

Split-brain routing can occur when:

- multiple routing layers classify the same input differently
- external URLs bypass one boundary but enter another
- RHCSA local retrieval and external review share fallback paths
- old orchestration remnants remain callable

## Recommendation

Freeze dependency boundaries before implementing enforcement.

Do not modify runtime dependencies in this phase.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/MEMORY_DOMAIN_SPLIT_PLAN.md`

- size: 1870 bytes
- sha256: `3df1f85ab3f9b1e8252b3dd5283d32410eea709a73e18215a7a695a8507d11dc`
- category: memory

```markdown
# Memory Domain Split Plan

Phase: 3 - governance preparation
Status: conceptual target design only

## Purpose

Describe the future conceptual split for AOIA memory domains.

This does not refactor `memory.py`.

## L0 - Ephemeral Runtime

Purpose:

- current request state
- temporary routing state
- process-local execution state

Persistence:

- none by default

Forbidden:

- evidence writes
- provenance writes
- authority decisions

## L1 - Operational Logs

Purpose:

- replay support
- execution diagnostics
- tool and runtime event history

Persistence:

- append-only operational log storage

Forbidden:

- evidence promotion
- canonical authority

## L2 - Reasoning Traces

Purpose:

- non-authoritative reasoning context
- audit of model/planner reasoning surfaces where available

Persistence:

- quarantined trace storage

Forbidden:

- retrieval as evidence
- promotion to L4
- provenance source status

## L3 - Provenance Records

Purpose:

- source chains
- import events
- normalization events
- derivation records

Persistence:

- append-only provenance log

Forbidden:

- ungrounded provider claims
- reasoning trace as source

## L4 - Immutable Evidence

Purpose:

- externally grounded evidence artifacts
- source documents
- verified raw imports

Persistence:

- immutable or content-addressed storage in future implementation

Forbidden:

- operational logs
- runtime state
- model output without external provenance

## L5 - Contradiction Registry

Purpose:

- preserve contradictions
- record review status
- prevent false resolution

Persistence:

- append-only contradiction registry

Forbidden:

- automatic contradiction resolution
- deletion as cleanup

## Future Physical Split

Future implementation should separate modules and storage paths by layer.

`memory.py` must not remain the shared write surface for multiple authority layers.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/contracts/RUNTIME_SAFETY_CONTRACTS.md`

- size: 2030 bytes
- sha256: `72a07359a149c1827652b381db20169c6f88c1b0a3f978f19481b920c920681d`
- category: governance

```markdown
# Runtime Safety Contracts

Phase: 3 - governance preparation
Status: design contract only

## Runtime Invariants

- Runtime state is not canonical authority.
- Runtime logs are not evidence.
- Retrieval results require provenance boundaries before use as evidence.
- External URL handling must not enter local RHCSA retrieval by default.
- Planner fallback must not expand authority.

## Provenance Invariants

- Every evidence artifact requires provenance.
- Unknown provider attribution remains `unknown`.
- Normalized artifacts must reference raw artifacts.
- Derived artifacts must reference their inputs.

## Forbidden Transitions

- reasoning trace -> immutable evidence
- operational log -> immutable evidence
- runtime state -> provenance
- provider response -> evidence without source
- archive review note -> runtime rule without migration phase
- LSC scientific artifact -> AOIA runtime validation

## Contradiction Constraints

- contradictions are first-class records
- contradiction records are not evidence by themselves
- contradictions are not auto-resolved
- review status must be explicit

## Session Isolation Principles

Sessions should remain isolated by:

- case study
- provider
- timestamp
- source system
- artifact class

AOIA sessions must not merge with LSC sessions by default.

## Replay Safety Assumptions

Replay reconstructs process, not truth.

Replay requires:

- immutable or append-only inputs
- stable provenance references
- explicit source paths
- no hidden runtime mutation

## Planner Fallback Restrictions

Planner fallback must not:

- bypass retrieval boundaries
- promote local knowledge to external review
- promote reasoning traces to evidence
- turn uncertainty into authority
- write canonical governance records

## Trust Boundary Definitions

Trusted only after validation:

- source artifacts
- provenance records
- operator-reviewed classifications

Untrusted by default:

- model output
- runtime state
- operational logs
- reasoning traces
- inferred provider attribution
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/enforcement/ENFORCEMENT_LAYER_DESIGN.md`

- size: 2524 bytes
- sha256: `94b6d017862c7bc8d9d5fd61a1860fa7814fcdf2940d4fe01ba02114fc6794c2`
- category: governance

```markdown
# Enforcement Layer Design

Phase: 3 - governance preparation
Status: target architecture only

## Purpose

Define the future enforcement layer required to make AOIA memory, provenance, and contradiction boundaries real.

## L0-L5 Write Boundaries

L0 Ephemeral runtime:

- may write temporary runtime state only
- must not write evidence or provenance

L1 Operational logs:

- may write execution and event logs
- must not promote logs into evidence

L2 Reasoning traces:

- may write non-authoritative reasoning context
- must remain quarantined from retrieval-as-evidence

L3 Provenance records:

- may write source, import, and derivation records
- must reference raw or normalized artifacts

L4 Immutable evidence:

- may receive externally grounded evidence only
- must require provenance validation before write

L5 Contradiction registry:

- may record contradiction events and review status
- must not auto-resolve contradictions

## Forbidden Cross-Layer Writes

Forbidden:

- L0 -> L3/L4/L5 direct authority writes
- L1 -> L4 evidence promotion
- L2 -> L4 evidence promotion
- planner output -> provenance without external source
- provider response -> evidence without provenance record
- runtime state -> canonical authority

## Evidence Promotion Restrictions

Evidence promotion should require:

- source artifact
- provenance record
- case-study assignment
- human or policy review status
- contradiction check

## Provenance Validation Concepts

Validation should confirm:

- source exists
- source class is allowed
- case study is explicit
- chain depth is bounded or reviewed
- provider attribution is known or marked unknown

## Append-Only Principles

Future enforcement should append new events instead of rewriting old records.

Corrections should be additional events, not mutation of prior evidence.

## Runtime Isolation Concepts

Runtime systems should not read archive material as live routing authority.

Archive review material can inform future design only through approved migration or policy phases.

## Contradiction Write Rules

Contradiction writes should record:

- source A
- source B
- contradiction type
- severity
- case-study scope
- review status

No contradiction should be auto-closed by model agreement.

## Planner Inheritance Restrictions

Planner outputs must not inherit authority from:

- prompt text
- reasoning trace
- model confidence
- prior operational log

Planner outputs may reference provenance records only when explicitly supplied by a validated retrieval path.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/archive/AOIA_MASTER_LIBRARY/MASTER_INDEX.md`

- size: 4228 bytes
- sha256: `7a83ee95d02b39e9c06e23e852e32e5967d2d28bdae9561d51d4f9860b880d49`
- category: governance

```markdown
# AOIA Master Library Index

Imported: 2026-05-24
Archive path: `MHLM_MHSR/case_studies/anti_hallucination_epi_app/archive/AOIA_MASTER_LIBRARY/`
Source file: `/home/l/Desktop/AOIA_Master_Library.pdf`
Archived filename: `AOIA_Master_Library.pdf`

## PDF Metadata

- title: `(anonymous)`
- author: `(anonymous)`
- producer: `ReportLab PDF Library`
- creation date: 2026-05-23 21:35:16 CEST
- pages: 127
- encrypted: no
- file size at import: 272,701 bytes

## Category

AOIA forensic archive source.

The PDF describes itself as a consolidated AOIA audit, governance, routing, epistemic safety, runtime architecture, and deterministic orchestration research library.

## Provider Classification Table

| Document | Detected provider | Category | Likely relevance | Ambiguity notes | Contamination concerns |
|---|---|---|---|---|---|
| `AOIA_Audit_Wave2_2305 (1).md` | claude | forensic audit | high | PDF text identifies Claude Sonnet | audit is engineering review, not LSC evidence |
| `AOIA_Audit_Wave2_2305 (2).md` | claude | forensic audit | high | PDF text identifies Claude Sonnet | audit is engineering review, not LSC evidence |
| `AOIA_Audit_Wave2_2305.md` | claude | forensic audit | high | PDF text identifies Claude Sonnet | audit is engineering review, not LSC evidence |
| `AOIA_CURRENT_STATE_SUMMARY.md` | unknown | current-state summary | high | no provider detected in index scan | do not promote summary to evidence without source chain |
| `AOIA_Safety_Governance_Review_2305-1.md` | claude | governance review | high | PDF text identifies Claude Sonnet | governance review is not runtime authority |
| `AOIA_Safety_Governance_Review_2305-2.md` | claude | governance review | high | PDF text identifies Claude Sonnet | governance review is not runtime authority |
| `AOIA_Safety_Governance_Review_2305.md` | claude | governance review | high | PDF text identifies Claude Sonnet | governance review is not runtime authority |
| `CODEX_RAPORT_1925.md` | codex | codex report | high | filename identifies Codex | operational report, not canonical evidence |
| `CODEX_RAPORT_2004.md` | codex | codex report | high | filename identifies Codex | operational report, not canonical evidence |
| `CODEX_RAPORT_2011.md` | codex | codex report | high | filename identifies Codex | operational report, not canonical evidence |
| `CODEX_RAPORT_2028.md` | codex | codex report | high | filename identifies Codex | operational report, not canonical evidence |
| `DETERMINISM_AUDIT.md` | unknown | determinism audit | high | no provider detected in index scan | must remain AOIA engineering material |
| `EPISTEMIC_RISK_REPORT.md` | unknown | epistemic risk report | high | no provider detected in index scan | must not become LSC scientific evidence |
| `FORENSIC_ARCHITECTURE_REPORT.md` | unknown | architecture report | high | no provider detected in index scan | architecture claims require source references |
| `MEMORY_FLOW_ANALYSIS.md` | unknown | memory analysis | high | no provider detected in index scan | memory/runtime state contamination risk |
| `MODULE_DEPENDENCY_MAP.md` | unknown | dependency map | medium | no provider detected in index scan | map is review material, not runtime authority |
| `NEXT_STEPS_RECOMMENDATION.md` | unknown | recommendation | medium | no provider detected in index scan | recommendation is derived guidance |
| `RAPORT_16-10.md` | unknown | summary report | high | no provider detected from filename alone | operational summary, not canonical evidence |
| `REPOSITORY_TREE.md` | unknown | repository tree | medium | generated structure artifact | may include mixed historical structure |
| `SYSTEM_EXECUTION_FLOW.md` | unknown | execution flow | high | no provider detected in index scan | execution-flow claims need code verification |

## Import Decision

The PDF was copied once into `AOIA_MASTER_LIBRARY/`.

Individual embedded documents were not extracted or duplicated during Phase 2.

## Contamination Controls

- Treat this PDF as AOIA engineering archive material only.
- Do not use it as LSC scientific evidence.
- Do not treat provider consensus as truth.
- Do not promote reasoning traces or recommendations to evidence.
- Preserve provider uncertainty as `unknown`.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/governance/GOVERNANCE_MODEL.md`

- size: 2035 bytes
- sha256: `8d8108e1483426302c735f4d3e64e86a2b6454cad3a2bf2c3edf5f9c57185b60`
- category: governance

```markdown
# AOIA Governance Model

Phase: 3 - governance preparation
Status: design only

## Purpose

Define governance boundaries for AOIA anti-hallucination engineering without implementing runtime enforcement.

## Authority Domains

### AOIA-Core

AOIA-Core is the runtime engineering domain.

Authority scope:

- deterministic routing behavior
- runtime safety boundaries
- provider execution containment
- retrieval boundary design
- memory/provenance implementation plans

AOIA-Core is not scientific authority for LSC claims.

### MHLM/MHSR

MHLM/MHSR is the framework and review domain.

Authority scope:

- case-study separation
- migration staging
- archival policy
- provenance doctrine
- lineage and contradiction review structures

MHLM/MHSR does not replace AOIA runtime code authority and does not execute runtime policy.

### LSC

LSC is the scientific anomaly case-study domain.

Authority scope:

- scientific anomaly artifacts
- scientific lineage
- LSC evidence chains

LSC artifacts are not AOIA runtime evidence.

## Conflict Resolution Principles

- Domain authority must be explicit before a claim is accepted.
- AOIA engineering claims and LSC scientific claims must not validate each other by proximity.
- Provider consensus is not proof.
- Unknown provenance remains unresolved until reviewed.
- Contradictions are recorded before any resolution attempt.

## Operator Override Principles

Operator override is a governance event, not silent authority.

Future override records should include:

- operator identity or role
- timestamp
- affected artifact or runtime boundary
- reason
- rollback expectation
- review requirement

Operator override must not convert reasoning traces into evidence.

## Human Review Concepts

Human review should be required for:

- cross-domain classifications
- evidence promotion
- contradiction closure
- provider attribution uncertainty
- runtime policy changes
- archive-to-runtime influence

## Non-Implementation Rule

This document does not implement governance runtime behavior.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/lineage/LINEAGE_POLICY.md`

- size: 1243 bytes
- sha256: `5cc3d91f1e41c9cb19c69f748189d3934e0d3626030979343cebc877d1b56c6a`
- category: governance

```markdown
# AOIA Forensic Lineage Policy

Phase: 2 AOIA forensic migration

## Purpose

Prepare lineage rules for future AOIA forensic migration without synthesizing lineage yet.

## Append-Only Principle

Lineage records should be append-only.

Existing lineage records must not be rewritten to force consistency. Corrections should be added as later events.

## Replay Concept

A future lineage system should allow a reviewer to replay:

- source import
- normalization
- provider classification
- contradiction registration
- synthesis creation

Replay does not prove correctness. It documents process.

## Provenance Inheritance

Derived artifacts inherit provenance from the raw or normalized artifacts they reference.

Provider output does not become evidence without a provenance record.

## Non-Authoritative Reasoning Traces

Reasoning traces may support session reconstruction, but they are not evidence.

They must not be promoted into evidence stores without explicit source support.

## Session Isolation

Sessions should remain isolated by:

- source system
- timestamp
- provider
- case study

AOIA sessions must not be merged with LSC scientific sessions by default.

## Phase 2 Stop Rule

No lineage synthesis was performed in Phase 2.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/prompts/PROMPT_ARCHIVE_POLICY.md`

- size: 1176 bytes
- sha256: `c809381d0a2d319bfd75626fb9f3d749c25a247df3cf668086d484527d93b553`
- category: governance

```markdown
# Prompt Archive Policy

Phase: 2 AOIA forensic migration

## Purpose

Prepare prompt archival rules without normalizing or migrating prompts yet.

## Raw Prompts

Raw prompts are preserved exactly as captured from their source.

Rules:

- preserve original text
- preserve original filename when available
- record source path or export source
- record capture timestamp
- do not edit provider/system/user boundaries

Target:

- `prompts/raw/`

## Normalized Prompts

Normalized prompts may be created in a future phase only after raw prompt preservation.

Rules:

- must point back to raw prompt source
- may normalize filename, metadata, and layout
- must not remove provenance-relevant content
- must not merge AOIA and LSC prompts

Target:

- `prompts/normalized/`

## Provider Tagging

Provider tags must be explicit:

- `claude`
- `gemini`
- `kimi`
- `codex`
- `deepseek`
- `unknown`

If provider is uncertain, use `unknown`.

## Timestamp Policy

Use ISO-style timestamps where possible:

- `YYYY-MM-DD`
- `YYYY-MM-DDTHH-MM-SS`

Do not infer timestamps from memory if source metadata is absent.

## Phase 2 Stop Rule

No prompt normalization was performed in Phase 2.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/claude/MANIFEST.md`

- size: 552 bytes
- sha256: `37c0ca8714a215775fb46000d6cc7e537f269aa91a141fffc23f99bcfd2ebea0`
- category: governance

```markdown
# Claude Provider Manifest

Phase: 2 AOIA forensic migration

## Referenced Artifacts

From `archive/AOIA_MASTER_LIBRARY/AOIA_Master_Library.pdf`:

- `AOIA_Audit_Wave2_2305 (1).md`
- `AOIA_Audit_Wave2_2305 (2).md`
- `AOIA_Audit_Wave2_2305.md`
- `AOIA_Safety_Governance_Review_2305-1.md`
- `AOIA_Safety_Governance_Review_2305-2.md`
- `AOIA_Safety_Governance_Review_2305.md`

## Handling

No duplicate report files were created in this folder.

The source remains the imported AOIA Master Library PDF. This manifest records provider classification only.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/codex/MANIFEST.md`

- size: 692 bytes
- sha256: `d6f817bcddd805deb905d067bf3b693c0e93616705111fab08fa2385850bdde8`
- category: governance

```markdown
# Codex Provider Manifest

Phase: 2 AOIA forensic migration

## Referenced Artifacts

From `archive/AOIA_MASTER_LIBRARY/AOIA_Master_Library.pdf`:

- `CODEX_RAPORT_1925.md`
- `CODEX_RAPORT_2004.md`
- `CODEX_RAPORT_2011.md`
- `CODEX_RAPORT_2028.md`

Existing repository reports likely produced during Codex-led stabilization:

- `docs/reports/PHASE_1A_GIT_VALIDATION.md`
- `docs/reports/PHASE_2B_ROUTING_BOUNDARY.md`
- `docs/reports/FINAL_URL_HANDOFF_PATCH.md`
- `docs/PHASE1_STRUCTURE_REPORT.md`
- `docs/PHASE1_POSTCHECK.md`
- `docs/PHASE1_COMPLETE_REPORT.md`

## Handling

No duplicate report files were created in this folder.

Existing repository reports remain in their current locations.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/deepseek/MANIFEST.md`

- size: 369 bytes
- sha256: `ac910f41eda957b9ff40c4e4f00c6bcbf1ce1c85a9f7e7b4474856e9654d93f7`
- category: governance

```markdown
# DeepSeek Provider Manifest

Phase: 2 AOIA forensic migration

## Referenced Artifacts

No standalone DeepSeek provider reports were confidently identified during Phase 2.

DeepSeek is mentioned in provider/runtime context, but those mentions are not sufficient to classify a standalone report as DeepSeek-authored.

## Handling

No files were imported or duplicated.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/gemini/MANIFEST.md`

- size: 379 bytes
- sha256: `6c2bafc5d258688d29fad4411216772627b1e98d2ab04277b61839b87401e418`
- category: governance

```markdown
# Gemini Provider Manifest

Phase: 2 AOIA forensic migration

## Referenced Artifacts

No standalone Gemini provider reports were confidently identified during Phase 2.

Gemini is mentioned in architecture/runtime documents as a provider or orchestrator component, but those references are not provider-authored audit reports.

## Handling

No files were imported or duplicated.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/kimi/MANIFEST.md`

- size: 217 bytes
- sha256: `6ff069a178e3efcf00ae46ff51fb6c80db00fa1bc391c45165683f086a7cabdc`
- category: governance

```markdown
# Kimi Provider Manifest

Phase: 2 AOIA forensic migration

## Referenced Artifacts

No standalone Kimi provider reports were confidently identified during Phase 2.

## Handling

No files were imported or duplicated.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/reports/raw_provider/unknown/MANIFEST.md`

- size: 937 bytes
- sha256: `92196550fd279158682360f175cac83470c4af64bea595a0b993120745966fbd`
- category: governance

```markdown
# Unknown Provider Manifest

Phase: 2 AOIA forensic migration

## Referenced Artifacts

From `archive/AOIA_MASTER_LIBRARY/AOIA_Master_Library.pdf`:

- `AOIA_CURRENT_STATE_SUMMARY.md`
- `DETERMINISM_AUDIT.md`
- `EPISTEMIC_RISK_REPORT.md`
- `FORENSIC_ARCHITECTURE_REPORT.md`
- `MEMORY_FLOW_ANALYSIS.md`
- `MODULE_DEPENDENCY_MAP.md`
- `NEXT_STEPS_RECOMMENDATION.md`
- `RAPORT_16-10.md`
- `REPOSITORY_TREE.md`
- `SYSTEM_EXECUTION_FLOW.md`

Existing repository AOIA engineering reports without explicit provider authorship in filename:

- root `AOIA_*.md` reports
- root `MEMORY_*.md` reports
- root `CURRENT_MEMORY_FLOW.md`
- root `ORCHESTRATION_REMNANT_AUDIT.md`
- root `ROUTING_AUTHORITY_ANALYSIS.md`
- `docs/forensic-runtime-audit/*.md`
- `docs/refactor/*.md`
- `docs/architecture/*.md`

## Handling

No duplicate report files were created in this folder.

Provider remains `unknown` unless future provenance records identify the source.
```

## `MHLM_MHSR/case_studies/anti_hallucination_epi_app/unclassified/UNCLASSIFIED_MANIFEST.md`

- size: 903 bytes
- sha256: `1c8bc3551947717deff143e652b45122659cc30b0d2e641a92e172cda6164fc5`
- category: governance

```markdown
# Unclassified Manifest

Phase: 2 AOIA forensic migration

## Purpose

Record artifacts that are ambiguous between:

- `lsc_neutrino` scientific lineage
- `anti_hallucination_epi_app` AOIA engineering lineage

## Current Quarantine Decisions

No physical artifacts were moved into `unclassified/` during Phase 2.

## Ambiguity Notes

Potential ambiguity was identified in historical names and summaries that mention both domain separation and prior mixed roots.

These were not auto-classified as LSC scientific artifacts:

- AOIA Master Library references to LSC/MHLM separation
- repository state reports mentioning LSC, MHLM, or mixed-root history
- Phase 1 historical reports mentioning old `LST` taxonomy

## Rule

If an artifact contains both scientific anomaly claims and AOIA engineering/governance claims, do not classify it automatically. Add a reference here first and require manual review.
```

## `MHLM_MHSR/case_studies/lsc_neutrino/README.md`

- size: 775 bytes
- sha256: `d4bb593e3b5204dc553367a1a179309ebae6e4f91880388ced035210d4227708`
- category: governance

```markdown
# LSC Neutrino Scientific Anomaly Case Study

This case study is reserved for scientific reasoning, neutrino anomaly material, LSC lineage, and related research artifacts.

## Scope

Allowed future material:

- LSC scientific reasoning records
- neutrino anomaly notes and reports
- source documents and datasets relevant to the scientific case
- provider exports specifically about the LSC case
- lineage records for scientific review

## Boundary

This case study is not evidence for AOIA engineering claims.

AOIA runtime behavior, anti-hallucination engineering, provider routing, and provenance-engineering material must stay in the AOIA case study unless a future cross-case reference policy is approved.

## Phase 1 Status

Skeleton only. No files have been migrated.
```

## `MHLM_MHSR/framework/methodology/evidence_policy.md`

- size: 1156 bytes
- sha256: `53d04b8de9a7b46b75675ce2598fabd69a6c5a3d9f17601061bfa8c0685142e7`
- category: governance

```markdown
# Evidence Policy

## Purpose

Define the minimum evidence boundaries for MHLM/MHSR Phase 1.

## Evidence Classes

- Raw evidence: source material preserved without interpretation.
- Normalized evidence: source material reformatted for review while preserving source meaning.
- Derived evidence: framework outputs based on raw or normalized evidence.
- Non-evidence: reasoning traces, assistant drafts, runtime state, temporary logs, and unverified summaries.

## Evidence Rules

- Raw evidence has priority over normalized or derived artifacts.
- Normalized artifacts must point back to raw artifacts.
- Derived artifacts must identify their input materials.
- Runtime state is operational context, not authority.
- Provider output is not automatically evidence unless its source and purpose are recorded.

## Reasoning Trace Boundary

Reasoning traces may support lineage review, but they are non-authoritative. They must not be promoted to evidence without an external source artifact.

## Future Requirements

Future phases should define content-addressed storage, append-only provenance records, and contradiction tracking before any large migration.
```

## `MHLM_MHSR/framework/methodology/inclusion_rules.md`

- size: 1371 bytes
- sha256: `1b635b971d6170156593119b6936b7b7128dbfa2578c5a0ebb469cd2c82863ac`
- category: governance

```markdown
# Inclusion Rules

## Purpose

Define what may enter the MHLM/MHSR framework during future migration phases.

## Inclusion Classes

- Raw artifacts: original provider exports, repository snapshots, session exports, source documents, logs, or datasets copied without semantic rewriting.
- Normalized artifacts: raw artifacts converted into a consistent format while preserving source meaning and provenance.
- Derived artifacts: summaries, synthesis reports, taxonomic mappings, analysis notes, or framework conclusions produced from raw or normalized artifacts.

## Required Metadata

Every migrated artifact should identify:

- source path or source system
- original filename when available
- import date
- case study target
- artifact class: raw, normalized, or derived
- provenance record reference when available

## Case Study Separation

LSC scientific anomaly material must enter only the `lsc_neutrino` case study.

AOIA anti-hallucination engineering material must enter only the `anti_hallucination_epi_app` case study.

Cross-case references may be documented later, but they must not imply evidential dependence.

## Prohibitions

- Do not treat reasoning traces as evidence.
- Do not promote normalized artifacts above raw sources.
- Do not mix LSC evidence with AOIA runtime evidence.
- Do not import unclear artifacts without a quarantine or review note.
```

## `MHLM_MHSR/framework/methodology/lineage_policy.md`

- size: 998 bytes
- sha256: `bce6a80ed17b18cc8256e07f3a120dbd2ee79a2763face0689b9f2a6ff437b3e`
- category: governance

```markdown
# Lineage Policy

## Purpose

Define how artifact history should be recorded during future migration phases.

## Lineage Event Types

- import: raw artifact enters the framework.
- normalize: raw artifact is converted into a standard format.
- classify: artifact is assigned to a case study or taxonomy.
- synthesize: derived report or summary is created.
- review: human or model reviewer records observations.
- quarantine: artifact is held due to ambiguity or provenance risk.

## Lineage Rules

- Every normalized artifact should trace to one or more raw artifacts.
- Every derived artifact should trace to raw or normalized inputs.
- Case study assignment must be explicit.
- LSC and AOIA lineage must remain separate unless a future cross-case reference policy is approved.
- A lineage event records what happened; it does not prove correctness.

## Non-Authoritative Records

Operational logs and reasoning traces may be recorded as lineage context, but they are not evidence by themselves.
```

## `MHLM_MHSR/framework/schemas/artifact.schema.json`

- size: 389 bytes
- sha256: `6fc8727669118ed1f46d83728aef4083f963bb4bd63bc63c9b4acf2d2abf8e10`
- category: governance

```json
{
  "schema_name": "artifact",
  "version": "0.1",
  "status": "placeholder",
  "required_fields": [
    "artifact_id",
    "case_study",
    "artifact_class",
    "path",
    "created_at"
  ],
  "allowed_artifact_classes": [
    "raw",
    "normalized",
    "derived",
    "non_authoritative_context"
  ],
  "notes": "Initial placeholder only. Do not treat as final validation schema."
}
```

## `MHLM_MHSR/framework/schemas/case_study_manifest.schema.json`

- size: 279 bytes
- sha256: `965a938aefc7032569de5ea77496566c159d289b6d77bd6ffc3b523ebb85132f`
- category: governance

```json
{
  "schema_name": "case_study_manifest",
  "version": "0.1",
  "status": "placeholder",
  "required_fields": [
    "case_study_id",
    "canonical_name",
    "scope",
    "prohibited_claims"
  ],
  "notes": "Initial placeholder only. Do not treat as final validation schema."
}
```

## `MHLM_MHSR/framework/schemas/lineage_event.schema.json`

- size: 410 bytes
- sha256: `e80840adc6197ea96de539bcfdedd5fabcd006a341d1a6e7f7190222910f05ec`
- category: governance

```json
{
  "schema_name": "lineage_event",
  "version": "0.1",
  "status": "placeholder",
  "required_fields": [
    "event_id",
    "event_type",
    "case_study",
    "artifact_refs",
    "timestamp"
  ],
  "allowed_event_types": [
    "import",
    "normalize",
    "classify",
    "synthesize",
    "review",
    "quarantine"
  ],
  "notes": "Initial placeholder only. Do not treat as final validation schema."
}
```

## `MHLM_MHSR/framework/schemas/report.schema.json`

- size: 373 bytes
- sha256: `72f45a6eb89692cd926425d9b9cd8f6763618375f459fffe3989e4569be669bf`
- category: governance

```json
{
  "schema_name": "report",
  "version": "0.1",
  "status": "placeholder",
  "required_fields": [
    "report_id",
    "case_study",
    "report_class",
    "input_refs",
    "path"
  ],
  "allowed_report_classes": [
    "raw_provider",
    "normalized",
    "synthesis",
    "review"
  ],
  "notes": "Initial placeholder only. Do not treat as final validation schema."
}
```

## `MHLM_MHSR/framework/taxonomy/case_studies.yml`

- size: 518 bytes
- sha256: `5b4911efc694bb28f96b97e6c25d081b1b9158d06cd8ac61fb020c24eb211e1b`
- category: configuration

```yaml
canonical_case_studies:
  lsc_neutrino:
    canonical_name: "LSC neutrino scientific anomaly case study"
    scope: "Scientific reasoning, neutrino anomaly material, LSC lineage, and related research artifacts."
    separation_rule: "LSC is not proof of AOIA."
  anti_hallucination_epi_app:
    canonical_name: "AOIA anti-hallucination engineering case study"
    scope: "Deterministic runtime, provenance boundaries, anti-hallucination engineering, and AOIA lineage."
    separation_rule: "AOIA is not proof of LSC."
```

## `MHLM_MHSR/framework/taxonomy/legacy_aliases.yml`

- size: 569 bytes
- sha256: `f15b43672f2a8c4e19e391de80ab0e6126be0e2dcd96efb55378fdec2a9cbe3e`
- category: configuration

```yaml
legacy_aliases:
  MHLM:
    canonical: "MHLM"
    status: "accepted_alias"
  MHSR:
    canonical: "MHSR"
    status: "accepted_alias"
  MDLH:
    canonical: "MHLM/MHSR adjacent legacy alias"
    status: "review_before_merge"
  LSC:
    canonical: "LSC"
    status: "canonical_case_study_alias"
  LST:
    canonical: "LSC"
    status: "legacy_transitional_alias"

rules:
  - "Aliases do not merge evidence automatically."
  - "Legacy names require provenance review before migration."
  - "Case-study aliases must not cross AOIA/LSC boundaries without explicit review."
```

## `MHLM_MHSR/framework/taxonomy/model_aliases.yml`

- size: 711 bytes
- sha256: `090b1d9413775739994f60b4f86b0a2816a442030fdde7cbeed3efbea7abd456`
- category: configuration

```yaml
canonical_terms:
  MHLM:
    canonical: "MHLM"
    note: "Framework naming retained as canonical alias."
  MHSR:
    canonical: "MHSR"
    note: "Framework naming retained as canonical alias."
  MDLH:
    canonical: "MDLH"
    note: "Legacy or adjacent alias; keep mapped but do not merge automatically."
  LSC:
    canonical: "LSC neutrino scientific anomaly case study"
    note: "Canonical active label for scientific anomaly materials."
  LST:
    canonical: "LSC neutrino scientific anomaly case study"
    status: "legacy_alias"
    note: "Legacy transitional alias retained for lookup only; active taxonomy uses LSC/lsc_neutrino."
    note: "Canonical case-study label for scientific anomaly materials."
```

## `docs/ADR/ADR-001-deterministic-routing.md`

- size: 391 bytes
- sha256: `9b0eb48efdcd4dcdcc17e81b6c7f260db2fb25b5c37f891dee20e404840f832a`
- category: docs

```markdown
# ADR-001: Deterministic Routing

## Context

AOIA needs routing decisions that can be reproduced during tests, debugging, and
review.

## Decision

Routing must be deterministic. The same input, same config, and same code
version must produce the same routing depth.

## Consequences

Runtime learning, random selection, hidden state, and live policy mutation are
excluded from the router.
```

## `docs/ADR/ADR-002-three-depth-model.md`

- size: 341 bytes
- sha256: `ab662825c3eb84ad2ebae6f21cca7d519f95e9b0b7f0356c1a0eb20f511e09b2`
- category: docs

```markdown
# ADR-002: Three Depth Model

## Context

AOIA needs a small vocabulary for routing depth without creating policy sprawl.

## Decision

AOIA uses exactly three routing depths: LOCAL, MID, and PREMIUM.

## Consequences

All routing logic, config, tests, and documentation must use these three names.
Adding a fourth depth requires a new ADR.
```

## `docs/ADR/ADR-003-local-first-execution.md`

- size: 417 bytes
- sha256: `bf733d84c88780329133a0bde77b8688d276727fcf73fa906da9d996400092a3`
- category: docs

```markdown
# ADR-003: Local-First Execution

## Context

AOIA is intended to support reliable operation with minimal external dependency.

## Decision

AOIA must prefer local configuration, local validation, and local knowledge
before any external path is considered.

## Consequences

External providers and network-dependent behavior must remain outside the core
router unless a later phase explicitly defines their boundary.
```

## `docs/ADR/ADR-004-no-runtime-learning.md`

- size: 347 bytes
- sha256: `80a3c8bc6fc87b71b151859221d8820c82a2ee0402cd701619d41e986ac79164`
- category: docs

```markdown
# ADR-004: No Runtime Learning

## Context

Runtime learning would make routing decisions depend on previous requests and
mutable internal state.

## Decision

AOIA must not learn, tune, rank, or modify routing behavior during runtime.

## Consequences

All routing changes must come from reviewed code or configuration changes loaded
at startup.
```

## `docs/ADR/ADR-005-fail-fast-philosophy.md`

- size: 399 bytes
- sha256: `128c3367073a42153da2a1fc8ea2f0aa63d58726688584587f54815fa7a096f5`
- category: docs

```markdown
# ADR-005: Fail-Fast Philosophy

## Context

Silent fallback behavior can hide invalid configuration and produce confusing
routing results.

## Decision

AOIA must fail immediately on invalid input, invalid configuration, or
unsupported routing states.

## Consequences

Error handling should be clear and early. The router should not guess a routing
depth when required data is missing or invalid.
```

## `docs/ARCHITECTURE.md`

- size: 2180 bytes
- sha256: `44f2fe55208e01db5ecad12684aa29c717784e87e68d1fd10df09ce5641a880b`
- category: docs

```markdown
# Architecture

## Current Runtime Flow

```text
User input
  -> local fast routes
  -> optional local knowledge retrieval
  -> model planning
  -> structured action validation
  -> human approval for non-response actions
  -> local executor
  -> memory/log update
  -> final response or next step
```

## Existing Architectural Layers

Local interface:
- terminal CLI through `run.sh`
- optional local web UI through `run_web.sh`

Runtime core:
- `AgentRuntime` in `main.py`
- builds prompt context
- manages model interaction
- coordinates execution results

Execution:
- `tools/executor.py`
- shell/filesystem/browser actions
- validation and safety checks

Knowledge:
- `knowledge/rhcsa_engine.py`
- `tools/rhcsa_search.py`
- local Linux/RHCSA lookup before external reasoning

Providers:
- `providers/`
- OpenRouter/Gemini/OpenAI-compatible configuration
- should remain isolated from AOIA until explicit integration

Memory and logs:
- `memory/`
- `state/`
- `logs/`
- `obsidian_vault/`

## AOIA Target Shape

AOIA should become a local advisory layer before provider selection or heavy
reasoning. It should eventually observe local conditions and recommend a mode.

Early target:

```text
local conditions
  -> AOIA classifiers
  -> recommended routing mode
  -> runtime policy decision
```

Current status:

```text
AOIA files exist
  -> no runtime integration
  -> no provider integration
  -> no autonomous behavior
```

## Design Boundary

AOIA should not execute actions. It should only classify conditions and propose
local mode hints until a later approved step.

Examples of future AOIA inputs:
- local hour
- static regional traffic profile
- token budget
- local cache confidence
- provider availability
- user-declared urgency

Examples of future AOIA outputs:
- `deep_mode`
- `surface_mode`
- `high_traffic`
- `low_traffic`
- later: `defer_heavy_work`, `prefer_local_cache`, `allow_external_reasoning`

## Integration Rule

No AOIA classifier may affect runtime behavior until:

1. its input contract is documented,
2. its output contract is documented,
3. tests or manual validation exist,
4. a checkpoint exists,
5. the user explicitly approves integration.
```

## `docs/CONSTRAINTS.md`

- size: 3294 bytes
- sha256: `9041cb830fa5e3ee31aafda4b74dceee9e0c89a3ee88cc6dc3685b010d282bff`
- category: docs

```markdown
# AOIA Constraints

These constraints are locked for the AOIA foundation. Any change requires an
ADR and explicit review.

## Stateless Router

Definition: The router must not store request history or mutate internal state
between requests.

Rationale: Stateless behavior keeps outputs reproducible and debugging simple.

Violation consequences: Runtime behavior can become order-dependent and hard to
test.

## Immutable Runtime Config

Definition: Configuration is loaded at startup, validated once, and treated as
read-only during runtime.

Rationale: Static configuration prevents hidden behavior changes while requests
are being processed.

Violation consequences: Routing decisions may differ during the same process
without a code or config restart boundary.

## Three Depth Limit

Definition: AOIA supports exactly three routing depths: LOCAL, MID, and PREMIUM.

Rationale: A small fixed set keeps decisions understandable and testable.

Violation consequences: Extra depths increase policy ambiguity and make
determinism harder to verify.

## Deterministic Routing

Definition: The same input and validated configuration must always return the
same routing result.

Rationale: AOIA is a request-routing component, not an adaptive runtime.

Violation consequences: Users cannot reproduce, audit, or confidently test
routing behavior.

## No Runtime Learning

Definition: AOIA must not learn from requests, update models, tune weights, or
modify rules during runtime.

Rationale: Runtime learning would break immutable configuration and stateless
routing.

Violation consequences: The system becomes non-reproducible and may drift from
documented behavior.

## Fail-Fast Behavior

Definition: Invalid input, invalid config, and unsupported states must fail
immediately with clear errors.

Rationale: Early failure is easier to debug than silent fallback behavior.

Violation consequences: Bad states may propagate into execution paths and hide
configuration defects.

## No Autonomous Adaptation

Definition: AOIA must not independently change providers, schedules, policies,
or routing rules at runtime.

Rationale: Routing behavior must remain explicit and governed by static rules.

Violation consequences: The system can start acting outside documented operator
intent.

## Request-Routing Only

Definition: AOIA classifies requests into routing depths and does not execute
shell commands, call providers, or perform side effects by itself.

Rationale: Keeping classification separate from execution limits blast radius.

Violation consequences: Router defects could trigger unintended actions.

## Local-First Default

Definition: AOIA must prefer local configuration, local validation, and local
knowledge before external dependency paths are considered.

Rationale: Local-first behavior improves reproducibility, privacy, and offline
operation.

Violation consequences: Routine requests may become unnecessarily dependent on
network state or third-party services.

## Lightweight Foundation

Definition: AOIA additions must stay small, readable, and dependency-minimal
unless a later ADR justifies expansion.

Rationale: The architecture should grow through controlled modules, not broad
redesigns.

Violation consequences: Maintenance cost grows faster than verified capability.
```

## `docs/FULL_PROJECT_TREE.txt`

- size: 13263 bytes
- sha256: `e7654cadb7b5a094d8e3b614fccd786392a6990ec668bf73b0441cf6ca22578a`
- category: docs

```text
/home/l/Desktop/AOIA-Core
├── .gitignore
├── AOIA_CANONICAL_STRUCTURE_PLAN.md
├── AOIA_CONTAMINATION_REPORT.md
├── AOIA_DEPENDENCY_GRAPH.md
├── AOIA_MEMORY_ONTOLOGY.md
├── AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md
├── AOIA_RUNTIME_MAP.md
├── AOIA_TRANSITIONAL_COMPONENTS.md
├── AUTHORITY_SCOPE.md
├── CONTRADICTION_SEMANTICS.md
├── CURRENT_MEMORY_FLOW.md
├── FILESYSTEM_ONTOLOGY_LAYOUT.md
├── LICENSE
├── MEMORY_BOUNDARY_ANALYSIS.md
├── MEMORY_LAYER_DECOMPOSITION.md
├── MUTABLE_STATE_ISOLATION_PLAN.md
├── ORCHESTRATION_REMNANT_AUDIT.md
├── PROVENANCE_FOUNDATION.md
├── README.md
├── ROADMAP.md
├── ROUTING_AUTHORITY_ANALYSIS.md
├── archive
│   └── quarantine
│       └── README.md
├── contradictions
│   └── README.md
├── docs
│   ├── ADR
│   │   ├── ADR-001-deterministic-routing.md
│   │   ├── ADR-002-three-depth-model.md
│   │   ├── ADR-003-local-first-execution.md
│   │   ├── ADR-004-no-runtime-learning.md
│   │   └── ADR-005-fail-fast-philosophy.md
│   ├── ARCHITECTURE.md
│   ├── CONSTRAINTS.md
│   ├── FULL_PROJECT_TREE.txt
│   ├── GIT_HISTORY_CONTINUATION_PLAN.md
│   ├── KNOWLEDGE_PACK_RULES.md
│   ├── KNOWLEDGE_PACK_SPEC.md
│   ├── LINEAGE_MAP.md
│   ├── NON_GOALS.md
│   ├── README.md
│   ├── REPOSITORY_CONSTITUTION.md
│   ├── REPO_STRUCTURE.md
│   ├── RHCSA_ENGINE_REVIEW.md
│   ├── RUNTIME_BOUNDARY.md
│   ├── TEST_CONSTITUTION.md
│   ├── adr
│   │   ├── 0001-keep-aoia-isolated.md
│   │   ├── 0002-minimal-deterministic-router-skeleton.md
│   │   ├── 0003-immutable-startup-configuration.md
│   │   ├── 0004-stdout-only-plain-text-logging.md
│   │   ├── 0005-test-constitution-determinism-first.md
│   │   └── README.md
│   ├── architecture
│   │   ├── AOIA_MEMORY_MODEL.md
│   │   ├── FORBIDDEN_MEMORY_FLOWS.md
│   │   └── MEMORY_LAYER_ACCESS_MATRIX.md
│   ├── checkpoints
│   │   └── 2026-05-23
│   │       ├── AOIA_DAILY_CHECKPOINT.md
│   │       └── NEXT_ACTIONS.md
│   ├── forensic-runtime-audit
│   │   ├── CANONICAL_REFACTOR_PREP.md
│   │   ├── CURRENT_RUNTIME_TOPOLOGY.md
│   │   ├── MEMORY_CONTAMINATION_MAP.md
│   │   └── RUNTIME_BOUNDARY_VIOLATIONS.md
│   ├── refactor
│   │   ├── CANONICAL_AUTHORITY_GRAPH.md
│   │   ├── MEMORY_AUTHORITY_BOUNDARIES.md
│   │   ├── MEMORY_CONTAMINATION_GRAPH.md
│   │   ├── MEMORY_DEPENDENCY_GRAPH.md
│   │   └── MEMORY_SPLIT_PLAN.md
│   └── reports
│       ├── FINAL_URL_HANDOFF_PATCH.md
│       ├── PHASE_1A_GIT_VALIDATION.md
│       └── PHASE_2B_ROUTING_BOUNDARY.md
├── governance
│   └── README.md
├── memory
│   └── README.md
├── provenance
│   └── README.md
├── retrieval
│   └── README.md
├── runtime
│   ├── adaptive_routing
│   │   ├── aoia_config.json
│   │   ├── circadian_router.py
│   │   ├── config_loader.py
│   │   ├── deterministic_router.py
│   │   ├── dvm_research.md
│   │   ├── environment
│   │   │   ├── environment_router.py
│   │   │   ├── network_patterns.md
│   │   │   └── traffic_profiles.json
│   │   ├── epistemic_kernel.py
│   │   ├── routing_modes.json
│   │   └── stdout_logger.py
│   ├── commands
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── local_commands.py
│   ├── contradiction_registry.json
│   ├── install.sh
│   ├── knowledge
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── bash
│   │   │   ├── README.md
│   │   │   ├── skrypty-bash-podstawy.md
│   │   │   ├── wyszukiwanie-i-filtrowanie-tekstu.md
│   │   │   ├── zaawansowane-narzdzia-tekstowe.md
│   │   │   └── zmienne-rodowiskowe-i-powoka.md
│   │   ├── canonical
│   │   │   └── rhcsa_commands.json
│   │   ├── command_graph.json
│   │   ├── context
│   │   │   └── context_pack.json
│   │   ├── examples
│   │   │   ├── ls-command.json
│   │   │   ├── rm-recursive-force.json
│   │   │   └── systemctl-status.json
│   │   ├── filesystem
│   │   │   ├── README.md
│   │   │   ├── archiwizacja-i-kompresja.md
│   │   │   ├── edytor-vim.md
│   │   │   ├── nawigacja-po-systemie-plikow.md
│   │   │   ├── operacje-na-plikach-i-katalogach.md
│   │   │   ├── przegldanie-zawartoci-plikow.md
│   │   │   └── wyszukiwanie-plikow.md
│   │   ├── index
│   │   │   └── command_index.json
│   │   ├── injection
│   │   │   └── injected_context.json
│   │   ├── lvm
│   │   │   ├── README.md
│   │   │   └── lvm-logical-volume-manager.md
│   │   ├── networking
│   │   │   ├── README.md
│   │   │   ├── nfs-i-autofs.md
│   │   │   ├── samba-i-nfs-klient.md
│   │   │   ├── sie-konfiguracja-i-diagnostyka.md
│   │   │   ├── ssh-i-dostp-zdalny.md
│   │   │   └── zapora-ogniowa-firewalld.md
│   │   ├── parsed
│   │   │   └── rhcsa_sections.json
│   │   ├── permissions
│   │   │   ├── README.md
│   │   │   └── uprawnienia-i-wasno-plikow.md
│   │   ├── podman
│   │   │   ├── README.md
│   │   │   └── kontenery-podman.md
│   │   ├── raw
│   │   │   └── rhcsa_raw.txt
│   │   ├── rhcsa_engine.py
│   │   ├── schema
│   │   │   └── command.schema.json
│   │   ├── selinux
│   │   │   ├── README.md
│   │   │   └── selinux.md
│   │   ├── source
│   │   │   └── RHCSA_Command_Library (1).pdf
│   │   ├── storage
│   │   │   ├── README.md
│   │   │   ├── przechowywanie-danych-dyski-i-partycje.md
│   │   │   ├── systemy-plikow-i-montowanie.md
│   │   │   └── zarzdzanie-dyskami-raid.md
│   │   ├── systemd
│   │   │   ├── README.md
│   │   │   ├── boot-i-grub.md
│   │   │   ├── cron-i-harmonogramowanie-zada.md
│   │   │   ├── systemd-i-zarzdzanie-usugami.md
│   │   │   └── zarzdzanie-pakietami-dnf-rpm.md
│   │   ├── tools
│   │   │   ├── CANONICAL_BUILDER_README.md
│   │   │   ├── CONTEXT_PACK_README.md
│   │   │   ├── INDEX_BUILDER_README.md
│   │   │   ├── INJECTION_LAYER_README.md
│   │   │   ├── README.md
│   │   │   ├── SECTION_PARSER_README.md
│   │   │   ├── canonical_builder.py
│   │   │   ├── context_injector.py
│   │   │   ├── context_pack_builder.py
│   │   │   ├── index_builder.py
│   │   │   ├── markdown_kb_builder.py
│   │   │   ├── pdf_extract.py
│   │   │   └── section_parser.py
│   │   ├── troubleshooting
│   │   │   ├── README.md
│   │   │   ├── diagnostyka-i-narzdzia-systemowe.md
│   │   │   ├── dodatkowe-narzdzia-administracyjne.md
│   │   │   ├── informacje-o-systemie.md
│   │   │   ├── logowanie-i-monitorowanie-systemu.md
│   │   │   └── zarzdzanie-procesami.md
│   │   ├── users
│   │   │   ├── README.md
│   │   │   ├── zarzdzanie-grupami.md
│   │   │   └── zarzdzanie-uytkownikami.md
│   │   └── validator
│   │       ├── __init__.py
│   │       ├── validation_report.md
│   │       ├── validation_rules.py
│   │       └── validator.py
│   ├── main.py
│   ├── memory
│   │   ├── __init__.py
│   │   ├── evidence_memory.jsonl
│   │   ├── gemma_worker_memory.py
│   │   ├── hats
│   │   │   ├── coding.json
│   │   │   ├── linux.json
│   │   │   └── research.json
│   │   ├── history.jsonl
│   │   ├── reasoning_trace.jsonl
│   │   └── rhcsa_context.py
│   ├── obsidian_vault
│   │   ├── .obsidian
│   │   │   └── app.json
│   │   ├── 00_START_HERE.md
│   │   ├── Daily
│   │   │   └── 2026-05-23.md
│   │   ├── Evidence
│   │   │   ├── 20260523_204053_498246.md
│   │   │   ├── 20260523_204122_715088.md
│   │   │   ├── 20260523_204427_843537.md
│   │   │   └── 20260523_204557_588315.md
│   │   ├── Inbox
│   │   ├── Knowledge
│   │   ├── Logs
│   │   ├── Projects
│   │   ├── Prompts
│   │   ├── Reasoning
│   │   │   ├── 20260523_204053_498246.md
│   │   │   ├── 20260523_204122_715088.md
│   │   │   ├── 20260523_204427_843537.md
│   │   │   └── 20260523_204557_588315.md
│   │   ├── Sessions
│   │   │   ├── 20260523_204053_498246.jsonl
│   │   │   ├── 20260523_204122_715088.jsonl
│   │   │   ├── 20260523_204427_843537.jsonl
│   │   │   └── 20260523_204557_588315.jsonl
│   │   └── Templates
│   ├── orchestrator
│   │   ├── __init__.py
│   │   ├── gemini_gemma.py
│   │   └── knowledge_router.py
│   ├── project_scan.json
│   ├── prompts
│   │   └── system_prompt.txt
│   ├── provenance_registry.json
│   ├── providers
│   │   ├── __init__.py
│   │   ├── aureon_provider.py
│   │   ├── base.py
│   │   ├── config.py
│   │   ├── gemini_provider.py
│   │   ├── gemma_provider.py
│   │   └── openai_compatible.py
│   ├── requirements.txt
│   ├── router
│   │   ├── __init__.py
│   │   └── local_router.py
│   ├── run.sh
│   ├── run_web.sh
│   ├── screenshots
│   ├── state
│   │   ├── agent_state.json
│   │   ├── model_config.json
│   │   ├── providers.json
│   │   └── token_savings_report.json
│   ├── tools
│   │   ├── __init__.py
│   │   ├── browser_tools.py
│   │   ├── build_rhcsa_library.py
│   │   ├── epistemic_registry.py
│   │   ├── executor.py
│   │   ├── filesystem_tools.py
│   │   ├── memory.py
│   │   ├── memory_hats.py
│   │   ├── project_scanner.py
│   │   ├── rhcsa_search.py
│   │   ├── shell_tools.py
│   │   ├── system_info.py
│   │   ├── validator.py
│   │   └── web_reader.py
│   └── webapp.py
├── state
│   ├── model_config.json
│   └── providers.json
├── tests
│   ├── test_aoia_determinism.py
│   ├── test_epistemic_kernel.py
│   ├── test_epistemic_registry.py
│   ├── test_epistemic_safeguards.py
│   ├── test_executor_containment.py
│   ├── test_knowledge_validator.py
│   ├── test_main.py
│   ├── test_rhcsa_retrieval.py
│   └── test_routing_boundary.py
└── web
    ├── app.js
    ├── index.html
    └── styles.css

68 directories, 237 files
```

## `docs/GIT_HISTORY_CONTINUATION_PLAN.md`

- size: 677 bytes
- sha256: `21023bb4386c27c59732b6fa533579ebca84bd33cd8f70537bc02c29a5273776`
- category: docs

```markdown
# Git History Continuation Plan

## Goal

Continue AOIA as a standalone runtime and infrastructure project.

## Immediate state

- This repository was physically extracted into a dedicated git root.
- Commit ancestry from the prior runtime repo is documented but was not replayed into this new root during extraction.

## Recommended continuation

1. Treat this root as the forward AOIA implementation authority.
2. Preserve references to prior runtime commits and reports externally.
3. If needed later, replay selected implementation history from `app2terminl_opened` with `git filter-repo` or subtree import.
4. Keep generated runtime state out of canonical source history.
```

## `docs/KNOWLEDGE_PACK_RULES.md`

- size: 1924 bytes
- sha256: `f2441dde7d035a135291b508b9c7d5c8f6e2b4ffe0a8df262cb15a382ee8c5f1`
- category: docs

```markdown
# AOIA Knowledge Pack Rules

Knowledge packs are local, static, JSON-only reference files. They support
future deterministic routing work but do not implement routing.

## Naming Rules

- Schema files use `*.schema.json`.
- Example files use lowercase kebab-case names.
- Entry `id` values use lowercase kebab-case.
- Tags use lowercase kebab-case.
- Categories and risk levels use lowercase names from the canonical lists.

## Validation Rules

- Every entry must validate against `knowledge/schema/command.schema.json`.
- Unknown top-level fields are not allowed.
- Required fields must be present.
- `tags`, `os`, `shell`, and `examples` must be non-empty arrays.
- `risk` must be one of: `low`, `medium`, `high`, `critical`.
- `category` must be one of the canonical categories in the spec.
- `examples[].expected_effect` must describe the expected result without
  promising external state.

## Risk Classification Rules

- Use `low` for read-only inspection commands.
- Use `medium` for local changes with clear recovery paths.
- Use `high` for service-impacting or broad filesystem changes.
- Use `critical` for destructive, secret-exposing, or access-breaking commands.
- When uncertain, choose the higher risk level.

## Tagging Rules

- Tags should describe function, not intent speculation.
- Use a small number of precise tags.
- Do not encode user names, dates, hostnames, or environment-specific data.
- Prefer stable tags such as `read-only`, `permissions`, `service-status`,
  `network-inspection`, or `package-management`.

## Mutation Rules

- Runtime code must not rewrite knowledge pack files.
- Generated knowledge pack updates must be reviewed before use.
- Knowledge pack files are source artifacts, not cache files.

## Dependency Rules

- Knowledge packs are JSON only.
- No database engine is required.
- No vector store is allowed.
- No embedding model is required.
- No external API is required.
```

## `docs/KNOWLEDGE_PACK_SPEC.md`

- size: 2131 bytes
- sha256: `7fa088792bb1490d4cd3433b2189f390d10fe589af7336938c027a79cf35ba03`
- category: docs

```markdown
# AOIA Knowledge Pack Specification

This document defines the canonical local JSON structure for AOIA knowledge
packs. It does not define retrieval, embeddings, ranking, or runtime mutation.

## Purpose

Knowledge packs are static local JSON files that describe operational command
knowledge in a deterministic format. They are reference material only.

## Directory Layout

```text
knowledge/
├── schema/
│   └── command.schema.json
└── examples/
    └── *.json
```

## Canonical Entry Type

The first supported entry type is a command entry. Each command entry describes
one command or one narrow command family.

Required fields:

- `id`: stable lowercase identifier.
- `command`: command name or command pattern.
- `description`: short operational description.
- `category`: one canonical category.
- `tags`: deterministic lowercase tags.
- `risk`: one canonical risk level.
- `os`: supported operating system labels.
- `shell`: supported shell labels.
- `examples`: one or more deterministic usage examples.

Optional fields:

- `notes`: short implementation notes.
- `related_commands`: deterministic list of related command names.

## Risk Levels

- `low`: read-only or harmless inspection command.
- `medium`: changes local state but is normally reversible.
- `high`: can interrupt services, modify permissions, or affect many files.
- `critical`: can delete data, expose secrets, disable access, or damage system
  availability.

## Categories

Initial canonical categories:

- `filesystem`
- `process`
- `network`
- `package`
- `service`
- `user`
- `security`
- `archive`
- `diagnostic`
- `system`

New categories require documentation before use.

## Determinism Rules

- JSON object keys should be written in schema order.
- Arrays must be stable and manually sorted where practical.
- Identifiers must not include timestamps or generated random values.
- Entries must not depend on network state.
- Files must not be modified by runtime routing code.

## Out of Scope

- AI retrieval
- embeddings
- vector databases
- semantic search
- autonomous routing
- live telemetry
- runtime learning
```

## `docs/LINEAGE_MAP.md`

- size: 531 bytes
- sha256: `27c3ba1e8ac550d23dab0923bdea9ca5b42a86768b47b09e7920e6995c77aca0`
- category: docs

```markdown
# Lineage Map

## Repository ancestry

Primary ancestry preserved in this repository:
- `app2terminl_opened`
- deterministic routing and local retrieval layers
- provenance and contradiction registry implementation
- test and documentation lineage for AOIA runtime controls

## Cross-repository references

- external research repositories may be cited as context only
- analytical repositories may cite AOIA stabilization and forensic analysis as case-study material
- AOIA does not own external science or epistemic truth claims
```

## `docs/LINUX_ENGINEERING_LIBRARY.md`

- size: 7900 bytes
- sha256: `3d835ca56925d4fe921f3dab60a69428866dc18c44ab36d03aa0566178937379`
- category: docs

```markdown
# Linux Engineering Library

Append-only working file for Gemini-generated packets.

Source corpus already present in the repository:
- `runtime/knowledge/raw/rhcsa_raw.txt`

## Packet 1

```bash
#!/bin/bash
# ==============================================================================
# LINUX ENGINEERING LIBRARY - GENERATOR PACKET 1
# DOMENY: 1. Fundamentals, 2. History, 3. GNU Ecosystem, 4-5. Filesystems, 6-7. Permissions & ACL, 8-9. Identity & PAM
# ==============================================================================

set -e

# 1. Przygotowanie struktury katalogów klastra wiedzy
OUTPUT_DIR="linux-engineering-corpus/01_storage_and_identity"
mkdir -p "${OUTPUT_DIR}"

echo "[*] Generowanie wolumenu 1: Core Fundamentals, Storage & Identity Architecture..."

# 2. Budowanie pliku Markdown za pomocą bezpiecznego bloku EOF (bez ekspansji zmiennych powłoki)
cat << 'EOF' > "${OUTPUT_DIR}/01_fundamentals_storage_identity.md"
---
schema_version: "1.2"
domain: "Core Infrastructure & Storage Engineering"
subdomain: "Kernel Runtime, VFS, CoW Filesystems, PAM Authentication"
kernel_target: ">=5.15"
distro_agnostic: true
danger_level: "High"
idempotent: true
provenance:
  author: "Linux Engineering Library Archivist"
  verified_against: ["RHEL 9.4", "Ubuntu Server 24.04 LTS", "Debian 12"]
tags: ["kernel-space", "vfs", "xfs", "zfs", "acl", "pam", "production-ops"]
related_concepts: ["syscalls", "device-mapper", "authentication-stacks"]
---

# ROZDZIAŁ 1: FUNDAMENTY SYSTEMU, EKOSYSTEM GNU, INŻYNIERIA SYSTEMÓW PLIKÓW I ZARZĄDZANIE TOŻSAMOŚCIĄ

## 1.1 ARCHITEKTURA RDZENIA I ŚRODOWISKO URUCHOMIENIOWE (LINUX FUNDAMENTALS)

Linux to monolityczne jądro o architekturze wielozadaniowej z wywłaszczaniem (preemptive kernel), implementujące standardy POSIX. Wszystkie operacje niskopoziomowe — sterowniki urządzeń, stos sieciowy, planista procesów (CFS/EEVDF) oraz systemy plików — wykonują się w jednej, wspólnej, uprzywilejowanej przestrzeni adresowej jądra.

### 1.1.1 Izolacja Ring 0 vs Ring 3 i Mechanizm Syscalls
Stabilność systemu opiera się na sprzętowej izolacji pierścieni ochrony procesora (CPU Privilege Rings):
*   Ring 0 (Kernel Space): Pełny dostęp do instrukcji procesora, rejestrów kontrolnych i fizycznej pamięci RAM. Każdy błąd (np. odwołanie do błędnego wskaźnika) skutkuje wywołaniem procedury Kernel Panic.
*   Ring 3 (User Space): Izolowane środowisko dla aplikacji i demonów. Procesy nie mają bezpośredniego dostępu do sprzętu. 

Komunikacja między Ring 3 a Ring 0 odbywa się wyłącznie poprzez System Calls (Syscalls). Wywołanie syscalla (np. przez instrukcję sysenter lub syscall w architekturze x86_64) powoduje przełączenie kontekstu procesora w tryb Ring 0, wykonanie operacji przez jądro i powrót do przestrzeni użytkownika.

### 1.1.2 Podsystem Pamięci Wirtualnej i Alokacja Zasobów
Pamięć fizyczna jest mapowana na pamięć wirtualną za pomocą jednostki MMU (Memory Management Unit).
*   Stronicowanie (Paging): Domyślny rozmiar strony w architekturze x86_64 wynosi 4KB.
*   Huge Pages (Strony Anonimowe i Przeźroczyste — THP): Alokacja ciągłych bloków pamięci o rozmiarze 2MB lub 1GB. Kluczowa dla baz danych (PostgreSQL, Oracle) w celu redukcji narzutu na wyszukiwanie w tablicy stron (Page Table) i maksymalizacji efektywności bufora TLB (Translation Lookaside Buffer).
*   Overcommit i OOM Killer: Jądro domyślnie pozwala na alokację większej ilości pamięci wirtualnej, niż wynosi fizyczna dostępność RAM + Swap (vm.overcommit_memory = 0). W sytuacji krytycznego braku pamięci, podsystem *Out-Of-Memory Killer* oblicza punktację (oom_score) na podstawie zużycia RAMu i priorytetu procesu, a następnie bezpowrotnie zabija proces o najwyższym wskaźniku.

### 1.1.2.1 Polecenia Strojenia Środowiska Runtime

#### sysctl [CAUTION]
Modyfikacja parametrów jądra w locie w przestrzeni /proc/sys/.

```bash
# Sprawdzenie aktualnego wskaźnika agresywności wymiany pamięci (Swap)
sysctl vm.swappiness

# Produkcyjne obniżenie swappiness na serwerach bazodanowych (minimalizacja I/O wait)
sysctl -w vm.swappiness=10

# Zmiana limitów mapowania pamięci dla silników Elasticsearch/Lucene
sysctl -w vm.max_map_count=262144
```

## Packet 2

### 1.2 HISTORIA, STANDARYZACJA I EKOSYSTEM GNU/LINUX

Wspolczesne dystrybucje Enterprise dziela sie na odrebne rodziny, ktorych cykl zycia oraz determinizm operacyjny zaleza od doboru bibliotek bazowych oraz mechanizmow zarzadzania pakietami.

### 1.2.1 Dziedzictwo POSIX i Standardy LSB

Linux implementuje specyfikacje POSIX, co gwarantuje przenosnosc kodu zrodlowego pomiedzy roznymi systemami operacyjnymi typu UNIX. Kluczowym elementem ekosystemu jest glibc (GNU C Library) - fundamentalna biblioteka systemowa, stanowiaca interfejs programistyczny dla wszystkich aplikacji w przestrzeni uzytkownika.

Ostrzezenie architektoniczne: uszkodzenie pliku `/lib64/libc.so.6` powoduje natychmiastowy paraliż systemu. Zadna standardowa komenda, w tym `ls`, `cp` i `sh`, nie uruchomi sie, poniewaz linkowanie dynamiczne zostanie przerwane.

### 1.2.2 Niskopoziomowa Anatomia Menedzerow Pakietow

Rodzina RPM (DNF / RHEL / Rocky Linux):
- baza danych: przechowywana w `/var/lib/rpm/`
- mechanizm transakcyjny: DNF wspiera pelne wycofywanie zmian stanu systemu

`dnf history [SAFE / CAUTION]`

Zarzadzanie historia instalacji:

```bash
# Wyswietlenie listy ostatnich transakcji [SAFE]
dnf history

# Szczegolowy audyt konkretnej transakcji [SAFE]
dnf history info 14

# Wycofanie zmian wprowadzonych przez transakcje [CAUTION]
dnf history undo 14
```

Rodzina DEB (APT / Debian / Ubuntu):
- baza danych: `/var/lib/dpkg/`
- mechanizm kontrolny: `dpkg --verify`

Znaczenie operacyjne: modyfikacja plikow binarnych w `/bin/` lub `/sbin/` bez wiedzy administratora, wykryta przez `dpkg -V`, to bezposredni dowod na kompromitacje systemu.

### 1.2.3 Rozwiazywanie Blokad Subsystemow Pakietow

Czesty przypadek awarii w automatyzacji (Ansible/Puppet): proces instalacji zostaje zablokowany przez demony dzialajace w tle.

```bash
# 1. Identyfikacja procesu trzymajacego deskryptor pliku blokady [SAFE]
lsof /var/lib/dpkg/lock-frontends

# 2. Wymuszenie zakonczenia procesu [CAUTION]
kill -15 <PID_Z_POLECENIA_LSOF>

# 3. Jesli proces nie zwalnia blokady po 10 sekundach [CAUTION]
kill -9 <PID_Z_POLECENIA_LSOF>

# 4. Usuniecie osieroconych plikow blokad - tylko jesli proces na pewno nie zyje [CAUTION]
rm -f /var/lib/dpkg/lock-frontends
rm -f /var/lib/apt/lists/lock

# 5. Rekonfiguracja uszkodzonej bazy danych [CAUTION]
dpkg --configure -a
```

### 1.3 INZYNIERIA SYSTEMOW PLIKOW

System plikow mapuje logiczne struktury drzewa katalogow na fizyczne adresy blokowe nosnika (LBA). Warstwa VFS w jadze unifikuje ten proces, udostepniajac aplikacjom standardowe wywolania systemowe `open`, `read` i `write` niezaleznie od typu systemu plikow.

#### 1.3.1 EXT4 vs XFS: Porownanie Strukturalne

| Wlasciwosc | EXT4 | XFS |
|---|---|---|
| Podstawowa jednostka | Grupy blokow | Grupy alokacji (AG) |
| Zarzadzanie wolna przestrzenia | Bitmapy blokow | Drzewa B+ |
| Skalowanie wielordzeniowe | srednie | wysokie |
| Rozmiar wolumenu | do 1 EB | do 8 EB |
| Pomniejszanie (shrink) | tak, po odmontowaniu | nie |

Kluczowe pojecia:
- inode: struktura przechowujaca metadane pliku, bez nazwy pliku
- extenty: ciagle bloki dyskowe przypisane do pliku jako zakres adresow

#### 1.3.2 Zaawansowane Systemy Plikow CoW

Systemy copy-on-write eliminuja tradycyjne nadpisywanie danych. Przy modyfikacji bloku:
- dane sa zapisywane w nowym, wolnym miejscu na dysku
- metadane sa aktualizowane i wskazuja nowy adres
- stary blok jest zwalniany albo zachowywany przy snapshotach

#### 1.3.3 Zarzadzanie, Strojenie i Tworzenie Systemow Plikow

`mkfs.xfs [CAUTION]`

Formatowanie wolumenu. Operacja niszczy strukture danych na urzadzeniu docelowym.
```

## `docs/LINUX_ENGINEERING_LIBRARY_REPORT.md`

- size: 658 bytes
- sha256: `f09d578b524ef790a6f7e90e9fffca700f8531b421022713239822d5c6064c79`
- category: docs

```markdown
# Linux Engineering Library Report

Status: append-only working file prepared for staged import of Linux/RHCSA content.

Current canonical file:
- `docs/LINUX_ENGINEERING_LIBRARY.md`

Included packets:
- Packet 1: core infrastructure and storage identity bootstrap
- Packet 2: GNU/Linux history, package management, filesystem engineering

Notes:
- Existing repository RHCSA corpus remains unchanged.
- No runtime logic, routing, memory, or provider configuration was modified.
- The workflow is intentionally single-file to avoid parallel archive trees or duplicate report structures.

Next step:
- append the next Gemini packet into the same markdown file
```

## `docs/NON_GOALS.md`

- size: 2119 bytes
- sha256: `53ac7ea355fec5dbfcca72b42a3dc91ba1e0f890badbce5b98cf015fe43b4449`
- category: docs

```markdown
# AOIA Non-Goals

AOIA is a deterministic request-routing architecture. The following directions
are explicitly excluded.

## NOT an AGI Platform

Excluded because AOIA does not define general intelligence, autonomous goals, or
open-ended reasoning. This would introduce unbounded scope and violate the
request-routing-only constraint.

## NOT Autonomous AI

Excluded because AOIA must not initiate actions, change policies, or pursue
tasks without direct request context. This would weaken operator control and
violate stateless routing.

## NOT Self-Learning Infrastructure

Excluded because AOIA must not learn from runtime traffic or update rules during
execution. This would break immutable config and deterministic reproducibility.

## NOT Swarm Intelligence

Excluded because AOIA does not coordinate independent agents or collective
decision systems. This would introduce distributed state and uncontrolled
complexity.

## NOT Adaptive Cognition

Excluded because AOIA does not model cognition or reasoning development. This
would make the architecture speculative instead of operational.

## NOT Dynamic Orchestration

Excluded because AOIA must not perform runtime provider balancing, live cloud
routing, or infrastructure control. This would exceed the current request
classification boundary.

## NOT a Biological Simulation

Excluded because biological systems are only used as limited conceptual
inspiration for layering, timing, and energy efficiency. Simulation would add
irrelevant models and testing burden.

## NOT a Consciousness Framework

Excluded because AOIA has no subjective state, identity model, or awareness
model. This language introduces ambiguity and violates engineering clarity.

## NOT Hyperscaler Infrastructure

Excluded because AOIA is local-first and lightweight. Hyperscaler design would
add scale assumptions, operational cost, and infrastructure complexity that are
outside this phase.

## NOT Self-Modifying Runtime Logic

Excluded because AOIA must not rewrite rules, configuration, or behavior while
running. This would violate fail-fast, auditability, and reproducibility.
```

## `docs/PHASE1_COMPLETE_REPORT.md`

- size: 4355 bytes
- sha256: `b4403960968e58b1e11df7f86a55487bf486508086404545ba5f5afcad9cdbe7`
- category: docs

```markdown
# Phase 1 Complete Report

Date: 2026-05-24
Repository: `/home/l/Desktop/AOIA-Core`
Package purpose: complete Phase 1 MHLM/MHSR skeleton and report bundle.

## What Was Requested

Initialize the Phase 1 MHLM/MHSR framework skeleton from the uploaded ZIP prompt while keeping the repository clean and non-destructive.

Required constraints:

- do not refactor runtime
- do not move AOIA runtime
- do not migrate reports or prompts yet
- do not touch provider configs
- do not modify routing logic
- do not create duplicate/conflicting structures
- document conflicts before creating anything

## Input ZIP

Uploaded file:

- `/home/l/Desktop/aaqqqqqqqqqq.zip`

Read files:

- `README.txt`
- `PHASE1_CODEX_PROMPT.txt`

The ZIP was unpacked only to `/tmp` and the temporary unpack directory was removed after completion.

## Pre-Phase Conflict Scan

Generated:

- `docs/PRE_PHASE1_CONFLICT_SCAN.md`

Detected existing naming/conflict risks:

- `docs/ADR/` and `docs/adr/`
- `memory/` and `runtime/memory/`
- `state/` and `runtime/state/`
- `runtime/prompts/` and `runtime/obsidian_vault/Prompts/`
- `runtime/knowledge/` and `runtime/obsidian_vault/Knowledge/`
- `runtime/logs/` and `runtime/obsidian_vault/Logs/`
- `runtime/logs/sessions/` and `runtime/obsidian_vault/Sessions/`

Decision:

- preserve existing structures
- do not normalize or rename during Phase 1
- create only one new isolated root: `MHLM_MHSR/`

## Created Skeleton Root

Created:

- `MHLM_MHSR/`

Top-level skeleton:

- `MHLM_MHSR/framework/`
- `MHLM_MHSR/case_studies/`
- `MHLM_MHSR/imports/`
- `MHLM_MHSR/docs/`

## Framework Skeleton

Created folders:

- `MHLM_MHSR/framework/methodology/`
- `MHLM_MHSR/framework/schemas/`
- `MHLM_MHSR/framework/taxonomy/`
- `MHLM_MHSR/framework/governance/`

Created methodology docs:

- `inclusion_rules.md`
- `evidence_policy.md`
- `lineage_policy.md`
- `contradiction_policy.md`

Created schemas:

- `artifact.schema.json`
- `lineage_event.schema.json`
- `report.schema.json`
- `provenance_record.schema.json`
- `case_study_manifest.schema.json`

Created taxonomy files:

- `case_studies.yml`
- `model_aliases.yml`
- `legacy_aliases.yml`

## Case Studies

Created separated case studies:

- `MHLM_MHSR/case_studies/lst/`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/`

Created README files:

- `MHLM_MHSR/case_studies/lst/README.md`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/README.md`

Case separation rule:

- LST/LSC scientific anomaly material is not evidence for AOIA engineering claims.
- AOIA anti-hallucination engineering material is not evidence for LST/LSC scientific claims.

## Migration Targets Created

Created under both case studies:

- `prompts/raw/`
- `prompts/normalized/`
- `reports/raw_provider/`
- `reports/normalized/`
- `reports/synthesis/`
- `lineage/sessions/`
- `lineage/events/`
- `lineage/decisions/`
- `provenance/`
- `contradictions/`
- `archive/`

No files were migrated into these folders.

## Import Targets Created

Created:

- `MHLM_MHSR/imports/provider_exports/raw/`
- `MHLM_MHSR/imports/provider_exports/normalized/`
- `MHLM_MHSR/imports/repo_snapshots/`
- `MHLM_MHSR/imports/git_bundles/`

No imports were performed.

## Reports Generated

Generated:

- `docs/PRE_PHASE1_CONFLICT_SCAN.md`
- `docs/PHASE1_STRUCTURE_REPORT.md`
- `docs/PHASE1_POSTCHECK.md`
- `docs/PHASE1_COMPLETE_REPORT.md`

## Verification

JSON schema placeholders were validated with `python3 -m json.tool`.

Result:

```text
schema json OK
```

Temporary unpack directory:

```text
/tmp/phase1_mhlm_mhsr_zip removed
```

## What Was Not Done

Not performed:

- no runtime migration
- no AOIA runtime reorganization
- no provider config edit
- no routing logic modification
- no report migration
- no prompt migration
- no file deletion from AOIA runtime
- no LST/AOIA mixing
- no duplicate runtime folders

## Remaining Known Dirty State

The repository already had unrelated local changes before Phase 1:

- `docs/reports/FINAL_URL_HANDOFF_PATCH.md`
- `runtime/main.py`
- `runtime/prompts/system_prompt.txt`
- `tests/test_routing_boundary.py`
- runtime state/log/memory surfaces
- previous transfer-report docs

Those were not part of Phase 1 skeleton initialization.

## Phase 1 Outcome

Phase 1 complete.

The repository now contains a clean MHLM/MHSR skeleton ready for review before any migration phase begins.
```

## `docs/PHASE1_POSTCHECK.md`

- size: 4257 bytes
- sha256: `d126011f8496ea00a79265532b48184e13c7d7e9cd4bdc13c6c49b0c2bd5da6c`
- category: docs

```markdown
# Phase 1 Postcheck

Date: 2026-05-24
Repository: `/home/l/Desktop/AOIA-Core`

## Summary

Phase 1 skeleton initialization is complete.

The work remained clean and non-destructive:

- no AOIA runtime files moved
- no provider configs touched
- no routing logic changed
- no reports migrated
- no prompts migrated
- no duplicated runtime directories created
- no LST/AOIA materials mixed

## Created Folders

New isolated root:

- `MHLM_MHSR/`

Created within it:

- `framework/methodology/`
- `framework/schemas/`
- `framework/taxonomy/`
- `framework/governance/`
- `case_studies/lst/`
- `case_studies/anti_hallucination_epi_app/`
- `imports/provider_exports/raw/`
- `imports/provider_exports/normalized/`
- `imports/repo_snapshots/`
- `imports/git_bundles/`
- `docs/`

Created under each case study:

- `prompts/raw/`
- `prompts/normalized/`
- `reports/raw_provider/`
- `reports/normalized/`
- `reports/synthesis/`
- `lineage/sessions/`
- `lineage/events/`
- `lineage/decisions/`
- `provenance/`
- `contradictions/`
- `archive/`

## Created Files

- `docs/PRE_PHASE1_CONFLICT_SCAN.md`
- `docs/PHASE1_STRUCTURE_REPORT.md`
- `docs/PHASE1_POSTCHECK.md`
- `MHLM_MHSR/framework/methodology/inclusion_rules.md`
- `MHLM_MHSR/framework/methodology/evidence_policy.md`
- `MHLM_MHSR/framework/methodology/lineage_policy.md`
- `MHLM_MHSR/framework/methodology/contradiction_policy.md`
- `MHLM_MHSR/framework/schemas/artifact.schema.json`
- `MHLM_MHSR/framework/schemas/lineage_event.schema.json`
- `MHLM_MHSR/framework/schemas/report.schema.json`
- `MHLM_MHSR/framework/schemas/provenance_record.schema.json`
- `MHLM_MHSR/framework/schemas/case_study_manifest.schema.json`
- `MHLM_MHSR/framework/taxonomy/case_studies.yml`
- `MHLM_MHSR/framework/taxonomy/model_aliases.yml`
- `MHLM_MHSR/framework/taxonomy/legacy_aliases.yml`
- `MHLM_MHSR/case_studies/lst/README.md`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/README.md`

## Reused Folders

Reused existing repository documentation root:

- `docs/`

Reports were placed there because the user explicitly requested:

- `docs/PRE_PHASE1_CONFLICT_SCAN.md`
- `docs/PHASE1_POSTCHECK.md`

No existing AOIA runtime, prompt, report, provenance, memory, or state folder was reused as a migration target in this phase.

## Avoided Duplications

Avoided:

- `docs/ADR_NEW`
- `lineage_v2`
- `lineage_new`
- `prompts_new`
- `runtime_copy`
- `aoia_core_final_v2`
- duplicate AOIA runtime roots
- mixed LST/AOIA migration folders

The only new root is:

- `MHLM_MHSR/`

## Detected Conflicts

Previously detected and left unchanged:

- `docs/ADR/` and `docs/adr/`
- `memory/` and `runtime/memory/`
- `state/` and `runtime/state/`
- `runtime/prompts/` and `runtime/obsidian_vault/Prompts/`
- `runtime/knowledge/` and `runtime/obsidian_vault/Knowledge/`
- `runtime/logs/` and `runtime/obsidian_vault/Logs/`
- `runtime/logs/sessions/` and `runtime/obsidian_vault/Sessions/`

These were documented instead of normalized during Phase 1.

## Unresolved Ambiguities

- Whether `MHLM_MHSR/` should remain inside `AOIA-Core` long term or become a separate repository later.
- Whether empty migration target folders should receive `.gitkeep` markers in a future commit-oriented phase.
- Whether `docs/ADR/` or `docs/adr/` should become canonical.
- Whether top-level `state/` and `runtime/state/` should be separated by authority class.
- How external provider exports will be normalized without contaminating raw records.

## Recommendations For Future Migration Phases

- Freeze canonical naming before moving any files.
- Add a manifest for each case study before imports.
- Add `.gitkeep` markers only if the skeleton needs to be committed with empty folders.
- Migrate raw artifacts first, then normalized artifacts, then derived synthesis.
- Keep AOIA runtime files in place until a dedicated runtime-boundary phase.
- Do not merge LST and AOIA evidence streams.
- Define provenance IDs before copying provider exports.

## Verification

JSON placeholder schemas were checked with `python3 -m json.tool`.

Result:

```text
schema json OK
```

Phase 1 stop condition satisfied:

- skeleton created
- policies created
- schemas created
- taxonomy created
- case study readmes created
- reports generated
- no migration started
```

## `docs/PHASE1_STRUCTURE_REPORT.md`

- size: 3731 bytes
- sha256: `18b1743898d9ea814c05baa51b6cf4f0a61be873e0c0c84de51ad25300d3fc1c`
- category: docs

```markdown
# Phase 1 Structure Report

Date: 2026-05-24
Repository: `/home/l/Desktop/AOIA-Core`
Phase: MHLM/MHSR Phase 1 framework skeleton initialization

## Scope

This phase initialized the MHLM/MHSR skeleton only.

No runtime refactor was performed.
No AOIA runtime files were moved.
No provider configs were modified.
No routing logic was modified.
No prompt/report migration was performed.

## Created Root

Created one isolated framework root:

- `MHLM_MHSR/`

This avoids creating parallel AOIA runtime folders, runtime copies, duplicate docs roots, or mixed LST/AOIA folders.

## Created Folders

Framework:

- `MHLM_MHSR/framework/`
- `MHLM_MHSR/framework/methodology/`
- `MHLM_MHSR/framework/schemas/`
- `MHLM_MHSR/framework/taxonomy/`
- `MHLM_MHSR/framework/governance/`

Case studies:

- `MHLM_MHSR/case_studies/lst/`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/`

Imports:

- `MHLM_MHSR/imports/provider_exports/raw/`
- `MHLM_MHSR/imports/provider_exports/normalized/`
- `MHLM_MHSR/imports/repo_snapshots/`
- `MHLM_MHSR/imports/git_bundles/`

Framework docs:

- `MHLM_MHSR/docs/`

Per-case migration targets were created for both `lst` and `anti_hallucination_epi_app`:

- `prompts/raw/`
- `prompts/normalized/`
- `reports/raw_provider/`
- `reports/normalized/`
- `reports/synthesis/`
- `lineage/sessions/`
- `lineage/events/`
- `lineage/decisions/`
- `provenance/`
- `contradictions/`
- `archive/`

## Created Files

Methodology:

- `MHLM_MHSR/framework/methodology/inclusion_rules.md`
- `MHLM_MHSR/framework/methodology/evidence_policy.md`
- `MHLM_MHSR/framework/methodology/lineage_policy.md`
- `MHLM_MHSR/framework/methodology/contradiction_policy.md`

Schemas:

- `MHLM_MHSR/framework/schemas/artifact.schema.json`
- `MHLM_MHSR/framework/schemas/lineage_event.schema.json`
- `MHLM_MHSR/framework/schemas/report.schema.json`
- `MHLM_MHSR/framework/schemas/provenance_record.schema.json`
- `MHLM_MHSR/framework/schemas/case_study_manifest.schema.json`

Taxonomy:

- `MHLM_MHSR/framework/taxonomy/case_studies.yml`
- `MHLM_MHSR/framework/taxonomy/model_aliases.yml`
- `MHLM_MHSR/framework/taxonomy/legacy_aliases.yml`

Case studies:

- `MHLM_MHSR/case_studies/lst/README.md`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/README.md`

Reports:

- `docs/PRE_PHASE1_CONFLICT_SCAN.md`
- `docs/PHASE1_STRUCTURE_REPORT.md`

## Naming Conventions

Canonical root:

- `MHLM_MHSR`

Canonical case study IDs:

- `lst`
- `anti_hallucination_epi_app`

Canonical framework subfolders:

- `framework`
- `case_studies`
- `imports`
- `docs`

Canonical artifact flow labels:

- `raw`
- `normalized`
- `derived`
- `synthesis`

## Canonical Case Study Separation Rules

LST/LSC case:

- reserved for scientific reasoning, neutrino anomaly material, LSC/LST lineage, and related research artifacts.
- not evidence for AOIA engineering claims.

AOIA case:

- reserved for anti-hallucination engineering, deterministic runtime, provenance, retrieval boundaries, and AOIA lineage.
- not evidence for LST/LSC scientific claims.

Cross-case references:

- may be documented in future phases only with explicit provenance and no evidential auto-promotion.

## Provenance Contamination Warnings

- Raw provider exports must remain separate from normalized and derived materials.
- Reasoning traces are non-authoritative unless tied to external evidence by future policy.
- Runtime state must not become canonical authority.
- AOIA runtime reports must not be migrated into LST by default.
- LST scientific artifacts must not be used as AOIA runtime validation by default.
- Contradictions must be preserved and not auto-resolved.

## Stop Condition

Phase 1 stopped after skeleton initialization and reports.

No migrations were started.
```

## `docs/PHASE2_DUPLICATION_SCAN.md`

- size: 1914 bytes
- sha256: `f61320684bb8126181ffbbff6fe106436cc94780a9ad71dfea140e594883566b`
- category: docs

```markdown
# Phase 2 Duplication Scan

Date: 2026-05-24
Phase: AOIA forensic migration

## Purpose

Check that Phase 2 did not create duplicate report trees, duplicate imported PDFs, runtime forks, or mixed case-study structures.

## PDF Duplication

Search result:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/archive/AOIA_MASTER_LIBRARY/AOIA_Master_Library.pdf`

Count:

- 1 copy inside `MHLM_MHSR/`

Decision:

- no duplicate PDF import detected.

## Report Duplication

No existing AOIA reports were copied into provider folders.

Provider folders contain `MANIFEST.md` files only. These are classification references, not duplicate report copies.

## Runtime Duplication

No runtime copy was created.

No new folders such as the following were created:

- `runtime_copy`
- `aoia_core_final_v2`
- `reports_final_v2`
- `archive_new`
- `prompts_new`
- `lineage_v2`

## Expected Mirrored Folders

Some repeated folder names are intentional because both case studies maintain separate structures:

- `prompts/`
- `reports/`
- `lineage/`
- `provenance/`
- `contradictions/`
- `archive/`

These are not duplicate structures because they exist under separate canonical case-study roots:

- `case_studies/lsc_neutrino/`
- `case_studies/anti_hallucination_epi_app/`

## Mixed-Case Legacy References

Active taxonomy uses:

- `lsc_neutrino`
- `LSC`

Remaining `LST` references inside `MHLM_MHSR/` are limited to:

- legacy alias mapping in taxonomy files
- unclassified manifest note about historical Phase 1 taxonomy

Historical Phase 1 reports outside `MHLM_MHSR/` were not rewritten.

## Reused Structures

Reused:

- `MHLM_MHSR/`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/`
- existing Phase 1 prompt/report/lineage/provenance/contradiction/archive folders

Created only missing provider and forensic subfolders.

## Result

No destructive duplication detected.

No abandoned temporary structures were left.
```

## `docs/PHASE2_MIGRATION_REPORT.md`

- size: 4393 bytes
- sha256: `4c12e2bbc309bf6bb098331fabdbeec8e7f104c5b54cd64feded0dca02436e8d`
- category: docs

```markdown
# Phase 2 Migration Report

Date: 2026-05-24
Phase: AOIA forensic migration
Repository: `/home/l/Desktop/AOIA-Core`

## Scope

This phase stabilized the AOIA anti-hallucination forensic archive structure.

This phase did not:

- modify AOIA runtime logic
- modify `memory.py`
- change routing systems
- touch provider configs
- migrate RHCSA corpus
- migrate LSC scientific reports
- create new runtime architecture

## Taxonomy Fixes

Active taxonomy was normalized:

- old: `lst` / `LST`
- new: `lsc_neutrino` / `LSC`

Applied change:

- `MHLM_MHSR/case_studies/lst/` -> `MHLM_MHSR/case_studies/lsc_neutrino/`

Updated active taxonomy files:

- `MHLM_MHSR/framework/taxonomy/case_studies.yml`
- `MHLM_MHSR/framework/taxonomy/model_aliases.yml`
- `MHLM_MHSR/framework/taxonomy/legacy_aliases.yml`

Generated:

- `docs/TAXONOMY_NORMALIZATION_REPORT.md`

Historical Phase 1 reports were not rewritten.

## Reused Structures

Reused existing Phase 1 root:

- `MHLM_MHSR/`

Reused existing AOIA case study root:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/`

Reused existing case-study folders where already present:

- `prompts/raw/`
- `prompts/normalized/`
- `reports/raw_provider/`
- `reports/normalized/`
- `reports/synthesis/`
- `lineage/sessions/`
- `lineage/events/`
- `lineage/decisions/`
- `provenance/`
- `contradictions/`
- `archive/`

Created only missing Phase 2 subfolders.

## Created AOIA Forensic Structure

Created under `MHLM_MHSR/case_studies/anti_hallucination_epi_app/`:

- `reports/raw_provider/claude/`
- `reports/raw_provider/gemini/`
- `reports/raw_provider/kimi/`
- `reports/raw_provider/codex/`
- `reports/raw_provider/deepseek/`
- `reports/raw_provider/unknown/`
- `reports/forensic/`
- `reports/governance/`
- `reports/architecture/`
- `unclassified/`
- `archive/AOIA_MASTER_LIBRARY/`

## Imported Archives

Imported one file:

- source: `/home/l/Desktop/AOIA_Master_Library.pdf`
- target: `MHLM_MHSR/case_studies/anti_hallucination_epi_app/archive/AOIA_MASTER_LIBRARY/AOIA_Master_Library.pdf`

Generated:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/archive/AOIA_MASTER_LIBRARY/MASTER_INDEX.md`

The PDF was copied once only.

## Provider Distribution

Provider classification was recorded by manifest only. Reports were not duplicated.

Claude:

- 6 documents identified inside AOIA Master Library.

Codex:

- 4 documents identified inside AOIA Master Library.
- Existing Codex-style repository stabilization reports referenced without copying.

Unknown:

- 10 AOIA Master Library documents have no confident provider attribution from local index scan.

Gemini:

- no standalone Gemini-authored report confidently identified.

Kimi:

- no standalone Kimi-authored report confidently identified.

DeepSeek:

- no standalone DeepSeek-authored report confidently identified.

## Generated Provider Manifests

- `reports/raw_provider/claude/MANIFEST.md`
- `reports/raw_provider/codex/MANIFEST.md`
- `reports/raw_provider/gemini/MANIFEST.md`
- `reports/raw_provider/kimi/MANIFEST.md`
- `reports/raw_provider/deepseek/MANIFEST.md`
- `reports/raw_provider/unknown/MANIFEST.md`

## Prompt Archival Preparation

Generated:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/prompts/PROMPT_ARCHIVE_POLICY.md`

No prompts were normalized or migrated.

## Lineage Preparation

Generated:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/lineage/LINEAGE_POLICY.md`

No lineage synthesis was performed.

## Quarantine Decisions

Generated:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/unclassified/UNCLASSIFIED_MANIFEST.md`

No physical artifacts were moved to `unclassified/`.

Ambiguous cross-domain references were documented for manual review instead of auto-classification.

## Detected Contamination Risks

- AOIA Master Library mentions domain separation and previous mixed-root history; it must remain AOIA engineering archive material, not LSC scientific evidence.
- Provider consensus must not be treated as truth.
- Unknown-provider documents must not be assigned to a provider without provenance.
- Runtime state and reasoning traces remain non-authoritative.
- RHCSA corpus remains outside this migration and must not be pulled into AOIA forensic reports.

## Phase 2 Stop Condition

Phase 2 completed archive stabilization only.

No runtime migration, report migration, prompt normalization, or LSC/RHCSA migration was started.
```

## `docs/PHASE2_UNCLASSIFIED_ITEMS.md`

- size: 1298 bytes
- sha256: `18f45e3f73b5d68d7b6aa1685af0f0e9e5491013d6d03652dbf9b4de9dd07ee4`
- category: docs

```markdown
# Phase 2 Unclassified Items

Date: 2026-05-24
Phase: AOIA forensic migration

## Purpose

Record ambiguous items that should not be automatically classified between:

- `lsc_neutrino`
- `anti_hallucination_epi_app`

## Physical Quarantine

No physical artifacts were moved into unclassified quarantine during Phase 2.

Quarantine manifest:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/unclassified/UNCLASSIFIED_MANIFEST.md`

## Ambiguous References

The following references require care in future phases:

- AOIA Master Library statements about domain separation and prior mixed-root history.
- Phase 1 reports that mention the old `lst` / `LST` taxonomy.
- Repository-level reports that discuss LSC, MHLM/MHSR, and AOIA in the same document.
- Any future provider export that combines scientific anomaly claims with AOIA runtime/governance claims.

## Classification Rule

If an artifact contains both LSC scientific lineage and AOIA engineering lineage:

1. do not classify automatically
2. do not copy it into either case-study evidence tree
3. add a reference to the unclassified manifest
4. require manual review

## Current Status

No unresolved physical items require migration action.

Unresolved ambiguity remains conceptual and will need review during future migration phases.
```

## `docs/PHASE3_DEPENDENCY_RISKS.md`

- size: 1945 bytes
- sha256: `84f1907a2e8bc80c7fc9de9412d9d57b7ad3e594c67bb80f39175c9ab60e1389`
- category: docs

```markdown
# Phase 3 Dependency Risks

Date: 2026-05-24
Phase: AOIA governance preparation

## Purpose

Record dependency and contamination risks before future runtime stabilization.

Primary design document:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/DEPENDENCY_BOUNDARY_ANALYSIS.md`

## Runtime Dependency Risks

- routing layers may remain split-brain if old and new classifiers coexist
- provider adapters may accidentally gain authority logic
- planner fallback may bypass provenance boundaries
- local RHCSA retrieval may contaminate external review unless boundaries remain explicit

## Archive Dependency Risks

- AOIA forensic reports may be treated as live runtime policy
- Master Library summaries may be treated as evidence rather than derived review material
- provider manifests may be mistaken for source files
- archive material may influence runtime without a migration phase

## LSC/AOIA Cross-Domain Risks

- shared MHLM/MHSR terminology can blur case-study boundaries
- old `LST` references can create transitional ambiguity
- LSC scientific lineage must not validate AOIA runtime claims
- AOIA engineering lineage must not validate LSC scientific claims

## Shared Utility Risks

Future utilities become risky if they:

- read both case studies without explicit scope
- normalize prompts across domains
- write shared provenance records
- collapse provider aliases globally
- merge contradiction registries

## Dependency Creep Risks

Avoid:

- `runtime_v2`
- `memory_new`
- `kernel_final`
- duplicate runtime trees
- experimental architecture clones
- archive-to-runtime shortcut imports

## Future Requirements

Before runtime implementation:

- define allowed import directions
- define runtime/archive read boundaries
- define provenance validation API conceptually
- freeze case-study scope identifiers
- design tests for forbidden transitions

## Current Status

No dependencies were modified in Phase 3.
```

## `docs/PHASE3_GOVERNANCE_PREP_REPORT.md`

- size: 2589 bytes
- sha256: `5a031a446e30bcb08af310569a8d9fd469a95d77eb4a2fb9defebd06b4ad08e7`
- category: docs

```markdown
# Phase 3 Governance Preparation Report

Date: 2026-05-24
Phase: AOIA governance preparation
Repository: `/home/l/Desktop/AOIA-Core`

## Scope

This phase prepares future AOIA runtime governance stabilization.

It does not implement runtime governance.

No runtime logic, `memory.py`, routing, provider configs, planner systems, RHCSA corpus, or execution behavior were modified.

## Created Governance Structures

Created under:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/governance/`

Subfolders:

- `authority/`
- `policies/`
- `review/`
- `audit/`
- `risk_models/`

Generated:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/governance/GOVERNANCE_MODEL.md`

## Created Architecture Structures

Created under:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/`

Subfolders:

- `enforcement/`
- `contracts/`

Generated:

- `architecture/enforcement/ENFORCEMENT_LAYER_DESIGN.md`
- `architecture/MEMORY_DOMAIN_SPLIT_PLAN.md`
- `architecture/contracts/RUNTIME_SAFETY_CONTRACTS.md`
- `architecture/DEPENDENCY_BOUNDARY_ANALYSIS.md`

## Created Provenance And Contradiction Preparation

Generated:

- `provenance/PROVENANCE_MODEL_PREP.md`
- `contradictions/CONTRADICTION_TAXONOMY.md`

## Governance Boundaries

Defined authority domains:

- AOIA-Core: runtime engineering authority
- MHLM/MHSR: framework, review, lineage, archive, and case-study separation authority
- LSC: scientific anomaly case-study authority

Boundary rule:

- AOIA engineering claims and LSC scientific claims must not validate each other by proximity.

## Future Enforcement Requirements

Future enforcement must address:

- L0-L5 write boundaries
- evidence promotion restrictions
- provenance validation
- contradiction write rules
- append-only records
- planner inheritance restrictions
- runtime/archive isolation

## Contamination Risks Identified

- runtime state becoming authority
- reasoning traces becoming evidence
- archive reports becoming runtime rules without migration review
- LSC scientific artifacts being used as AOIA validation
- AOIA anti-hallucination claims being used as LSC scientific validation
- provider consensus being mistaken for truth

## Unresolved Architecture Gaps

- no implemented enforcement layer yet
- `memory.py` remains unsplit
- contradiction registry semantics are design-only
- provenance chain-depth policy is not enforced
- planner exclusion rules are not implemented
- runtime/archive boundary still requires future code review

## Phase 3 Stop Condition

Governance preparation completed.

No runtime stabilization was implemented.
```

## `docs/PHASE3_RUNTIME_PREP_STATUS.md`

- size: 1964 bytes
- sha256: `33c0119a70bdaab8be76b9b5833faf64d455b1634c9adc6b8392204dc857dc7c`
- category: docs

```markdown
# Phase 3 Runtime Preparation Status

Date: 2026-05-24
Phase: AOIA governance preparation

## Runtime Status

Runtime remains unchanged by Phase 3.

No changes were made to:

- `runtime/main.py`
- `runtime/tools/memory.py`
- routing systems
- provider configs
- planner systems
- kernel logic
- RHCSA corpus
- execution tools

## Prepared Design Documents

Governance:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/governance/GOVERNANCE_MODEL.md`

Enforcement:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/enforcement/ENFORCEMENT_LAYER_DESIGN.md`

Memory:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/MEMORY_DOMAIN_SPLIT_PLAN.md`

Contracts:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/contracts/RUNTIME_SAFETY_CONTRACTS.md`

Dependencies:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/architecture/DEPENDENCY_BOUNDARY_ANALYSIS.md`

Contradictions:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/contradictions/CONTRADICTION_TAXONOMY.md`

Provenance:

- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/provenance/PROVENANCE_MODEL_PREP.md`

## Unresolved Runtime Concerns

- `memory.py` still needs future physical separation.
- L0-L5 enforcement is not implemented.
- Reasoning trace quarantine is not enforced in code.
- Evidence promotion restrictions are not enforced in code.
- Contradiction write rules are not enforced in code.
- Planner fallback restrictions remain design-only.
- Dependency boundaries still require future verification.

## Future Enforcement Requirements

Future runtime stabilization should implement:

- separate write surfaces for L0-L5
- append-only provenance records
- immutable evidence store
- contradiction registry write policy
- retrieval guard
- planner output exclusion from evidence/provenance
- runtime/archive isolation tests

## Safety Statement

Phase 3 prepared architecture only.

It did not implement runtime stabilization.
```

## `docs/PRE_PHASE1_CONFLICT_SCAN.md`

- size: 3651 bytes
- sha256: `5173d5104a4e8b9b930842ffedb0c27b42f6d22838901bb441d138036f3083f7`
- category: docs

```markdown
# Pre-Phase 1 Conflict Scan

Date: 2026-05-24
Repository: `/home/l/Desktop/AOIA-Core`
Purpose: detect naming conflicts and duplication risks before initializing the MHLM/MHSR Phase 1 skeleton.

## Scope

This scan was performed before creating the `MHLM_MHSR/` skeleton.

Excluded from review noise:

- `.git/`
- `runtime/.venv/`
- `__pycache__/`
- generated package/cache internals

## Existing Relevant Structures

Existing repository surfaces relevant to Phase 1:

- `docs/`
- `docs/ADR/`
- `docs/adr/`
- `docs/architecture/`
- `docs/forensic-runtime-audit/`
- `docs/refactor/`
- `docs/reports/`
- `governance/`
- `memory/`
- `provenance/`
- `retrieval/`
- `contradictions/`
- `runtime/`
- `runtime/knowledge/`
- `runtime/memory/`
- `runtime/obsidian_vault/`
- `runtime/prompts/`
- `runtime/state/`
- `state/`

## Duplicated Folder Names

Detected repeated purpose/name surfaces:

- `memory/` and `runtime/memory/`
- `state/` and `runtime/state/`
- `governance/` and future `MHLM_MHSR/framework/governance/`
- `provenance/` and future case-study `provenance/` folders
- `contradictions/` and future case-study `contradictions/` folders
- `docs/reports/` and future case-study `reports/` folders
- `runtime/prompts/` and future case-study `prompts/` folders

Resolution for Phase 1:

- Do not merge or move any existing folder.
- Keep existing AOIA runtime structures untouched.
- Create the Phase 1 framework under a single isolated `MHLM_MHSR/` root to prevent accidental mixing with AOIA runtime folders.
- Document reuse only where exact target paths already exist.

## Mixed-Case Duplicates

Detected mixed-case naming risks:

- `docs/ADR/` and `docs/adr/`
- `runtime/prompts/` and `runtime/obsidian_vault/Prompts/`
- `runtime/knowledge/` and `runtime/obsidian_vault/Knowledge/`
- `runtime/logs/` and `runtime/obsidian_vault/Logs/`
- `runtime/logs/sessions/` and `runtime/obsidian_vault/Sessions/`

Resolution for Phase 1:

- Do not create new ADR variants.
- Do not create new prompt/report/lineage variants outside the requested Phase 1 skeleton.
- Preserve the existing mixed-case folders as-is for later review.

## Possible Collisions With Requested Skeleton

Requested new root:

- `MHLM_MHSR/`

Current status:

- No existing `MHLM_MHSR/` directory was present at scan time.

Requested case studies:

- `MHLM_MHSR/case_studies/lst/`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/`

Current status:

- No existing `case_studies/` root was present at repository root.
- No existing `lst/` case-study directory was present under repository root.
- No existing `anti_hallucination_epi_app/` directory was present under repository root.

Requested imports:

- `MHLM_MHSR/imports/provider_exports/`
- `MHLM_MHSR/imports/repo_snapshots/`
- `MHLM_MHSR/imports/git_bundles/`

Current status:

- No existing `imports/` root was present at repository root.

## Naming Inconsistencies To Preserve For Now

Existing inconsistencies are recorded but not changed:

- uppercase/lowercase ADR folder split
- top-level architecture reports mixed with `docs/` reports
- runtime state duplicated conceptually across `state/` and `runtime/state/`
- memory/provenance/contradiction concepts represented both as top-level boundary folders and runtime persistence areas

## Phase 1 Safety Decision

Proceed with a single new root:

- `MHLM_MHSR/`

Do not:

- duplicate AOIA runtime
- move AOIA files
- move LST/LSC materials
- create parallel `docs_new`, `prompts_new`, `lineage_v2`, or `runtime_copy` folders
- normalize existing mixed-case folders during this phase

Phase 1 may create only the missing framework skeleton and required Phase 1 reports.
```

## `docs/README.md`

- size: 188 bytes
- sha256: `bb805f3e266e3ebbcdef975ed16a652d8754bca083d469a6986c33470b08aa54`
- category: docs

```markdown
# AOIA Core Docs

Repository-level control documents for the extracted AOIA runtime authority root.

Files:
- `LINEAGE_MAP.md`
- `GIT_HISTORY_CONTINUATION_PLAN.md`
- `RUNTIME_BOUNDARY.md`
```

## `docs/REPOSITORY_CONSTITUTION.md`

- size: 2448 bytes
- sha256: `5132482706f6db8449fffcaec714743b8c84b19e7657f9a630c342160016e628`
- category: docs

```markdown
# Repository Constitution

## Purpose

This repository contains the local terminal application used for controlled
AI-assisted shell, filesystem, browser, memory, and research workflows.

AOIA work must evolve this application gradually. The project should gain
adaptive behavior only through small, reviewable layers that preserve local
control and do not destabilize the existing terminal runtime.

## Current System Identity

- Project root: `/home/l/Desktop/app2terminl_opened`
- Primary CLI entrypoint: `run.sh`
- Web UI entrypoint: `run_web.sh`
- Runtime core: `main.py`
- Existing local knowledge path: `knowledge/`, `tools/rhcsa_search.py`
- Existing state path: `state/`
- Existing logs path: `logs/`
- AOIA foundation path: `adaptive_routing/`

## Non-Negotiable Rules

- Do not redesign the whole application in one step.
- Do not add autonomous behavior without explicit approval.
- Do not connect new routing layers to providers until the local model is
  documented, tested, and reviewed.
- Do not move existing runtime modules unless a migration plan exists.
- Do not store secrets in repository files.
- Do not publish local partner notes, private contacts, tokens, browser state,
  or mailbox data.
- Keep AOIA additions modular and reversible.

## Evolution Model

The application evolves in staged layers:

1. Document the concept.
2. Add a small isolated local module.
3. Add tests or manual validation.
4. Create a checkpoint.
5. Integrate only after explicit approval.

This keeps the system stable while allowing long-term growth.

## AOIA Direction

AOIA means Adaptive Oceanic Intelligence Architecture. In this repository it is
an architecture metaphor and routing discipline inspired by biological systems,
especially Diel Vertical Migration.

AOIA is not AGI, not an autonomous ecosystem, and not a distributed compute
system at this stage.

## Public vs Private Boundary

Public-safe:
- architecture documents
- routing mode definitions
- static local profiles
- tests
- high-level research notes

Private/local-only:
- API keys
- Gmail tokens
- partner identity notes
- browser profiles
- logs containing private user content
- screenshots with personal data
- unpublished research drafts unless approved

## Acceptance Criteria For New AOIA Steps

Each AOIA step must state:

- objective
- files added or changed
- what is intentionally not implemented
- validation performed
- restore/checkpoint path when relevant
```

## `docs/REPOSITORY_STATE_REPORT.md`

- size: 9947 bytes
- sha256: `fa39903b4076ccc59171ff790222357eb9119546a6ce9633fb2812e554d1d872`
- category: docs

```markdown
# Repository State Report

Date: 2026-05-24
Repository: AOIA-Core
Local path: `/home/l/Desktop/AOIA-Core`
Remote: `https://github.com/luciferprosun/AOIA-Core.git`
Branch: `main`
HEAD at scan time: `ad548b73ea7cac692fff37207ae7c7119d986b16`

## Purpose

This report documents the current repository state for external architecture and epistemic-framework review.

This is documentation only. No architecture redesign, runtime refactor, file deletion, or research-material cleanup is performed here.

## Snapshot Policy

The transfer archive preserves repository content needed for:

- architecture review
- MHLM/MHSR framework planning
- AOIA lineage analysis
- provenance structure planning
- case-study separation analysis
- repository stabilization planning

The archive intentionally excludes generated or local machine artifacts:

- `.git`
- `.venv`
- `__pycache__`
- `.pytest_cache`
- `node_modules`
- `dist`
- `build`
- cache folders
- temporary runtime logs
- OS junk files such as `.DS_Store`

The archive keeps documentation, reports, prompts, architecture notes, research artifacts, datasets, experiments, lineage records, runtime state snapshots, and knowledge-base files.

## Current Architecture Overview

AOIA-Core is a Python-centered epistemic/runtime framework with a strong documentation layer around authority boundaries, provenance, memory ontology, deterministic routing, and runtime containment.

The repository currently combines:

- runtime application code under `runtime/`
- epistemic routing and deterministic knowledge components
- RHCSA/Linux command knowledge corpus
- provider adapters and model orchestration components
- persistent memory/state snapshots
- architecture and governance documentation
- forensic audit reports and refactor-preparation notes
- tests for routing, containment, determinism, retrieval, and kernel behavior

The current runtime direction is local-first and deterministic-first. Recent work added a deterministic boundary so external URLs and GitHub/GitLab repository requests bypass RHCSA/local Linux retrieval.

## Major Systems

### Runtime

Location: `runtime/`

Contains:

- `main.py` as the main runtime entrypoint
- `providers/` for model provider adapters
- `tools/` for executor, browser, filesystem, shell, memory, scanner, and validation utilities
- `adaptive_routing/` for routing configuration and epistemic kernel behavior
- `router/` and `orchestrator/` for routing and orchestration remnants
- `commands/` for command abstractions
- `prompts/system_prompt.txt` for planner/runtime prompt behavior
- `state/` and `memory/` for runtime state and memory snapshots

### Knowledge And Retrieval

Location: `runtime/knowledge/`

Contains:

- RHCSA/Linux command knowledge in Markdown
- canonical command JSON
- parsed/indexed/context/injection data
- validation tooling and reports
- source PDF retained as evidence/reference material

This area is central to the deterministic local knowledge path and must be reviewed carefully for retrieval boundaries.

### Memory And Provenance

Locations:

- `runtime/memory/`
- `memory/`
- `provenance/`
- `contradictions/`
- `runtime/provenance_registry.json`
- `runtime/contradiction_registry.json`

The repository currently distinguishes intended memory/provenance concepts in documentation, but runtime persistence is still mixed across JSONL logs, state files, and memory files. This is documented as a known contamination risk in the forensic reports.

### Documentation

Locations:

- root `*.md`
- `docs/`
- `docs/architecture/`
- `docs/forensic-runtime-audit/`
- `docs/refactor/`
- `docs/reports/`
- `docs/checkpoints/`
- `docs/ADR/`
- `docs/adr/`

The documentation layer includes architecture plans, memory ontology, contamination reports, dependency graphs, boundary recommendations, governance notes, runtime reports, ADRs, and checkpoint material.

### Tests

Location: `tests/`

Contains unit tests for:

- deterministic behavior
- epistemic kernel behavior
- epistemic registry behavior
- safeguards
- executor containment
- knowledge validation
- main runtime behavior
- RHCSA retrieval
- routing boundary behavior

### Web Surface

Location: `web/`

Contains minimal web/static surface files. It appears secondary to the runtime and architecture documentation.

## Current Folder Organization

Top-level organization:

- `runtime/` - active runtime code, tools, providers, routing, knowledge corpus, state, memory, and prompts
- `docs/` - architecture, ADRs, reports, checkpoints, and review documents
- `tests/` - unit/regression tests
- `archive/` - quarantine archive boundary
- `governance/` - governance placeholder/documentation surface
- `memory/` - top-level memory boundary documentation
- `provenance/` - top-level provenance boundary documentation
- `retrieval/` - top-level retrieval boundary documentation
- `contradictions/` - contradiction registry documentation surface
- `state/` - top-level state snapshots
- root Markdown files - legacy and current architecture reports/plans

## Research Branches And Experimental Areas

The repository contains multiple research and experimental surfaces:

- `runtime/adaptive_routing/dvm_research.md`
- `runtime/adaptive_routing/environment/`
- `runtime/knowledge/` RHCSA corpus, builders, validators, and context injection files
- `runtime/obsidian_vault/` session/evidence/reasoning vault material
- `docs/refactor/` memory and authority split planning
- `docs/forensic-runtime-audit/` forensic runtime mapping
- root architecture reports such as `AOIA_RUNTIME_MAP.md`, `AOIA_DEPENDENCY_GRAPH.md`, and `AOIA_CONTAMINATION_REPORT.md`

These should be preserved for review even where they overlap or are not yet canonical.

## Duplicated Structures

The repository has intentional or historical duplication that should be reviewed before stabilization:

- `docs/ADR/` and `docs/adr/` both exist.
- Memory concepts appear in root Markdown files, `docs/architecture/`, `docs/refactor/`, `runtime/memory/`, and top-level `memory/`.
- Provenance concepts appear in root documentation, `provenance/`, runtime registries, and Obsidian evidence files.
- State exists both at `runtime/state/` and top-level `state/`.
- Reports exist both as root architecture Markdown files and under `docs/reports/` or `docs/forensic-runtime-audit/`.

No consolidation was performed for this snapshot.

## Mixed Concerns

Areas with mixed runtime/research/documentation concerns:

- `runtime/` contains active code, generated scan output, state snapshots, memory files, knowledge datasets, source PDF material, and Obsidian vault content.
- `runtime/knowledge/` includes source material, derived parsed data, command indexes, validation tools, and generated context/injection products.
- `runtime/memory/` includes runtime memory code and JSONL persistence files.
- Root-level Markdown files include architecture doctrine, audit findings, transition plans, and current-state maps.

These mixed concerns are valuable for review but should be treated as stabilization targets later.

## Possible Chaos Points

Notes for reviewers:

- `runtime/tools/memory.py` remains a high-risk boundary because memory, logs, state, reasoning traces, and evidence concepts have historically overlapped.
- L2 reasoning traces and L4 evidence/provenance must remain separated in future implementation.
- RHCSA/local knowledge retrieval should not handle external repository or web URL requests.
- Browser/external URL handoff exists, but full external-source provenance capture is not finalized.
- Runtime state must not become canonical authority.
- Obsidian vault evidence/reasoning/session files are useful for lineage review but should not be treated as canonical evidence without policy.
- Documentation contains both current doctrine and refactor-preparation notes; reviewers should distinguish frozen doctrine from proposed future work.

## Archive Areas

Archive and quarantine surfaces:

- `archive/quarantine/`
- `docs/checkpoints/`
- `docs/forensic-runtime-audit/`
- `docs/refactor/`
- `runtime/obsidian_vault/`

These areas are preserved in the transfer archive because they carry lineage and review context.

## Naming Inconsistencies

Observed naming inconsistencies:

- mixed uppercase/lowercase ADR directories: `docs/ADR/` and `docs/adr/`
- root reports use several naming conventions: `AOIA_*`, `MEMORY_*`, `CURRENT_*`, `ROUTING_*`
- runtime state exists in both `runtime/state/` and top-level `state/`
- memory/provenance/retrieval names exist as both top-level boundary folders and runtime implementation/persistence areas

No renaming was performed.

## Current Working Tree Notes

At scan time, local changes were present in:

- `docs/reports/FINAL_URL_HANDOFF_PATCH.md`
- `runtime/main.py`
- `runtime/prompts/system_prompt.txt`
- `tests/test_routing_boundary.py`

Untracked runtime/state surfaces were also present:

- `runtime/memory/`
- `runtime/obsidian_vault/`
- `runtime/project_scan.json`
- `runtime/state/`
- `state/`

Generated log directories were excluded from the transfer archive as temporary runtime logs.

## File-Type Summary For Transfer Archive

Approximate included file counts after transfer exclusions:

- Python files: 61
- Markdown files: 130
- JSON files: 26
- JSONL files: 7
- text files: 3
- shell scripts: 3
- PDF files: 1

## Generated Documentation

Generated for this snapshot:

- `docs/FULL_PROJECT_TREE.txt`
- `docs/REPOSITORY_STATE_REPORT.md`

## Review Guidance

This repository should be reviewed as a living stabilization snapshot, not as a clean final product.

The highest-value review targets are:

- runtime boundary placement
- memory/provenance separation
- external URL/repository handoff policy
- RHCSA retrieval containment
- authority registry design
- contradiction registry semantics
- separation between research lineage, evidence, operational logs, and runtime state

No implementation changes are recommended or applied by this report.
```

## `docs/REPO_STRUCTURE.md`

- size: 1920 bytes
- sha256: `688cc725551f8c431a23f38c2d10bc08b339b93e4494d3e3c71252655c64fb9f`
- category: docs

```markdown
# Repository Structure

## Top-Level Layout

```text
app2terminl_opened/
  main.py
  webapp.py
  run.sh
  run_web.sh
  requirements.txt
  README.md
  adaptive_routing/
  commands/
  docs/
  knowledge/
  memory/
  obsidian_vault/
  orchestrator/
  prompts/
  providers/
  reports/
  router/
  state/
  tests/
  tools/
  web/
```

## Runtime Areas

`main.py`
- Owns the CLI runtime loop.
- Coordinates prompt construction, local routing, model calls, execution, and
  memory updates.

`webapp.py`
- Exposes a local HTTP UI wrapper around the same runtime.
- Must remain secondary to the terminal runtime.

`commands/`
- Slash command and local command registry.

`tools/`
- Local execution tools: shell, filesystem, browser, memory, validation, project
  scanning, and web reading.

`providers/`
- Provider adapters and model configuration.
- AOIA must not directly alter provider behavior until a later integration step.

`orchestrator/`
- Existing orchestration helpers.
- New adaptive routing layers should stay outside this directory until the
  contract is stable.

`knowledge/`
- Local operational knowledge engines.
- Currently includes RHCSA/Linux retrieval.

`memory/`
- Runtime memory and memory-hat helpers.

`state/`
- Local runtime state.
- Do not commit or publish secrets, browser profiles, or private state.

`web/`
- Static local web interface.

## AOIA Areas

`adaptive_routing/`
- Isolated AOIA foundation.
- Current status: documentation and static prototypes only.
- No backend integration yet.

`adaptive_routing/environment/`
- Static environmental profiles.
- Current status: local data and simple classifier only.

`docs/`
- Repository constitution, architecture notes, glossary, constraints, and ADRs.

`docs/adr/`
- Architecture Decision Records.
- One decision per file.

## Checkpoints

`checkpoints/`
- Local restore points.
- Checkpoints should describe scope and excluded generated files.
```

## `docs/RHCSA_ENGINE_REVIEW.md`

- size: 2242 bytes
- sha256: `8175065103a5a8fdb585a481309e5a688d76e1307f6f527e6bdf7654d1d10bd6`
- category: docs

```markdown
# RHCSA Engine Review

Review date: 2026-05-21

Reviewed file:

```text
knowledge/rhcsa_engine.py
```

## Classification

Classification: LEGACY, NEEDS ISOLATION.

It is not unsafe by itself, but it is not part of the new static AOIA Knowledge
Pack pipeline.

## Findings

### Retrieval Logic

Present: YES.

The engine imports and calls:

- `search_commands`
- `search_workflows`
- `retrieve_examples`
- `search_rhcsa`

This is local retrieval over existing RHCSA memory/search utilities.

### Semantic Ranking

Present: PARTIAL.

The file does not use embeddings or model-based semantic ranking, but it does
compute a deterministic score and confidence value from counts of matched
commands, workflows, troubleshooting items, examples, related topics, and graph
matches.

### Scoring

Present: YES.

`_score()` assigns fixed weights to result types. `_confidence()` maps score
ranges to `high`, `medium`, `low`, or `none`.

### Hidden State

Present: LOW.

The engine loads `knowledge/command_graph.json` during initialization and stores
it on the instance. It does not appear to write state.

### AI-Like Behavior

Present: NO direct AI behavior.

The file does not call providers, generate text with a model, use embeddings, or
perform autonomous actions. It formats local search results as a local answer.

### Runtime Mutation Risk

Risk: LOW.

The file reads local JSON and returns Python objects/strings. No file mutation
or runtime policy mutation was found.

## Conflict With AOIA Foundation

Conflict level: MEDIUM.

Reason: current AOIA Knowledge Pack work explicitly avoids retrieval, scoring,
ranking, and runtime integration. This file contains older local retrieval and
scoring behavior and can be confused with the new deterministic static pipeline.

## Recommendation

Do not modify the file in this cleanup phase.

Recommended next cleanup action:

- Add a label or README note marking `knowledge/rhcsa_engine.py` as legacy
  runtime memory.
- Keep the new static pipeline under `knowledge/raw`, `knowledge/parsed`,
  `knowledge/canonical`, `knowledge/index`, `knowledge/context`, and
  `knowledge/injection`.
- Do not import the new AOIA static injection artifacts into runtime until a
  later approved integration phase.
```

## `docs/RUNTIME_BOUNDARY.md`

- size: 345 bytes
- sha256: `d44b0a3bce995347fb22e49091e5ccfb2e54356d3df7759ee7f6438bd329adca`
- category: docs

```markdown
# Runtime Boundary

Allowed:
- runtime code
- routing logic
- retrieval systems
- provenance and contradiction infrastructure
- tests and implementation docs

Not allowed as canonical authority:
- external science doctrine
- external epistemic theory papers
- public portal/archive ownership

Rule:
- AOIA remains infrastructure authority only.
```

## `docs/TAXONOMY_NORMALIZATION_REPORT.md`

- size: 1885 bytes
- sha256: `67cf2922048141129377e3699509262e6cf3872df8ad339ba817ed554ffb7282`
- category: docs

```markdown
# Taxonomy Normalization Report

Date: 2026-05-24
Phase: 2 - AOIA forensic migration

## Objective

Normalize the active Phase 1 scientific case-study taxonomy:

- old transitional label: `lst` / `LST`
- new canonical label: `lsc_neutrino` / `LSC`

Historical report titles were not renamed.

## Changes Applied

Renamed active case-study folder:

- `MHLM_MHSR/case_studies/lst/`
- to `MHLM_MHSR/case_studies/lsc_neutrino/`

Updated active taxonomy/methodology files:

- `MHLM_MHSR/framework/taxonomy/case_studies.yml`
- `MHLM_MHSR/framework/taxonomy/model_aliases.yml`
- `MHLM_MHSR/framework/taxonomy/legacy_aliases.yml`
- `MHLM_MHSR/framework/methodology/inclusion_rules.md`
- `MHLM_MHSR/framework/methodology/lineage_policy.md`
- `MHLM_MHSR/framework/methodology/contradiction_policy.md`
- `MHLM_MHSR/case_studies/lsc_neutrino/README.md`
- `MHLM_MHSR/case_studies/anti_hallucination_epi_app/README.md`

## Preserved Historical References

Phase 1 reports and earlier repository documentation may still mention `lst` or `LST` as historical state. Those files were not rewritten because they document what existed during Phase 1.

Preserved examples:

- `docs/PHASE1_STRUCTURE_REPORT.md`
- `docs/PHASE1_POSTCHECK.md`
- `docs/PHASE1_COMPLETE_REPORT.md`
- `docs/PRE_PHASE1_CONFLICT_SCAN.md`

## Canonical Active Taxonomy

Active scientific case-study ID:

- `lsc_neutrino`

Active scientific case-study label:

- `LSC`

Active AOIA engineering case-study ID:

- `anti_hallucination_epi_app`

## Separation Rule

`lsc_neutrino` and `anti_hallucination_epi_app` remain separate.

LSC scientific material must not be used as AOIA runtime/provenance evidence.

AOIA anti-hallucination engineering material must not be used as LSC scientific evidence.

## Notes

No runtime logic, provider configuration, routing logic, memory module, RHCSA corpus, or scientific report corpus was modified.
```

## `docs/TRANSFER_CONTENT_REPORT.txt`

- size: 4840 bytes
- sha256: `21d7793b02957b79f809010b4a1245c5d13c4974cdc4d15dcc92865af81e84af`
- category: docs

```text
AOIA-Core transfer content report
Generated: 2026-05-24
Repository path: /home/l/Desktop/AOIA-Core
Target archive: /home/l/Desktop/FULL_RESEARCH_TRANSFER.zip

Purpose
-------
Create a balanced repository transfer snapshot for external architecture and
epistemic-framework review while preserving important project, research,
lineage, documentation, prompt, config, source, and small dataset content.

Important finding
-----------------
The repository is 212 MB on disk, but most of that size is local/generated
environment data:

- runtime/.venv: 206 MB
- .git: 2.3 MB
- runtime logs: 112 KB
- Python __pycache__ folders: approximately 456 KB total

After excluding only the requested transfer-noise categories, the actual
transferable repository content is approximately 1.81 MB before compression.
The final ZIP may therefore be much smaller than tens of MB because the
remaining repository is mostly text: Markdown, Python, JSON, JSONL, shell
scripts, and one small PDF.

Included top-level content
--------------------------
Approximate included size per top-level entry after transfer exclusions:

- runtime: 1.517 MB, 154 files
- docs: 0.178 MB, 43 files
- tests: 0.042 MB, 9 files
- web: 0.014 MB, 3 files
- README.md: 0.008 MB
- AOIA_RUNTIME_MAP.md: 0.004 MB
- AOIA_MEMORY_ONTOLOGY.md: 0.004 MB
- AOIA_CONTAMINATION_REPORT.md: 0.004 MB
- CURRENT_MEMORY_FLOW.md: 0.004 MB
- ROUTING_AUTHORITY_ANALYSIS.md: 0.003 MB
- ORCHESTRATION_REMNANT_AUDIT.md: 0.003 MB
- MUTABLE_STATE_ISOLATION_PLAN.md: 0.003 MB
- MEMORY_LAYER_DECOMPOSITION.md: 0.003 MB
- MEMORY_BOUNDARY_ANALYSIS.md: 0.003 MB
- FILESYSTEM_ONTOLOGY_LAYOUT.md: 0.003 MB
- AOIA_TRANSITIONAL_COMPONENTS.md: 0.003 MB
- AOIA_CANONICAL_STRUCTURE_PLAN.md: 0.003 MB
- PROVENANCE_FOUNDATION.md: 0.002 MB
- CONTRADICTION_SEMANTICS.md: 0.002 MB
- AOIA_RUNTIME_BOUNDARY_RECOMMENDATION.md: 0.002 MB
- AOIA_DEPENDENCY_GRAPH.md: 0.002 MB
- ROADMAP.md: 0.001 MB
- LICENSE: 0.001 MB
- AUTHORITY_SCOPE.md: 0.001 MB
- state: included
- retrieval: included
- provenance: included
- memory: included
- governance: included
- contradictions: included
- archive: included
- .gitignore: included

Included source folders
-----------------------
- runtime/
- runtime/adaptive_routing/
- runtime/adaptive_routing/environment/
- runtime/commands/
- runtime/knowledge/
- runtime/knowledge/tools/
- runtime/memory/
- runtime/orchestrator/
- runtime/providers/
- runtime/router/
- runtime/tools/
- tests/
- web/

Included documentation and report areas
---------------------------------------
- root architecture Markdown files
- docs/
- docs/ADR/
- docs/adr/
- docs/architecture/
- docs/checkpoints/
- docs/forensic-runtime-audit/
- docs/refactor/
- docs/reports/
- archive/quarantine/
- governance/
- memory/
- provenance/
- retrieval/
- contradictions/

Included prompts/config/state/research artifacts
------------------------------------------------
- runtime/prompts/system_prompt.txt
- runtime/adaptive_routing/*.json
- runtime/adaptive_routing/dvm_research.md
- runtime/adaptive_routing/environment/*
- runtime/knowledge/**/*
- runtime/knowledge/source/RHCSA_Command_Library (1).pdf
- runtime/obsidian_vault/**/*
- runtime/memory/*.jsonl
- runtime/state/*.json
- state/*.json
- runtime/project_scan.json
- runtime/provenance_registry.json
- runtime/contradiction_registry.json

Included file-type summary
--------------------------
- Python source files: present
- Markdown docs/reports/architecture notes: present
- JSON configs/datasets/state files: present
- JSONL memory/session/lineage files: present
- shell scripts: present
- prompts: present
- PDF source artifact: present
- web files: present

Excluded folders and artifacts
------------------------------
Excluded by policy:

- .git
- runtime/.venv
- node_modules
- __pycache__
- .pytest_cache
- .cache
- cache
- build
- dist
- runtime/logs
- *.pyc
- .DS_Store

Excluded folder sizes observed
------------------------------
- runtime/.venv: 206 MB
- .git: 2.3 MB
- runtime/logs: 112 KB
- runtime/tools/__pycache__: 156 KB
- tests/__pycache__: 60 KB
- runtime/__pycache__: 52 KB
- runtime/commands/__pycache__: 40 KB
- runtime/providers/__pycache__: 40 KB
- runtime/orchestrator/__pycache__: 32 KB
- runtime/adaptive_routing/__pycache__: 24 KB
- runtime/knowledge/__pycache__: 20 KB
- runtime/memory/__pycache__: 16 KB
- runtime/router/__pycache__: 16 KB

Large file scan
---------------
No transferable files larger than 20 MB were found outside excluded folders.

Largest included non-source artifact:

- runtime/knowledge/source/RHCSA_Command_Library (1).pdf: 153,760 bytes

Archive expectation
-------------------
The final ZIP is expected to remain small because the included content is
small and highly compressible. A small final archive does not indicate missing
project content in this repository if the verification checks pass.
```

## `docs/adr/0001-keep-aoia-isolated.md`

- size: 1311 bytes
- sha256: `2ecd998937dd00f4588163226590d74ab1eeba948850c2a75fc573f4e89c7f1b`
- category: docs

```markdown
# ADR 0001: Keep AOIA Isolated Until Explicit Integration

Status: accepted

Date: 2026-05-21

## Context

The terminal app already has a working runtime, provider configuration, local
knowledge routing, approval gates, logs, memory, CLI, and web UI.

AOIA introduces a new adaptive routing direction inspired by DVM and ecosystem
behavior. Integrating that too early would risk changing provider behavior,
token usage, or terminal workflows before the design is stable.

## Decision

AOIA files remain isolated under `adaptive_routing/` and documentation under
`docs/`.

No AOIA module may control runtime behavior, provider selection, shell
execution, browser automation, or memory writes until a later approved
integration step.

## Consequences

Positive:
- Existing terminal behavior remains stable.
- AOIA can evolve through small reviewable modules.
- Future integration points can be designed with clearer contracts.

Negative:
- AOIA will not affect runtime efficiency immediately.
- Some early modules may feel like scaffolding before they become useful.

## Validation

Validation for this ADR is structural:

- AOIA files are isolated.
- No imports from `adaptive_routing/` are added to `main.py`.
- No provider code is modified for AOIA.
- No shell/browser executor behavior is modified for AOIA.
```

## `docs/adr/0002-minimal-deterministic-router-skeleton.md`

- size: 1101 bytes
- sha256: `c508391d2c90a03561e989a828147385d7d56e2f86ed59965469573f29ae3ee9`
- category: docs

```markdown
# ADR 0002: Minimal Deterministic Router Skeleton

Status: accepted

Date: 2026-05-21

## Context

AOIA needs a tiny deterministic routing skeleton before any adaptive runtime
integration. The goal is to define a stable shape for later routing work without
adding networking, provider selection, or backend changes.

## Decision

Add one pure function:

```python
select_depth(pressure: int) -> str
```

It returns exactly one of:

- `shallow`
- `mid`
- `deep`

The function is deterministic and uses fixed thresholds:

- `0..33` -> `shallow`
- `34..66` -> `mid`
- `67+` -> `deep`

Negative pressure is invalid and raises `ValueError`.

## Consequences

Positive:
- Simple contract for later tests and integration.
- No network behavior.
- No provider behavior.
- No runtime side effects.

Negative:
- The pressure score is not yet derived from real system conditions.
- The names are placeholders for future AOIA semantics.

## Validation

Manual validation:

- `select_depth(0)` returns `shallow`
- `select_depth(34)` returns `mid`
- `select_depth(67)` returns `deep`
- module compiles with Python
```

## `docs/adr/0003-immutable-startup-configuration.md`

- size: 1086 bytes
- sha256: `aacbbafdaafe7b93e45cb792e0fc6318e2d5b38eb55304bd4cbf25846c4682ff`
- category: docs

```markdown
# ADR 0003: Immutable Startup Configuration

Status: accepted

Date: 2026-05-21

## Context

AOIA needs configuration before runtime integration, but mutable runtime config
would make routing behavior harder to audit. The early system should load config
once, validate it, and expose it as read-only data.

## Decision

Add:

- `adaptive_routing/aoia_config.json`
- `adaptive_routing/config_loader.py`

The loader returns a frozen dataclass and wraps runtime policy in a read-only
mapping. The config defines:

- config version
- three depths
- pressure thresholds
- startup-only, no-network, readonly runtime policy

## Consequences

Positive:
- AOIA config has a clear contract.
- Later routing logic can use validated thresholds.
- Runtime mutation is blocked by type and structure.

Negative:
- Config changes require process restart in future integrations.
- No live tuning exists yet.

## Validation

Manual validation:

- JSON parses.
- Python compiles.
- `load_config()` returns expected values.
- mutation attempts fail for frozen dataclass fields and runtime policy mapping.
```

## `docs/adr/0004-stdout-only-plain-text-logging.md`

- size: 887 bytes
- sha256: `6fe2a2165ba897e9024851ddd9c6a515983ab18ab01057e4f3287e0b536a72cf`
- category: docs

```markdown
# ADR 0004: Stdout-Only Plain-Text Logging

Status: accepted

Date: 2026-05-21

## Context

AOIA will eventually make routing recommendations. Those recommendations need
to be explainable, but adding dashboards or telemetry now would create
unnecessary complexity and privacy risk.

## Decision

AOIA logging starts with:

- stdout only
- plain text
- correlation ids
- no dashboards
- no external services

Add a small helper:

- `adaptive_routing/stdout_logger.py`

## Consequences

Positive:
- Easy to inspect in terminal sessions.
- No storage or privacy expansion.
- No new dependencies.
- Suitable for early deterministic prototypes.

Negative:
- Logs are not persisted unless the parent process captures stdout.
- No search UI or dashboard exists.

## Validation

Manual validation:

- module compiles
- running module prints one plain-text log line
- runtime remains unmodified
```

## `docs/adr/0005-test-constitution-determinism-first.md`

- size: 875 bytes
- sha256: `28e7d96f7206fceb4b90953a7ed5c6cb88f0dc7cbdc05490a069bc4b8161a9bd`
- category: docs

```markdown
# ADR 0005: Test Constitution, Determinism First

Status: accepted

Date: 2026-05-21

## Context

AOIA will later influence routing decisions. Before integration, its core must
be deterministic, easy to test, and fail-fast on invalid input.

## Decision

Add a dedicated AOIA test module:

- `tests/test_aoia_determinism.py`

AOIA tests prioritize:

- same input -> same output
- explicit boundary checks
- invalid input raises
- readonly config checks
- no network or provider requirements

## Consequences

Positive:
- Future routing changes have a stable safety net.
- Runtime integration can be gated by tests.
- Failures happen early and locally.

Negative:
- Current tests are narrow by design.
- No behavioral runtime coverage exists yet because AOIA is not integrated.

## Validation

Validation command:

```bash
python3 -m unittest tests.test_aoia_determinism
```
```

## `docs/adr/README.md`

- size: 411 bytes
- sha256: `697c68d69e4c2508fd534d548782f0f8b5956b8e52e9a7e89b0bf5084b25f6d4`
- category: docs

```markdown
# Architecture Decision Records

This directory stores Architecture Decision Records for the terminal app and
AOIA expansion.

## Format

Each ADR should include:

- title
- status
- date
- context
- decision
- consequences
- validation

## Status Values

- `proposed`
- `accepted`
- `superseded`
- `rejected`

## Naming

Use:

```text
NNNN-short-title.md
```

Example:

```text
0001-keep-aoia-isolated.md
```
```

## `docs/checkpoints/2026-05-23/AOIA_DAILY_CHECKPOINT.md`

- size: 10920 bytes
- sha256: `a55db02a207f78f907eb59459feda9fb3799b970c4e5f744ae010a3fdeda7c4a`
- category: docs

```markdown
# AOIA Daily Checkpoint

Date: 2026-05-23
Repository: `/home/l/Desktop/AOIA-Core`
Remote: `https://github.com/luciferprosun/AOIA-Core.git`
Branch: `main`
Current commit at checkpoint creation: `5674fd4`
Mode: safe archive / no runtime behavior changes during checkpoint creation

## Repository Verification

Verified working directory:

```text
/home/l/Desktop/AOIA-Core
```

Verified remote:

```text
origin  https://github.com/luciferprosun/AOIA-Core.git (fetch)
origin  https://github.com/luciferprosun/AOIA-Core.git (push)
```

Verified branch:

```text
main
```

Recent commits:

```text
5674fd4 Freeze AOIA memory model doctrine
1b349a9 AOIA memory ontology foundation checkpoint
aa29a0e AOIA runtime stabilization checkpoint
b82e559 Add AOIA quarantine boundary
836d76e Tighten authority boundary wording
```

Status before this checkpoint was written:

```text
## main...origin/main
 M runtime/tools/executor.py
?? docs/forensic-runtime-audit/
?? docs/refactor/
?? docs/reports/
?? state/
?? tests/test_executor_containment.py
```

## Key Conclusion

AOIA-Core has moved from conceptual app development toward a constrained epistemic runtime foundation.

The work completed today changed the project direction from broad runtime construction toward explicit epistemic boundaries: memory ontology, authority classification, contamination mapping, and the first minimal containment of pseudo-evidence.

## Model-Audit Convergence

Audits from Claude, Gemini, DeepSeek, Kimi, and Codex converged on the same core risks:

- `runtime/tools/memory.py` is the highest-risk convergence point.
- L2 reasoning traces must never become evidence.
- L1 operational logs must never become evidence.
- Runtime state must not define canonical authority.
- Provenance must be enforceable, not only described.
- Contradictions must be preserved and not auto-resolved.
- Retrieval must not read runtime continuity, operational logs, reasoning traces, or vault projections as source material.
- Current runtime was partially ready for doctrine freeze, but not ready for broad refactor.

## Phase 1A Result

Phase 1A froze the canonical AOIA memory ontology.

Created:

- `docs/architecture/AOIA_MEMORY_MODEL.md`
- `docs/architecture/FORBIDDEN_MEMORY_FLOWS.md`
- `docs/architecture/MEMORY_LAYER_ACCESS_MATRIX.md`

Frozen layers:

- L0 Ephemeral Runtime State
- L1 Operational Logs
- L2 Reasoning Traces
- L3 Provenance Records
- L4 Immutable Evidence
- L5 Contradiction Registry

Frozen prohibitions:

- L2 reasoning traces are not evidence.
- L1 operational logs are not evidence.
- Runtime outputs are not authority.
- Cloud planner outputs are not evidence without external provenance.
- Contradictions must not be auto-resolved.
- Retrieval must not index L0/L1/L2/Vault.

## Phase 1B Result

Phase 1B mapped the dependency and contamination structure around `runtime/tools/memory.py`.

Created:

- `docs/refactor/MEMORY_SPLIT_PLAN.md`
- `docs/refactor/MEMORY_DEPENDENCY_GRAPH.md`
- `docs/refactor/MEMORY_CONTAMINATION_GRAPH.md`
- `docs/refactor/MEMORY_AUTHORITY_BOUNDARIES.md`

Main finding:

```text
ExecutionEngine._record_execution()
  -> MemoryStore.append_evidence("action_result", payload)
```

This was identified as the highest-risk active pseudo-evidence flow.

Other findings:

- `memory.py` combines L0 runtime state, L1 logs, L2 reasoning, pseudo-L4 evidence, browser/session capture, and Vault projection.
- Retrieval currently reads deterministic knowledge and registries, not runtime memory, but this is not enforced by a guard.
- Vault behaves as a projection surface but was not formally labeled projection-only before Phase 1C.

## Phase 1C Result

Phase 1C froze canonical authority semantics.

Created:

- `docs/refactor/CANONICAL_AUTHORITY_GRAPH.md`

Canonical authority hierarchy:

1. L3 provenance records
2. L5 contradiction registry
3. L4 immutable evidence
4. RHCSA deterministic knowledge artifacts
5. operator approvals for execution permission only
6. L2 reasoning traces for audit only
7. L1 operational logs for replay only
8. L0 runtime state for continuity only
9. vault projections for human readability only

Vault semantics:

- Obsidian Vault is projection-only.
- Vault is not evidence.
- Vault is not provenance.
- Vault is not a retrieval source.
- Vault is not canonical authority.

## Phase 2A Result

Phase 2A performed the first live runtime containment operation.

Modified:

- `runtime/tools/executor.py`

Added:

- `tests/test_executor_containment.py`

Containment performed:

```text
action_result
  -> history/replay/debug
  -> NOT evidence
```

The removed behavior:

```python
self.memory_store.append_evidence("action_result", payload)
```

Preserved behavior:

- command log write
- `record_result(result)`
- `append_history("action_result", payload)`
- browser event logging
- recent outputs
- replay continuity
- debugging visibility
- runtime continuity

New authority labeling:

```python
"authority": {
    "classification": "operational_event",
    "retention": "replay_only",
    "non_authoritative": True,
    "canonical_evidence": False,
}
```

Frozen doctrine now reflected in runtime payloads:

- `action_result` is `operational_event`.
- `action_result` is `replay_only`.
- `action_result` is `non_authoritative`.
- `action_result` has `canonical_evidence: False`.

## Files Changed Today

Architecture doctrine and refactor planning:

- `docs/architecture/AOIA_MEMORY_MODEL.md`
- `docs/architecture/FORBIDDEN_MEMORY_FLOWS.md`
- `docs/architecture/MEMORY_LAYER_ACCESS_MATRIX.md`
- `docs/refactor/MEMORY_SPLIT_PLAN.md`
- `docs/refactor/MEMORY_DEPENDENCY_GRAPH.md`
- `docs/refactor/MEMORY_CONTAMINATION_GRAPH.md`
- `docs/refactor/MEMORY_AUTHORITY_BOUNDARIES.md`
- `docs/refactor/CANONICAL_AUTHORITY_GRAPH.md`

Validation and checkpoint reporting:

- `docs/reports/PHASE_1A_GIT_VALIDATION.md`
- `docs/checkpoints/2026-05-23/AOIA_DAILY_CHECKPOINT.md`
- `docs/checkpoints/2026-05-23/NEXT_ACTIONS.md`

Runtime containment:

- `runtime/tools/executor.py`
- `tests/test_executor_containment.py`

Preserved but not yet committed/decided:

- `docs/forensic-runtime-audit/**`
- `state/model_config.json`
- `state/providers.json`

## Tests Run

Focused Phase 2A containment test:

```text
PYTHONPATH=runtime python3 -m unittest tests.test_executor_containment
```

Expected result:

```text
.
----------------------------------------------------------------------
Ran 1 test

OK
```

Known broader test limitation:

- `tests.test_main` currently fails to import because `runtime/main.py` imports `memory.rhcsa_context`, which is not present as an importable module in the current test environment.
- This was not fixed today because Phase 2A was restricted to minimal pseudo-evidence containment.

## Current Runtime Status

Runtime behavior was not broadly refactored.

Current status:

- Runtime execution path remains intact.
- `action_result` no longer writes to evidence-like memory.
- Operational history remains available.
- Command logs remain available.
- Runtime continuity remains available through `recent_outputs`.
- Retrieval logic is unchanged.
- Provider logic is unchanged.
- Routing logic is unchanged.
- Governance runtime is unchanged.

Authority status:

- Runtime is safer than before Phase 2A because the strongest pseudo-evidence leak was contained.
- Runtime is not yet fully authority-safe because strict L4 evidence, retrieval guard, L2 quarantine, and CAS evidence storage are not implemented.

## Current Canonical Doctrine

The current AOIA doctrine is:

- L2 reasoning traces are not evidence.
- L1 operational logs are not evidence.
- Runtime outputs are not authority.
- Cloud planner outputs are not evidence without external provenance.
- Obsidian Vault is projection-only.
- Contradictions must not be auto-resolved.
- Retrieval must not index L0/L1/L2/Vault.
- `action_result` is `operational_event / replay_only / non_authoritative / canonical_evidence: False`.

## Current Unresolved Risks

High risk:

- `memory.py` is still a mixed L0/L1/L2/pseudo-L4/projection module.
- `append_evidence()` still accepts arbitrary payloads from other callers.
- Existing legacy `memory/evidence_memory.jsonl` should be treated as quarantined mixed memory if present in runtime output.
- Retrieval guard is not implemented.

Medium risk:

- Vault projection is still generated by runtime side effects.
- L2 reasoning traces are not physically quarantined.
- Provenance registry is not append-only event history.
- Contradiction registry has no append-only runtime event model.
- `KnowledgeRouter` still writes token savings reports under `state/`.

Operational risk:

- `state/` remains untracked runtime state inside the repository working tree.
- `docs/forensic-runtime-audit/` remains untracked and needs a commit/archive decision.
- Full test suite import remains blocked by `memory.rhcsa_context` missing from the import path.

## Next Recommended Phase

Recommended next phase:

- Phase 2A validation and checkpoint commit, or Phase 2B only after the current checkpoint is accepted.

Safest Phase 2B candidate:

- Add a narrow evidence-write validation boundary for `append_evidence()` callers without redesigning the evidence store.

Do not start with:

- splitting `memory.py`
- moving runtime directories
- adding retrieval guard
- changing provider logic
- changing routing logic
- changing governance runtime
- redesigning Vault

## Rollback Notes

Phase 2A rollback is simple:

- restore the removed executor line:

```python
self.memory_store.append_evidence("action_result", payload)
```

- remove `tests/test_executor_containment.py`
- remove the authority label block if full rollback is required

No data migration is involved.
No registry migration is involved.
No provider/routing/governance changes are involved.

## DO NOT TOUCH List

Until the next explicit phase:

- Do not refactor `memory.py`.
- Do not split modules.
- Do not move runtime state directories.
- Do not modify providers.
- Do not modify routing.
- Do not implement governance.
- Do not implement retrieval guard.
- Do not redesign Vault.
- Do not treat `memory/evidence_memory.jsonl` as canonical L4.
- Do not commit `state/` without explicit policy.
- Do not push to LSC or MHLM/MDLH repositories.
- Do not broaden Phase 2A beyond pseudo-evidence containment.

## Safe-To-Proceed Assessment

Safe to proceed tomorrow:

- Yes, for narrow validation, checkpointing, and the next explicitly scoped containment phase.

Not safe yet:

- broad memory refactor
- architecture split
- retrieval redesign
- governance implementation
- provider/routing changes

Recommended next action tomorrow:

- Cleanly decide which untracked documentation belongs in the next AOIA-Core commit.
- Keep `state/` out of source authority unless a runtime-state policy is accepted.
- Commit Phase 1B/1C/2A documentation and Phase 2A containment together or in separate reviewed commits.
```

## `docs/checkpoints/2026-05-23/NEXT_ACTIONS.md`

- size: 2638 bytes
- sha256: `72e957aedeb0f954d8f1fe17eceb8d0efede2ae8bf6280489e9cfc365cea9d66`
- category: docs

```markdown
# Next Actions

Date: 2026-05-23
Repository: `/home/l/Desktop/AOIA-Core`
Mode: checkpoint guidance

## Recommended Next Step

The next safest step is repository validation and checkpoint commit hygiene.

Before any new implementation:

- Review untracked documentation under `docs/refactor/`.
- Review untracked validation report under `docs/reports/`.
- Decide whether `docs/forensic-runtime-audit/` should be committed as architecture audit material.
- Keep `state/` uncommitted unless a specific runtime-state policy is accepted.
- Confirm Phase 2A containment diff remains minimal.
- Run the focused containment test again.

## What Must Not Be Done Next

Do not:

- split `memory.py`
- create memory adapters
- redesign retrieval
- modify providers
- modify routing
- implement governance
- redesign Vault
- move runtime directories
- treat `memory/evidence_memory.jsonl` as canonical L4
- index L0/L1/L2/Vault in retrieval
- commit `state/` by default
- push to LSC or MHLM/MDLH repositories

## Safest Phase 2B Candidate

Safest Phase 2B candidate:

- Add a narrow evidence-write validation boundary around `append_evidence()` usage.

Goal:

- Ensure only explicitly approved evidence-like events can call evidence storage.
- Preserve existing kernel evidence flow until L4 schema exists.
- Do not redesign evidence storage yet.
- Do not implement CAS yet.
- Do not implement retrieval guard yet.

Alternative safe Phase 2B candidate:

- Add documentation-only migration notes for legacy `memory/evidence_memory.jsonl` as quarantined mixed memory.

## Repo Readiness For Next Implementation Phase

Ready:

- Ready for narrow pseudo-evidence containment validation.
- Ready for documentation checkpointing.
- Ready for focused regression tests around executor containment.

Not ready:

- Not ready for broad memory split.
- Not ready for retrieval guard implementation.
- Not ready for CAS evidence store implementation.
- Not ready for governance runtime implementation.

Reason:

- Phase 2A contained the strongest active leak, but L4 schema, CAS evidence model, L2 physical quarantine, provenance event schema, and contradiction event schema are not yet implemented.

## Tomorrow's Recommended Order

1. Validate current worktree.
2. Decide which documentation directories should be committed.
3. Keep `state/` out of git unless explicitly approved.
4. Commit Phase 2A containment and checkpoint docs.
5. Only then define Phase 2B scope.

## Stop Rule

If a proposed next change touches provider logic, routing logic, governance, or broad memory architecture, stop and create a new explicit phase document before implementation.
```

## `docs/forensic-runtime-audit/CANONICAL_REFACTOR_PREP.md`

- size: 4669 bytes
- sha256: `a397b0b84d1e33d2c3d1738e938045b48b288e7670f2d6b88cdc190396c6ab3f`
- category: docs

```markdown
# Canonical Refactor Prep

Status: preparation only. No refactor implemented.

## Guiding principle

The safest refactor path is boundary-first, not feature-first.

Do not start by changing provider behavior, orchestrator behavior, or routing semantics.
Start by isolating mutable state and removing ambiguity in the runtime substrate.

## Safe migration order

### Phase 1: make memory boundaries explicit

Target:

- `runtime/tools/memory.py`
- `runtime/main.py`
- `runtime/tools/executor.py`

Goal:

- split live runtime state from append-only logs
- split evidence from reasoning
- split notebook/vault projection from canonical state
- define one authoritative write path per layer

Rollback-safe because:

- it is a data-shape and boundary split before behavior changes
- the runtime can still use the old structures temporarily through adapters

### Phase 2: choose one canonical local routing authority

Target:

- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/orchestrator/knowledge_router.py`

Goal:

- keep one routing authority for RHCSA/local knowledge
- demote the other to compatibility or archive status
- remove split-brain routing decisions

Rollback-safe because:

- the old router can be retained behind a compatibility switch during transition

### Phase 3: separate provider configuration from provider execution

Target:

- `runtime/providers/config.py`
- `runtime/providers/*.py`

Goal:

- keep model selection/persistence separate from provider instantiation
- keep env loading separate from fallback policy
- keep provider adapters pure

Rollback-safe because:

- provider behavior stays unchanged while config handling is extracted

### Phase 4: reduce `main.py` to a thin coordinator

Target:

- `runtime/main.py`

Goal:

- leave prompt assembly and execution loop coordination
- move policy, persistence, and routing decisions behind dedicated services
- keep CLI behavior stable

Rollback-safe because:

- user-facing commands can stay unchanged while internals move behind adapters

### Phase 5: retire transitional orchestrator paths

Target:

- `runtime/orchestrator/gemini_gemma.py`
- `runtime/orchestrator/knowledge_router.py`

Goal:

- quarantine or remove legacy orchestration after canonical routing is stable

Rollback-safe because:

- orchestration can be disabled by default while still preserved for archive review

## Files/modules that must be isolated first

1. `runtime/tools/memory.py`
2. `runtime/main.py`
3. `runtime/tools/executor.py`
4. `runtime/adaptive_routing/epistemic_kernel.py`
5. `runtime/orchestrator/knowledge_router.py`
6. `runtime/providers/config.py`
7. `runtime/orchestrator/gemini_gemma.py`

## Files/modules that must not be touched before governance layer is finalized

These are the highest-risk modules because they encode policy, fallback behavior, or mutable authority:

- `runtime/providers/config.py`
- `runtime/providers/aureon_provider.py`
- `runtime/providers/gemini_provider.py`
- `runtime/providers/openai_compatible.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/orchestrator/gemini_gemma.py`
- `runtime/tools/memory.py`
- `runtime/tools/memory_hats.py`
- `runtime/tools/executor.py`
- `runtime/main.py` prompt/model loop sections

## Dependency-safe refactor sequence

1. Introduce explicit adapters around the existing memory writer methods.
2. Split durable state from append-only logs.
3. Move evidence/reasoning into separate sinks.
4. Select one local RHCSA routing authority.
5. Separate provider config and provider execution.
6. Convert `main.py` into orchestration-only coordination.
7. Only after that, implement governance-layer boundaries.

## Estimated implementation phases

- **Phase A**: boundary inventory and adapter scaffolding
- **Phase B**: memory split and state normalization
- **Phase C**: routing authority consolidation
- **Phase D**: provider/config separation
- **Phase E**: thin coordinator refactor
- **Phase F**: governance layer introduction

## Safest first refactor target

`runtime/tools/memory.py`

Reason:

- it currently carries the highest contamination density
- it is the main boundary where state, logs, evidence, reasoning, and Obsidian projection collide
- cleaning this first reduces downstream ambiguity in `main.py`, `executor.py`, and the web runtime

## What should remain untouched until governance is finalized

- cloud provider selection policy
- model fallback semantics
- orchestrator plan generation
- knowledge routing threshold semantics
- contradiction interpretation semantics
- provenance registry generation semantics
- browser/tool execution semantics
```

## `docs/forensic-runtime-audit/CURRENT_RUNTIME_TOPOLOGY.md`

- size: 5954 bytes
- sha256: `cc974b71c097414bc99d70e7b4d29bdc6e5510f49a04eef9efe11fdd068aadca`
- category: docs

```markdown
# Current Runtime Topology

Status: forensic mapping only. No runtime changes made.

## Runtime entrypoints

- [`runtime/main.py`](../../runtime/main.py) is the primary terminal entrypoint.
- [`runtime/webapp.py`](../../runtime/webapp.py) is the web entrypoint.
- [`runtime/run.sh`](../../runtime/run.sh) and [`runtime/run_web.sh`](../../runtime/run_web.sh) are thin launch wrappers.
- [`runtime/install.sh`](../../runtime/install.sh) is a bootstrap/install helper.

## High-level flow

The live runtime follows this path:

`user input -> command registry -> local router / epistemic kernel / knowledge router -> provider manager -> model request -> JSON validation -> executor -> memory + logs -> transcript/status`

The important split is:

- local fast-path handling in `runtime/main.py`
- deterministic RHCSA retrieval in `runtime/adaptive_routing/epistemic_kernel.py`
- legacy RHCSA routing in `runtime/orchestrator/knowledge_router.py`
- cloud-provider fallback in `runtime/providers/config.py`
- action dispatch in `runtime/tools/executor.py`

## Import graph

### Core runtime

- `runtime/main.py`
  - `commands.build_command_registry`
  - `adaptive_routing.epistemic_kernel.AOIAEpistemicKernel`
  - `memory.rhcsa_context.inject_linux_context`
  - `orchestrator.GeminiGemmaOrchestrator`
  - `orchestrator.knowledge_router.KnowledgeRouter`
  - `providers.ProviderManager`
  - `router.LocalRouter`
  - `tools.executor.ExecutionEngine`
  - `memory.gemma_worker_memory.GemmaWorkerMemory`
  - `tools.memory_hats.MemoryHatStore`
  - `tools.memory.MemoryStore`
  - `tools.system_info.detect_desktop_dir`
  - `tools.validator.extract_json_object`, `validate_action`

### Routing and retrieval

- `runtime/router/local_router.py` handles trivial local commands.
- `runtime/adaptive_routing/epistemic_kernel.py` performs deterministic RHCSA retrieval and contradiction-aware output.
- `runtime/orchestrator/knowledge_router.py` performs legacy local-memory routing for Linux operational requests.
- `runtime/tools/rhcsa_search.py` is the deterministic keyword/tag/exact/grep retrieval engine.

### Execution and persistence

- `runtime/tools/executor.py` dispatches tool actions and records execution.
- `runtime/tools/memory.py` owns runtime state, append-only logs, browser logs, and Obsidian vault projection.
- `runtime/tools/memory_hats.py` stores active context overlays in `memory/hats` and `state/active_hat.json`.
- `runtime/tools/epistemic_registry.py` builds provenance and contradiction registries.

### Providers

- `runtime/providers/config.py` owns model selection, env loading, provider fallback, and provider instantiation.
- `runtime/providers/gemini_provider.py`, `runtime/providers/aureon_provider.py`, `runtime/providers/openai_compatible.py` are provider adapters.

### Web

- `runtime/webapp.py` wraps `AgentRuntime` in a threaded HTTP service.

## Write paths

### Mutable runtime state

- `state/agent_state.json`
- `state/model_config.json`
- `state/providers.json`
- `state/active_hat.json`
- `state/token_savings_report.json`
- `state/browser_profile/`

### Runtime memory and logs

- `memory/history.jsonl`
- `memory/evidence_memory.jsonl`
- `memory/reasoning_trace.jsonl`
- `memory/hats/*.json`
- `logs/sessions/*.jsonl`
- `logs/commands/*.json`
- `logs/errors/*.json`
- `logs/browser/*.jsonl`
- `screenshots/*`

### Obsidian projection layer

- `obsidian_vault/Daily/*.md`
- `obsidian_vault/Sessions/*.jsonl`
- `obsidian_vault/Evidence/*.md`
- `obsidian_vault/Reasoning/*.md`
- `obsidian_vault/Logs/`
- `obsidian_vault/.obsidian/app.json`

### Knowledge and registry files

- `runtime/provenance_registry.json`
- `runtime/contradiction_registry.json`
- `runtime/knowledge/index/command_index.json`
- `runtime/knowledge/context/context_pack.json`
- `runtime/knowledge/injection/injected_context.json`
- `runtime/knowledge/parsed/rhcsa_sections.json`
- `runtime/knowledge/examples/*.json`
- `runtime/knowledge/raw/rhcsa_raw.txt`

## Read paths

- `runtime/main.py` reads prompt template, current state, provider status, local RHCSA context, knowledge routing, and epistemic flags.
- `runtime/providers/config.py` reads `state/model_config.json`, `state/providers.json`, and API env files under `~/.config/*/api.env`.
- `runtime/adaptive_routing/epistemic_kernel.py` reads the provenance and contradiction registries plus all RHCSA knowledge artifacts.
- `runtime/tools/rhcsa_search.py` reads the local RHCSA knowledge modules and example indexes.
- `runtime/tools/memory.py` reads/writes the same state and projection files on each step.

## Mutable state locations

The following locations are mutable and currently mixed with source-facing runtime code:

- `runtime/tools/memory.py` state + logs + vault projection
- `runtime/tools/memory_hats.py` overlays stored under `memory/hats`
- `runtime/providers/config.py` model/provider configuration persistence
- `runtime/adaptive_routing/epistemic_kernel.py` registry loading
- `runtime/orchestrator/knowledge_router.py` local savings report
- `runtime/webapp.py` shared runtime object in process memory

## Forensic notes

- `runtime/main.py` is not a thin coordinator yet; it contains prompt construction, routing, execution, logging, status, planning, orchestration, and local bootstrap logic.
- `runtime/tools/memory.py` mixes runtime state, evidence, reasoning, browser tracking, and Obsidian note generation.
- `runtime/providers/config.py` mixes configuration loading, provider fallback policy, model selection persistence, and provider instantiation.
- `runtime/orchestrator/knowledge_router.py` overlaps with `runtime/adaptive_routing/epistemic_kernel.py` on local RHCSA routing.
- `runtime/orchestrator/gemini_gemma.py` is still a delegated-plan path and still imports RHCSA context plus worker memory.
- `runtime/tools/build_rhcsa_library.py` still references `memory/rhcsa_context.py` as an integration point, which is not present as a runtime module in this tree.
```

## `docs/forensic-runtime-audit/MEMORY_CONTAMINATION_MAP.md`

- size: 4838 bytes
- sha256: `031a1aafa36d238505565328bf394ac9d07235558972bbf8b6c876707b640d94`
- category: memory

```markdown
# Memory Contamination Map

Status: forensic mapping only. No runtime changes made.

## CRITICAL risk zones

### 1. `runtime/tools/memory.py`

Responsibilities mixed in one class:

- runtime state persistence (`state/agent_state.json`)
- append-only history (`memory/history.jsonl`)
- evidence journaling (`memory/evidence_memory.jsonl`)
- reasoning traces (`memory/reasoning_trace.jsonl`)
- browser event logging (`logs/browser/*.jsonl`)
- Obsidian vault projection (`obsidian_vault/*`)
- session bootstrapping (`session_start` note)
- mutable state replay via `AgentMemory`

Why this is critical:

- evidence, reasoning, and operational history are persisted by the same adapter
- the same object both represents live runtime state and writes notebook-style projections
- `append_history()` writes to history JSONL and also to the vault note surface
- `append_evidence()` and `append_reasoning()` each have both JSONL storage and vault note side effects

### 2. `runtime/main.py`

Mixed authority in one module:

- prompt construction
- model request generation
- runtime state snapshot
- local route handling
- deterministic knowledge routing
- legacy knowledge routing
- orchestrated planning path
- execution loop
- session logging
- reasoning trace logging
- epistemic fallback / unknown handling

Why this is critical:

- `main.py` is currently the coordination hub and the policy hub
- it builds the model prompt from mutable runtime state
- it injects RHCSA context into both planning and reactive execution
- it records evidence from the epistemic kernel directly into memory

### 3. `runtime/adaptive_routing/epistemic_kernel.py`

Mixed but more bounded:

- provenance loading
- contradiction loading
- deterministic retrieval
- confidence scoring
- routing-depth selection
- manual review detection
- response formatting

Risk:

- retrieval and epistemic output formatting are coupled
- provenance/contradiction signals are merged into one output object

## HIGH risk zones

### `runtime/tools/memory_hats.py`

- active prompt overlay is persisted in `state/active_hat.json`
- overlay text is inserted into the runtime request payload
- this is a mutable prompt-shaping layer with durable state

### `runtime/orchestrator/knowledge_router.py`

- reads local RHCSA memory
- updates token savings report in `state/token_savings_report.json`
- still encodes local retrieval policy that overlaps with the epistemic kernel

### `runtime/providers/config.py`

- persists model selection to `state/model_config.json`
- persists provider chain to `state/providers.json`
- loads API env files into process environment
- performs cloud-provider fallback

### `runtime/orchestrator/gemini_gemma.py`

- mixes strategic planning, worker action generation, RHCSA context injection, and worker-memory replay
- still assumes a two-model split and a worker model path that is explicitly disabled in this build

## MEDIUM risk zones

### `runtime/webapp.py`

- shares one `AgentRuntime` instance across requests
- exposes model switching and prompt execution in one process
- thread lock reduces race risk but does not separate authority

### `runtime/router/local_router.py`

- conservative and narrow, but still executes commands directly
- performs folder creation and shell execution before model involvement

### `runtime/tools/executor.py`

- one class handles tool registry, approval, execution, result recording, and memory writes

### `runtime/tools/epistemic_registry.py`

- builds provenance and contradiction registries from every knowledge artifact
- safe in purpose, but foundational to all later routing decisions

## Contamination patterns

1. Operational logs become pseudo-evidence
   - `executor._record_execution()` writes the same action payload to command logs, history, evidence, and browser logs where applicable.

2. Reasoning becomes persistent memory
   - `main.log_reasoning_trace()` writes to `memory/reasoning_trace.jsonl`.
   - `emit_epistemic_unknown()` also writes reasoning to disk.

3. Notebook projection and runtime state are intertwined
   - `MemoryStore.append_vault_note()` writes note surfaces from live execution payloads.

4. Provider selection becomes durable state
   - `ProviderManager.switch_model()` persists model choice into `state/model_config.json`.

5. RHCSA retrieval and local routing overlap
   - `AOIAEpistemicKernel` and `KnowledgeRouter` both decide whether local evidence should answer before cloud reasoning.

## Risk summary

- **CRITICAL**: `runtime/tools/memory.py`, `runtime/main.py`
- **HIGH**: `runtime/providers/config.py`, `runtime/orchestrator/knowledge_router.py`, `runtime/orchestrator/gemini_gemma.py`, `runtime/tools/memory_hats.py`
- **MEDIUM**: `runtime/webapp.py`, `runtime/router/local_router.py`, `runtime/tools/executor.py`, `runtime/tools/epistemic_registry.py`
```

## `docs/forensic-runtime-audit/RUNTIME_BOUNDARY_VIOLATIONS.md`

- size: 7048 bytes
- sha256: `abccce71a6e2de4dfa0ca65592df0111e173900ed2ae70f4fed4742d7afc09f5`
- category: docs

```markdown
# Runtime Boundary Violations

Status: forensic mapping only. No runtime changes made.

## 1. `runtime/main.py`

Severity: **CRITICAL**

Violations:

- too many responsibilities in one coordinator
- builds prompts and also owns runtime policy
- performs local routing, deterministic knowledge routing, legacy knowledge routing, and orchestrator dispatch
- owns unknown-response policy and logging policy
- mixes runtime state assembly with model-facing prompt construction

Relevant lines:

- imports and runtime assembly: [`runtime/main.py:24-36`](../../runtime/main.py#L24-L36)
- runtime state / prompt payload: [`runtime/main.py:167-227`](../../runtime/main.py#L167-L227)
- route selection and model loop: [`runtime/main.py:306-420`](../../runtime/main.py#L306-L420)
- knowledge routing bridge: [`runtime/main.py:698-760`](../../runtime/main.py#L698-L760)
- reasoning logging: [`runtime/main.py:915-918`](../../runtime/main.py#L915-L918)

## 2. `runtime/tools/memory.py`

Severity: **CRITICAL**

Violations:

- state, logs, evidence, reasoning, and Obsidian projection share one persistence layer
- runtime state and notebook projection are not separated
- append-only assumptions are not enforced by type boundary
- live mutable state is written back to disk on many different code paths

Relevant lines:

- path creation: [`runtime/tools/memory.py:50-121`](../../runtime/tools/memory.py#L50-L121)
- state file + log file setup: [`runtime/tools/memory.py:124-145`](../../runtime/tools/memory.py#L124-L145)
- evidence/reasoning/history methods: [`runtime/tools/memory.py:153-181`](../../runtime/tools/memory.py#L153-L181)
- command/result/state mutation: [`runtime/tools/memory.py:197-230`](../../runtime/tools/memory.py#L197-L230)
- vault note projection: [`runtime/tools/memory.py:232-260`](../../runtime/tools/memory.py#L232-L260)

## 3. `runtime/tools/executor.py`

Severity: **HIGH**

Violations:

- execution registry, approval UI, execution dispatch, and memory recording are coupled
- result recording writes to command logs and memory in the same method
- browser actions trigger browser-specific logs inside the same recorder

Relevant lines:

- tool registry: [`runtime/tools/executor.py:92-116`](../../runtime/tools/executor.py#L92-L116)
- approval gate: [`runtime/tools/executor.py:69-90`](../../runtime/tools/executor.py#L69-L90)
- execution recording: [`runtime/tools/executor.py:175-191`](../../runtime/tools/executor.py#L175-L191)

## 4. `runtime/providers/config.py`

Severity: **HIGH**

Violations:

- loads API env files into process environment
- persists model selection and provider chain state
- constructs provider instances
- makes fallback policy decisions

Relevant lines:

- env loading and config setup: [`runtime/providers/config.py:50-84`](../../runtime/providers/config.py#L50-L84)
- fallback generation: [`runtime/providers/config.py:89-111`](../../runtime/providers/config.py#L89-L111)
- model switching persistence: [`runtime/providers/config.py:113-121`](../../runtime/providers/config.py#L113-L121)
- provider availability and fallback chain: [`runtime/providers/config.py:126-149`](../../runtime/providers/config.py#L126-L149)

## 5. `runtime/adaptive_routing/epistemic_kernel.py`

Severity: **HIGH**

Violations:

- provenance, contradiction, routing depth, confidence, and response generation are coupled
- local retrieval and output formatting are handled in one class
- manual review is emitted from the same evaluator

Relevant lines:

- registry loading and artifact indexing: [`runtime/adaptive_routing/epistemic_kernel.py:84-102`](../../runtime/adaptive_routing/epistemic_kernel.py#L84-L102)
- evaluate path: [`runtime/adaptive_routing/epistemic_kernel.py:104-153`](../../runtime/adaptive_routing/epistemic_kernel.py#L104-L153)
- evidence merge/confidence/contradiction: [`runtime/adaptive_routing/epistemic_kernel.py:191-260`](../../runtime/adaptive_routing/epistemic_kernel.py#L191-L260)

## 6. `runtime/orchestrator/knowledge_router.py`

Severity: **HIGH**

Violations:

- overlaps conceptually with `AOIAEpistemicKernel`
- encodes local routing, thresholding, and savings accounting in one unit
- is a second authority for local RHCSA routing

Relevant lines:

- routing decision path: [`runtime/orchestrator/knowledge_router.py:62-81`](../../runtime/orchestrator/knowledge_router.py#L62-L81)
- report accounting: [`runtime/orchestrator/knowledge_router.py:83-106`](../../runtime/orchestrator/knowledge_router.py#L83-L106)

## 7. `runtime/orchestrator/gemini_gemma.py`

Severity: **HIGH**

Violations:

- strategic planning, worker action generation, RHCSA context injection, and memory replay are coupled
- worker path is currently disabled yet still present as transitional architecture

Relevant lines:

- planner and worker responsibilities: [`runtime/orchestrator/gemini_gemma.py:17-73`](../../runtime/orchestrator/gemini_gemma.py#L17-L73)
- prompt construction with RHCSA context and worker memory: [`runtime/orchestrator/gemini_gemma.py:122-180`](../../runtime/orchestrator/gemini_gemma.py#L122-L180)

## 8. `runtime/webapp.py`

Severity: **MEDIUM**

Violations:

- thin but still shares a single runtime object across requests
- model switching and prompt execution are exposed via the same service process

Relevant lines:

- shared runtime adapter: [`runtime/webapp.py:28-63`](../../runtime/webapp.py#L28-L63)
- HTTP API surface: [`runtime/webapp.py:74-144`](../../runtime/webapp.py#L74-L144)

## 9. `runtime/tools/build_rhcsa_library.py`

Severity: **MEDIUM**

Violations:

- build/generation tool still references `memory/rhcsa_context.py` as a runtime integration point
- this points to a missing/generated boundary rather than a canonical in-repo module

Relevant lines:

- integration point list: [`runtime/tools/build_rhcsa_library.py:1087-1099`](../../runtime/tools/build_rhcsa_library.py#L1087-L1099)

## 10. Missing runtime module boundary

Severity: **CRITICAL**

Observed issue:

- `runtime/main.py` imports `memory.rhcsa_context` and `memory.gemma_worker_memory`
- the repository tree contains only `memory/README.md`
- no in-repo Python package for `memory.*` is present

Why this matters:

- the runtime currently depends on a generated or out-of-tree module boundary
- this is a hard architectural ambiguity before any refactor

Relevant lines:

- imports: [`runtime/main.py:25-34`](../../runtime/main.py#L25-L34)
- generator hint: [`runtime/tools/build_rhcsa_library.py:1087-1099`](../../runtime/tools/build_rhcsa_library.py#L1087-L1099)

## Future L0-L5 violations

Likely violations against the planned ontology:

- `L0` ephemeral state is mixed with durable state in `MemoryStore`
- `L1` operational logs are mixed with evidence and notebook projections
- `L2` reasoning traces are persisted alongside execution records
- `L3` provenance is embedded in retrieval runtime rather than isolated
- `L4` evidence is written through the same recorder as operational history
- `L5` contradiction handling is loaded into runtime routing rather than read-only verification
```

## `docs/linux-engineering/README.md`

- size: 2471 bytes
- sha256: `e59df0800ce2090ae89ac41d3e41d069b918d73f1a167b2b060bbdf29b88b326`
- category: docs

```markdown
# Linux Engineering Knowledge Layer

The Linux Engineering knowledge layer is the local RHCSA/RHCE/Linux command corpus used by AIOA Core for deterministic, local-first technical retrieval.

## Why It Exists

AIOA Core already has a deterministic RHCSA retrieval path in `runtime/knowledge/`, `runtime/tools/rhcsa_search.py`, and `runtime/knowledge/rhcsa_engine.py`. This layer keeps Linux administration knowledge available without relying on a cloud model for every operational question.

The layer supports:

- RHCSA/RHCE study and command lookup
- local-first Linux administration answers
- deterministic retrieval over known source artifacts
- future command indexing toward a 10,000+ utility archive
- provenance-aware source handling

## Current Source Layout

The repository already had an RHCSA knowledge tree, so the integration reuses it instead of creating a duplicate `knowledge/linux-engineering/` tree.

Canonical source:

- `runtime/knowledge/source/linux_master_library_v1.pdf`

Legacy source retained:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`

Manifest:

- `runtime/knowledge/manifests/library_manifest.yaml`

Extracted text:

- `runtime/knowledge/extracted/linux_master_library_v1.txt`
- `runtime/knowledge/extracted/linux_master_library_v1.md`

Index template:

- `runtime/knowledge/index/command_index_template.csv`

## Deterministic Local-First Retrieval

Future retrieval should use deterministic preprocessing:

1. extract text from the canonical PDF
2. parse commands and examples into structured records
3. deduplicate against existing `rhcsa_commands.json`
4. preserve source page and source hash metadata
5. write versioned indexes
6. validate schema and category consistency
7. only then update runtime retrieval surfaces

No retrieval update should silently overwrite existing indexes.

## Future 10,000+ Command Updates

Future expansion should be append-only and versioned:

- add each new source as a versioned artifact
- record source hash in the manifest
- extract into `runtime/knowledge/extracted/`
- generate candidate rows into a review index
- deduplicate by command, subcommand, alias, package family, and ecosystem
- preserve deprecated commands and aliases as explicit metadata
- rebuild deterministic indexes only after validation

Do not mix evidence memory with reasoning memory. Extracted source text and command records belong to the knowledge/provenance layer; runtime reasoning traces remain separate.
```

## `docs/refactor/CANONICAL_AUTHORITY_GRAPH.md`

- size: 16925 bytes
- sha256: `c06d8781369d07dc6660dc5edfaf1425281e063f8eef6d20d6f061e95db0e3d1`
- category: docs

```markdown
# Canonical Authority Graph

Status: Phase 1C canonical authority freeze
Mode: forensic architecture only
Scope: AOIA-Core authority semantics before containment implementation

## Purpose

AOIA-Core must distinguish runtime continuity from epistemic authority.

This document freezes what is allowed to become authority, what must never become authority, and how authority may propagate through the system. It does not authorize implementation, refactor, runtime modification, adapter extraction, provider changes, routing changes, retrieval guards, or governance code.

## Canonical Authority Hierarchy

Highest authority is not "latest runtime output". Authority is constrained by source lineage, immutable evidence, and unresolved contradiction pressure.

Canonical order:

1. L3 provenance records
2. L5 contradiction registry
3. L4 immutable evidence
4. RHCSA deterministic knowledge artifacts
5. operator approvals for execution permission only
6. L2 reasoning traces for audit only
7. L1 operational logs for replay only
8. L0 runtime state for continuity only
9. vault projections for human readability only

Interpretation:
- L3 provenance defines source identity and constrains whether evidence can be trusted structurally.
- L5 contradictions constrain confidence and must remain visible.
- L4 evidence supports claims only when linked to provenance and contradiction checks.
- RHCSA deterministic knowledge can seed retrieval because it is source material under provenance policy.
- Operator approvals authorize actions; they do not create factual truth.
- L2, L1, L0, and vault projections are not factual authority.

## Objects That Are Authority

L3 provenance registry:
- `runtime/provenance_registry.json`
- Authority class: source lineage and artifact identity.
- Authority limit: does not itself prove the factual content of a claim; it identifies source origin, metadata, references, and fingerprints.

L5 contradiction registry:
- `runtime/contradiction_registry.json`
- Authority class: unresolved conflict and epistemic pressure.
- Authority limit: does not decide truth automatically; it constrains confidence and review requirements.

L4 immutable evidence:
- Future strict evidence objects only.
- Authority class: factual support artifact.
- Authority limit: valid only when fingerprinted, immutable, and linked to provenance.
- Current `memory/evidence_memory.jsonl` is not canonical L4 because it contains mixed payloads.

RHCSA deterministic knowledge:
- `runtime/knowledge/**`
- `runtime/knowledge/examples/*.json`
- `runtime/knowledge/command_graph.json`
- Authority class: deterministic local knowledge source material.
- Authority limit: must be interpreted through provenance, contradiction checks, retrieval policy, and confidence boundaries.

Operator approvals:
- Authority class: permission authority for execution.
- Authority limit: approval means "this action may run"; it does not mean the action result is true evidence, provenance, or contradiction resolution.

## Objects That Are Never Authority

The following must never become provenance, immutable evidence, retrieval source material, or contradiction resolution authority:

- L0 runtime state.
- `AgentMemory`.
- `state/agent_state.json`.
- `recent_outputs`.
- `previous_commands`.
- `current_task`.
- current working directory.
- browser state.
- open tabs.
- current browser URL.
- screenshots.
- session continuity.
- L1 operational logs.
- command logs.
- session logs.
- browser logs.
- error logs.
- command outputs.
- tool outputs.
- approval prompts or approval rejections.
- L2 reasoning traces.
- planner reasoning.
- planner summaries.
- model/provider responses.
- cloud planner output.
- local planner output.
- generated summaries.
- temporary summaries.
- Obsidian vault notes.
- vault daily notes.
- vault session notes.
- vault evidence projection notes.
- vault reasoning projection notes.

These objects may be useful for continuity, audit, debugging, or human review. They are not authority.

## Authority Propagation Rules

| Flow | Status | Rule |
| --- | --- | --- |
| L3 provenance -> L4 evidence | allowed | Evidence may reference provenance; provenance constrains evidence identity. |
| L4 evidence -> retrieval | allowed | Only valid immutable, fingerprinted, provenance-linked evidence may feed retrieval. |
| L5 contradiction -> retrieval confidence | allowed | Contradictions constrain confidence and review; they do not auto-resolve truth. |
| RHCSA deterministic knowledge -> provenance | allowed | Source artifacts may be registered as provenance through deterministic build policy. |
| RHCSA deterministic knowledge -> retrieval | allowed | Retrieval may read deterministic knowledge under provenance and contradiction policy. |
| Operator approval -> execution | allowed | Approval authorizes action execution only. |
| Operator approval -> evidence | forbidden | Approval is not factual evidence. |
| L0 runtime state -> L4 evidence | forbidden | Continuity state is not evidence. |
| L0 runtime state -> provenance | forbidden | Runtime state cannot define source lineage. |
| L0 runtime state -> retrieval source | forbidden | Runtime state is not source material. |
| L1 logs -> L4 evidence | forbidden | Operational logs are procedural records. |
| L1 logs -> provenance | forbidden | Logs are not source identity. |
| L1 logs -> retrieval source | forbidden | Replay traces are not retrieval authority. |
| L2 reasoning -> L4 evidence | forbidden | Reasoning is generated inference, not evidence. |
| L2 reasoning -> provenance | forbidden | Reasoning cannot create source lineage. |
| L2 reasoning -> retrieval source | forbidden | Retrieval over reasoning traces creates recursive authority. |
| Runtime output -> evidence | forbidden | Tool/model outputs need external provenance before evidence capture. |
| Planner summary -> provenance | forbidden | Generated summaries are derivatives, not source identity. |
| Cloud planner output -> evidence | forbidden by default | External provenance is required before evidence capture. |
| Vault projection -> retrieval source | forbidden | Vault is derivative projection only. |
| Vault projection -> evidence | forbidden | Projection is not immutable evidence. |
| Screenshot -> evidence | forbidden by default | Screenshot requires explicit capture policy, fingerprint, source link, and evidence type. |
| Command output -> evidence | forbidden by default | Command output is L1 unless recaptured through a source/evidence policy. |

## Safe Authority Flow

Canonical safe flow:

```text
external or deterministic source
  -> source ingestion / knowledge artifact
  -> L3 provenance record
  -> L5 contradiction check
  -> L4 immutable evidence object
  -> retrieval guard
  -> answer construction with confidence constraints
```

Properties required:
- Source identity is explicit.
- Source fingerprint is present.
- Contradictions remain visible.
- Evidence is immutable.
- Retrieval reads only allowed authority layers.
- Generated answer does not rewrite provenance, evidence, or contradiction state.

## Forbidden Authority Flow

Canonical forbidden flow:

```text
runtime output
  -> history log
  -> evidence_memory.jsonl
  -> retrieval
  -> authority claim
```

This flow is forbidden because:
- Runtime output is not source lineage.
- History is L1, not L4.
- Current evidence memory is mixed and not canonical.
- Retrieval must not read runtime logs or reasoning traces.
- Authority claims must be constrained by provenance and contradiction checks.

Expanded forbidden flow:

```text
planner output
  -> action JSON
  -> tool result
  -> recent_outputs
  -> next prompt
  -> generated summary
  -> vault note
  -> future retrieval or knowledge ingestion
```

This flow is forbidden as authority propagation. It may exist as continuity and projection, but it must not become evidence, provenance, or retrieval source material.

## Runtime-Only Components

Runtime-only components maintain execution continuity. They may influence the next action as context, but they must not define factual authority.

Runtime-only:
- `runtime/tools/memory.py` current L0 state responsibilities.
- `AgentMemory`.
- `MemoryStore.save()`.
- `MemoryStore.record_command()`.
- `MemoryStore.record_result()`.
- `MemoryStore.set_current_task()`.
- `MemoryStore.update_cwd()`.
- browser state fields.
- `AgentRuntime.build_model_request()` runtime state block.
- `AgentRuntime.snapshot_status()`.

Rule:
- Runtime-only components may support planning context and status reporting.
- Runtime-only components must not write L3, L4, or L5 authority.

## Operational-Only Components

Operational-only components record what happened. They support replay, audit, and debugging.

Operational-only:
- `ExecutionEngine._record_execution()` command log behavior.
- `MemoryStore.append_history()`.
- `MemoryStore.append_browser_event()`.
- `AgentRuntime.log_session_event()`.
- `AgentRuntime.log_error()`.
- `logs/commands/**`.
- `logs/browser/**`.
- `logs/sessions/**`.
- `logs/errors/**`.
- `memory/history.jsonl`.

Rule:
- Operational-only components may write L1.
- Operational-only components must not write L4.
- Operational-only components must not feed retrieval as source material.

## Epistemic-Only Components

Epistemic-only components evaluate source-backed knowledge, evidence candidates, uncertainty, and contradictions.

Epistemic-only:
- `runtime/adaptive_routing/epistemic_kernel.py`.
- `runtime/tools/rhcsa_search.py`.
- `runtime/knowledge/rhcsa_engine.py`.
- deterministic knowledge artifacts under `runtime/knowledge/**`.
- reasoning trace emitters when used only for audit.

Rule:
- Epistemic components may read L3/L4/L5 where policy allows.
- Epistemic components may emit L2 reasoning traces.
- Epistemic components must not promote L2 to L4.
- Epistemic components must not auto-resolve L5.

## Projection-Only Components

Projection-only components create human-readable surfaces. They are not canonical memory.

Projection-only:
- `obsidian_vault/**`.
- `MemoryStore.build_obsidian_vault_paths()` behavior.
- `MemoryStore.append_vault_note()`.
- `MemoryStore._append_channel_note()`.
- `MemoryStore._vault_block()`.
- vault daily notes.
- vault session notes.
- vault evidence notes.
- vault reasoning notes.

Rule:
- Projection-only components may display or summarize.
- Projection-only components must not feed provenance.
- Projection-only components must not feed evidence.
- Projection-only components must not feed retrieval indexes.
- Projection-only components must be treated as derivative and non-authoritative.

Vault semantics:
- The Obsidian vault is projection-only.
- It is not operational memory authority.
- It is not an evidence layer.
- It is not a provenance source.
- It is a forbidden retrieval source unless a future human-reviewed source ingestion policy explicitly imports an external source artifact, not the vault note itself.

## Governance-Only Components

Governance-only components define rules, constraints, and permissions. They do not create factual evidence by themselves.

Governance-only:
- future authority registry.
- future retrieval guard.
- future evidence promotion policy.
- future human-review promotion policy.
- operator approvals as execution permissions.
- memory doctrine documents.

Rule:
- Governance can permit, block, or classify flows.
- Governance cannot turn generated output into source truth.
- Governance cannot erase contradictions silently.
- Governance cannot make L0/L1/L2 authority by declaration.

## Canonical Role Of Current Components

`runtime/tools/memory.py`:
- Current role: mixed runtime persistence, logs, reasoning traces, evidence-like writes, and vault projection.
- Canonical future role: not authority itself.
- Authority status now: unsafe mixed memory surface.

`runtime/tools/executor.py`:
- Current role: action dispatcher and execution recorder.
- Canonical role: operational execution and L1 replay only.
- Authority status now: unsafe because `_record_execution()` writes action results into evidence-like memory.

`runtime/adaptive_routing/epistemic_kernel.py`:
- Current role: deterministic local epistemic kernel.
- Canonical role: epistemic evaluator reading provenance, contradictions, and deterministic knowledge.
- Authority status now: comparatively healthy, but its evidence output lands in weak storage.

`runtime/orchestrator/knowledge_router.py`:
- Current role: legacy local RHCSA router and token-savings reporter.
- Canonical role: transitional retrieval path, operationally useful but not final authority boundary.
- Authority status now: must remain secondary to canonical kernel/governance model.

`runtime/provenance_registry.json`:
- Current role: source identity registry.
- Canonical role: L3 provenance authority.
- Authority status now: valid seed, but not append-only event history.

`runtime/contradiction_registry.json`:
- Current role: conflict and duplicate-source registry.
- Canonical role: L5 contradiction authority.
- Authority status now: valid seed, with no auto-resolution observed.

`runtime/knowledge/**`:
- Current role: deterministic RHCSA/Linux knowledge source corpus.
- Canonical role: source material eligible for provenance, contradiction checks, evidence creation, and retrieval.
- Authority status now: allowed source surface under guard policy.

## Must Never Enter L4

The following must never enter canonical L4 evidence:
- `action_result` payloads.
- tool outputs.
- command outputs.
- shell stdout/stderr.
- command success/failure status.
- browser events.
- browser state.
- screenshots without evidence capture policy.
- runtime state.
- recent outputs.
- previous commands.
- planner output.
- cloud provider output.
- local model output.
- reasoning traces.
- vault notes.
- generated summaries.
- session logs.
- approval events.
- rejection events.
- temporary reports.

Allowed exception:
- An external artifact observed through a tool may become L4 only through a future explicit evidence capture policy requiring source identity, fingerprint, capture time, evidence type, and provenance linkage.

## Must Never Enter Provenance

The following must never enter L3 provenance:
- runtime state.
- operational logs.
- command outputs.
- reasoning traces.
- planner summaries.
- provider responses.
- vault notes.
- generated reports.
- screenshots without source identity.
- temporary summaries.
- operator approval events.
- token savings reports.

Allowed source identity must come from:
- deterministic source ingestion.
- knowledge artifact registration.
- external source artifact capture with identity and fingerprint.
- human-reviewed source registration under policy.

## Must Never Enter Retrieval Indexes

The following must never be indexed as source material:
- `state/**`.
- `logs/**`.
- `memory/history.jsonl`.
- `memory/reasoning_trace.jsonl`.
- mixed `memory/evidence_memory.jsonl`.
- `obsidian_vault/**`.
- `screenshots/**` unless evidence policy creates a separate L4 object.
- session continuity records.
- planner traces.
- model responses.
- vault projections.
- temporary generated summaries.
- command output logs.

Retrieval may read:
- deterministic knowledge artifacts.
- L3 provenance.
- canonical L4 evidence once implemented.
- L5 contradictions as confidence and review constraints.

## Future Enforcement Implications

This document implies future enforcement work, but does not implement it.

Future enforcement must:
- block `action_result` from evidence writes.
- prevent retrieval from indexing L0/L1/L2/projection paths.
- require provenance and fingerprint for L4.
- distinguish operator approval from factual authority.
- label vault output as projection-only.
- keep contradiction records append-only and visible.
- prevent generated summaries from becoming provenance.
- prevent cloud planner output from becoming evidence without external provenance.
- treat legacy mixed `memory/evidence_memory.jsonl` as quarantined until reviewed.

## Runtime Safety Judgment

Runtime is not currently authority-safe.

Runtime is safe for Phase 2A pseudo-evidence containment only if Phase 2A is narrowly scoped to containment of the known bad flow:

```text
ExecutionEngine._record_execution()
  -> MemoryStore.append_evidence("action_result", payload)
```

Phase 2A must not broaden into memory splitting, provider changes, routing changes, governance implementation, or retrieval redesign until this authority graph is accepted.

## Frozen Decision

The canonical AOIA authority graph is:

```text
source artifact
  -> L3 provenance
  -> L5 contradiction check
  -> L4 immutable evidence
  -> retrieval guard
  -> answer construction
```

Everything else is continuity, operation, reasoning audit, projection, or governance policy. None of those are factual authority unless explicitly and validly promoted through future provenance/evidence policy.
```

## `docs/refactor/MEMORY_AUTHORITY_BOUNDARIES.md`

- size: 7543 bytes
- sha256: `a8de7355a8c692de59a2d1dba4a412ada6f111a2dc78fd14497d750dd2d9ef30`
- category: memory

```markdown
# Memory Authority Boundaries

Status: Phase 1B forensic analysis
Mode: documentation only
Scope: authority mapping for current `memory.py` split planning

## Boundary Principle

`memory.py` currently stores records, but it does not enforce authority. Phase 1A requires each memory layer to have an explicit authority class. Phase 1B identifies where current code crosses those authority classes.

## Current Authority Classes

| Current Surface | Intended Layer | Current Authority Problem |
| --- | --- | --- |
| `AgentMemory` | L0 | Prompt-visible continuity state can be mistaken for source context. |
| `state/agent_state.json` | L0 | Runtime state persists under repo root. |
| `memory/history.jsonl` | L1 | Operational history is projected into vault and duplicated into evidence. |
| `logs/commands/*.json` | L1 | Command replay records may contain stdout/stderr that look factual. |
| `logs/browser/*.jsonl` | L1 | Browser operations are not evidence captures by themselves. |
| `memory/reasoning_trace.jsonl` | L2 | Reasoning is persisted near evidence-like memory. |
| `runtime/provenance_registry.json` | L3 | Registry exists, but evolution is not append-only yet. |
| `memory/evidence_memory.jsonl` | pseudo-L4 | Generic evidence append accepts non-evidence payloads. |
| `runtime/contradiction_registry.json` | L5 | Registry exists, but runtime event semantics are not formalized yet. |
| `obsidian_vault/**` | projection | Human-readable derivatives can be mistaken for canonical memory. |

## Authority Graph

```text
runtime/knowledge/**
  -> provenance registry (L3)
  -> contradiction registry (L5)
  -> AOIAEpistemicKernel evidence candidates
  -> local answer construction

ExecutionEngine action result
  -> command log (L1)
  -> runtime state (L0)
  -> history log (L1)
  -> evidence_memory.jsonl (pseudo-L4 violation)
  -> vault projection

Reasoning event
  -> reasoning_trace.jsonl (L2)
  -> vault reasoning projection

Vault projection
  -> operator-readable notes
  -> must not feed provenance/evidence/retrieval
```

## Boundary Findings

Finding 1: L0 boundary is weak.
- `AgentMemory` is correctly shaped for ephemeral continuity.
- It is persisted and injected into prompts.
- It must later be explicitly marked as non-authoritative context.

Finding 2: L1 boundary is broken at executor evidence write.
- `action_result` is operational history.
- It is currently written to `memory/evidence_memory.jsonl`.
- This is the strongest violation of Phase 1A doctrine.

Finding 3: L2 boundary is documented but not enforced.
- Reasoning traces are separate from evidence writes.
- No retrieval path currently reads reasoning traces.
- Physical location and vault projection still allow future accidental misuse.

Finding 4: L3 boundary exists outside `memory.py`.
- Provenance registry has content hashes and artifact metadata.
- It is read by the AOIA kernel.
- It is not append-only event history yet.

Finding 5: L4 boundary does not exist as an implementation contract.
- `append_evidence()` is a generic write method.
- No required fingerprint, source reference, content-addressed key, or schema exists.
- Kernel evidence summaries and executor action results share the same storage path.

Finding 6: L5 boundary is healthier than L4 but incomplete.
- Contradictions are reported and not auto-resolved.
- Runtime contradiction status events do not yet exist.

Finding 7: Vault boundary is absent.
- Vault output is currently generated as a side effect.
- It is a projection, but code does not label it as derivative or non-authoritative.

## Future Adapter Classification

Ephemeral runtime adapter:
- Owns L0 state only.
- Should preserve active session continuity.
- Must not expose state as evidence, provenance, or retrieval source.
- Candidate current members: `AgentMemory`, `save()`, `set_current_task()`, `update_cwd()`, `record_command()`, `record_result()`.

Operational log adapter:
- Owns L1 event logs only.
- Should record chronological runtime behavior.
- Must not write evidence.
- Candidate current members: `append_history()`, `append_browser_event()`, command log path handling, session logs, error logs.

Reasoning trace quarantine:
- Owns L2 reasoning records only.
- Should store route choices, uncertainty, planner requests, kernel decisions, and unknown responses.
- Must not be indexed by retrieval.
- Candidate current members: `append_reasoning()`, `log_reasoning_trace()`.

Provenance registry:
- Owns L3 source identity and lineage.
- Should be append-only or versioned by epoch.
- Candidate current modules: `tools/epistemic_registry.py`, `runtime/provenance_registry.json`, kernel provenance enrichment.

Immutable evidence adapter:
- Owns L4 evidence objects only.
- Must require fingerprint, source identity, capture time, evidence type, and immutable write semantics.
- Candidate current member to replace: `append_evidence()`.

Contradiction registry:
- Owns L5 conflict records and status events.
- Must preserve unresolved conflicts and append status changes.
- Candidate current modules: `tools/epistemic_registry.py`, `runtime/contradiction_registry.json`, kernel contradiction hits.

Vault projection layer:
- Owns derivative human-readable notes.
- Must not be authority.
- Candidate current members: `build_obsidian_vault_paths()`, `append_vault_note()`, `_append_channel_note()`, `_vault_block()`.

## Future Split Safety Rules

Rule 1:
- Remove executor-to-evidence writes before changing evidence storage semantics.

Rule 2:
- Keep a compatibility facade while extracting adapters because `AgentRuntime`, `ExecutionEngine`, commands, and tests depend on `MemoryStore`.

Rule 3:
- Do not make retrieval aware of vault, history, reasoning, or runtime state.

Rule 4:
- Do not let evidence migration accept old `action_result` records as canonical L4 evidence.

Rule 5:
- Treat existing `memory/evidence_memory.jsonl` as legacy mixed memory until reviewed.

Rule 6:
- Treat vault notes as derivative projection and never as source lineage.

Rule 7:
- Keep contradiction detection report-only until an append-only status event model exists.

## Highest-Risk Refactor Boundaries

`ExecutionEngine._record_execution()`:
- Highest risk because it is called for every action and currently fans out to L0/L1/pseudo-L4.

`MemoryStore.append_evidence()`:
- High risk because current callers provide payloads with different epistemic quality.

`MemoryStore.record_result()`:
- High risk because prompt continuity depends on it.

`AgentRuntime.build_model_request()`:
- High risk because it determines how L0 state enters generated planning.

`build_runtime_paths()`:
- Medium risk because moving paths affects browser profiles, screenshots, logs, and state.

`build_obsidian_vault_paths()`:
- Medium risk because tests and `/vault` expect vault availability.

`KnowledgeRouter` state report:
- Medium risk because it writes retrieval metrics into `state/`, outside memory ownership.

## Phase 2A Gate

Runtime is not safe for Phase 2A implementation until the team accepts:
- the exact first change to stop `action_result` evidence writes
- the compatibility strategy for `MemoryStore`
- the fate of legacy `memory/evidence_memory.jsonl`
- the physical quarantine rule for L2
- the retrieval guard allowlist
- the handling policy for untracked runtime `state/`

Recommended Phase 2A starting point:
- a narrow change that prevents new L1 operational action results from entering evidence-like storage while preserving L1 history, command logs, L0 continuity, and existing tests.
```

## `docs/refactor/MEMORY_CONTAMINATION_GRAPH.md`

- size: 8928 bytes
- sha256: `72c9e88ed17bf0cf6f2a1c2a2d89ff017cd74e60b14069f5c8edb014c391e864`
- category: memory

```markdown
# Memory Contamination Graph

Status: Phase 1B forensic analysis
Mode: documentation only
Scope: contamination and leakage around `runtime/tools/memory.py`

## Core Contamination Graph

```text
tool action result
  -> command log JSON                  [L1]
  -> AgentMemory.recent_outputs         [L0]
  -> memory/history.jsonl               [L1]
  -> memory/evidence_memory.jsonl       [pseudo-L4 violation]
  -> obsidian_vault/Daily               [projection]
  -> obsidian_vault/Sessions            [projection]
  -> model prompt recent_outputs        [recursive generated-output channel]
```

This is the highest-risk contamination graph in current AOIA-Core.

## L0 Leak Map

Current L0 sources:
- `AgentMemory.cwd`
- `AgentMemory.current_task`
- `AgentMemory.previous_commands`
- `AgentMemory.recent_outputs`
- `AgentMemory.open_tabs`
- `AgentMemory.current_browser_page`
- `AgentMemory.screenshots`
- `AgentMemory.browser_active`

Current leak paths:
- L0 is persisted to `state/agent_state.json`.
- L0 is read by `build_model_request()` and included in model prompt JSON.
- L0 is read by `snapshot_status()`.
- L0 is mixed into vault notes through `_vault_block()` because every block includes `cwd` and `task`.
- L0 browser state is mutated from tool result payloads.

Doctrine risk:
- L0 is allowed as continuity state, but it must not persist as authority.
- Current prompt injection makes L0 influential over planner behavior.
- Current vault projection can make L0 look like durable continuity memory.

## L1 Leak Map

Current L1 sources:
- `logs/commands/<timestamp>.json`
- `memory/history.jsonl`
- `logs/browser/browser_<session>.jsonl`
- `logs/sessions/session_<session>.jsonl`
- `logs/errors/error_<timestamp>.json`
- token savings report under `state/token_savings_report.json`

Current leak paths:
- `append_history()` writes L1 to `memory/history.jsonl` and then projects it into vault daily/session notes.
- `append_browser_event()` writes L1 browser logs and projects browser events into vault daily/session notes.
- `ExecutionEngine._record_execution()` writes the same payload to command logs, history, and evidence-like memory.

Doctrine risk:
- L1 must never become evidence.
- Current executor flow makes L1 action results become pseudo-L4.

## L2 Leak Map

Current L2 sources:
- `planner_request`
- `aoia_kernel_decision`
- `knowledge_route_disabled`
- `unknown_response`
- other calls through `AgentRuntime.log_reasoning_trace()`

Current leak paths:
- `append_reasoning()` writes to `memory/reasoning_trace.jsonl`.
- `append_reasoning()` writes to `obsidian_vault/Reasoning/<session>.md`.
- Direct calls to `append_reasoning()` can bypass helper-level safeguard checks.
- Human-readable reasoning projection may later be copied into knowledge or prompt contexts.

Doctrine risk:
- L2 must never become evidence.
- Retrieval does not currently read L2, but no retrieval guard prevents future reads.
- Vault projection creates a soft human-mediated route for L2 to re-enter authority channels.

## Pseudo-Evidence Formation

Pseudo-evidence forms at:

```text
ExecutionEngine._record_execution
  -> append_evidence("action_result", payload)
```

Payload includes:
- action requested
- result object
- command output when present
- filesystem path when present
- browser URL or text when present
- cancellation/rejection result when present
- current cwd

Why this violates Phase 1A:
- It has no external provenance requirement.
- It has no content fingerprint.
- It has no CAS identity.
- It has no evidence type schema.
- It may contain generated model action proposals.
- It may contain operational command output.
- It may contain approval rejection events.
- It is structurally indistinguishable from stronger evidence-like records in the same JSONL file.

## Runtime State Becomes Authority

Authority-like runtime state paths:
- Prompt construction includes `previous_commands` and `recent_outputs`.
- Prompt construction includes active browser page and open tabs.
- Prompt construction includes current vault path.
- Snapshot/status exposes memory state as runtime status.

Risk:
- The planner may infer truth from recent outputs.
- Recent model-generated output can become future prompt context.
- Runtime status can be mistaken for epistemic source state.

This is not a direct retrieval violation today, but it is a recursive planning contamination path.

## Generated Output Recursive Re-Entry

Recursive flow:

```text
cloud/local planner output
  -> action JSON
  -> executor result
  -> record_result()
  -> AgentMemory.recent_outputs
  -> build_model_request()
  -> next planner prompt
```

Expanded recursive flow:

```text
cloud/local planner output
  -> action result
  -> append_history()
  -> append_evidence("action_result")
  -> append_vault_note()
  -> human-readable notes
  -> possible future operator copy/paste or knowledge ingestion
```

Doctrine risk:
- Generated outputs must not become provenance.
- Cloud planner output must not become evidence without external provenance.
- Current runtime does not enforce this distinction.

## Vault Projection Contamination

Vault projection contamination paths:
- `session_start` becomes daily note and session JSONL.
- Every history event becomes daily note and session JSONL.
- Browser events become daily note and session JSONL.
- Evidence events become evidence markdown notes.
- Reasoning events become reasoning markdown notes.

Risk:
- Projection notes mix L0 cwd/task with L1/L2/pseudo-L4 payload summaries.
- Summaries use only `message`, `summary`, or `error`, which can hide source identity and context.
- Vault files look durable and human-readable, which increases risk of later misuse as source authority.

## Retrieval Contamination Status

Current retrieval sources:
- `runtime/knowledge/**`
- `runtime/knowledge/examples/*.json`
- `runtime/knowledge/command_graph.json`
- `runtime/provenance_registry.json`
- `runtime/contradiction_registry.json`

Current non-sources:
- `memory/history.jsonl`
- `memory/evidence_memory.jsonl`
- `memory/reasoning_trace.jsonl`
- `obsidian_vault/**`
- `logs/**`
- `state/agent_state.json`

Current judgment:
- Retrieval is not currently contaminated by L0/L1/L2 reads.
- Retrieval is still vulnerable because mutable runtime output directories live under the repository root and no guard prevents future indexing.

## Contamination Hotspots

Hotspot 1: `ExecutionEngine._record_execution()`
- Converts every action result into history and evidence.
- Highest immediate doctrine violation.

Hotspot 2: `MemoryStore.append_evidence()`
- Generic append with no evidence contract.
- Accepts both real artifact summaries and operational payloads.

Hotspot 3: `MemoryStore.record_result()`
- Stores compact result summaries in L0.
- Feeds prompt continuity.

Hotspot 4: `AgentRuntime.build_model_request()`
- Converts L0 state into planner context.
- Enables recursive generated-output influence.

Hotspot 5: `MemoryStore.append_vault_note()`
- Projects mixed runtime events into durable human-readable notes.

Hotspot 6: `MemoryStore.append_reasoning()`
- Persists L2 and projects it to vault.
- Quarantine is not enforced physically.

Hotspot 7: `KnowledgeRouter.record_local_hit()` and `record_miss()`
- Writes routing metrics under `state/`.
- Creates mutable retrieval-adjacent state outside `memory.py`.

## Current Behaviors Violating Phase 1A Doctrine

Violates "L1 must never become evidence":
- `append_evidence("action_result", payload)` from executor.

Violates "cloud planner output must not become evidence without external provenance":
- Model-proposed action results can be written as evidence-like events.

Violates "runtime state must not persist as authority":
- L0 state persists in `state/agent_state.json` and is prompt-visible.
- The violation becomes active if prompt consumers treat it as source truth.

Violates "L2 must never become evidence":
- No direct code path currently promotes L2 to evidence.
- Risk remains because L2 and pseudo-L4 live under the same generic memory concept and vault projection.

Violates "retrieval must not read L0/L1/L2":
- No current direct violation found.
- Enforcement is absent.

Violates "contradiction records must not be auto-resolved":
- Current kernel reports contradictions without auto-resolution.
- Current registry builder writes unresolved policy.
- No active violation found.

## Containment Recommendations For Future Implementation

- First remove or block `action_result` evidence writes.
- Give `append_evidence()` a replacement interface requiring source identity and fingerprint.
- Move L2 reasoning traces away from any retrieval-scannable path.
- Mark vault projection as derivative-only and prevent retrieval indexing.
- Keep command/session/browser logs as L1 only.
- Keep runtime state L0 behind a continuity adapter.
- Add a retrieval guard with explicit allowlist: L3, L4, and L5 constraints only.
```

## `docs/refactor/MEMORY_DEPENDENCY_GRAPH.md`

- size: 7464 bytes
- sha256: `3a4bd28f3a72b2d07919d8eae9c4d7f4e1f2216590ac37d4021ebd3a50361ecc`
- category: memory

```markdown
# Memory Dependency Graph

Status: Phase 1B forensic analysis
Mode: documentation only
Scope: current dependency structure around `runtime/tools/memory.py`

## Direct Module Dependencies

`runtime/tools/memory.py` imports:
- `datetime`
- `json`
- `dataclasses.asdict`
- `dataclasses.dataclass`
- `dataclasses.field`
- `pathlib.Path`
- `typing.Any`

It does not import runtime modules. The dependency direction is mostly inward: other runtime components depend on `MemoryStore`.

## Direct Runtime Dependents

`runtime/main.py`:
- Imports `MemoryStore`.
- Constructs it in `AgentRuntime.__init__()`.
- Reads `memory_store.memory`.
- Reads `memory_store.vault_dir`.
- Reads `memory_store.paths`.
- Calls `append_evidence()`.
- Calls `append_reasoning()` through `log_reasoning_trace()` and direct calls.

`runtime/tools/executor.py`:
- Imports `MemoryStore`.
- Receives a `MemoryStore` instance at construction.
- Reads `memory_store.memory.cwd`.
- Reads `memory_store.paths.command_logs_dir`.
- Reads `memory_store.paths.state_dir`.
- Reads `memory_store.paths.screenshots_dir`.
- Calls `record_command()`.
- Calls `record_result()`.
- Calls `append_history()`.
- Calls `append_evidence()`.
- Calls `append_browser_event()`.

`runtime/commands/local_commands.py`:
- Reads `runtime.memory_store.vault_dir` for `/vault`.

Tests:
- `tests/test_main.py` constructs `MemoryStore` directly and asserts vault initialization.
- `tests/test_epistemic_safeguards.py` constructs `MemoryStore` directly and asserts evidence/reasoning vault directories.

## Indirect Runtime Dependents

`AgentRuntime.build_model_request()`:
- Depends on `AgentMemory` shape.
- Injects `session_id`, `cwd`, `current_task`, `previous_commands`, `recent_outputs`, browser state, screenshots, and vault path into model prompt context.

`AgentRuntime.snapshot_status()`:
- Depends on `AgentMemory` and `MemoryStore` paths.
- Exposes L0 state and vault path to status callers.

`ExecutionEngine.configure_browser_bridge()`:
- Depends on `memory_store.paths.state_dir / "browser_profile"`.
- Depends on `memory_store.paths.screenshots_dir`.

`ExecutionEngine._record_execution()`:
- Depends on `memory_store.paths.command_logs_dir`.
- Depends on `MemoryStore` write methods.

## Path Dependency Graph

```text
project_dir
  -> state/
     -> agent_state.json
     -> browser_profile/
     -> model_config.json
     -> providers.json
     -> token_savings_report.json
  -> memory/
     -> history.jsonl
     -> evidence_memory.jsonl
     -> reasoning_trace.jsonl
  -> screenshots/
  -> logs/
     -> browser/
     -> sessions/
     -> commands/
     -> errors/
  -> obsidian_vault/
     -> Daily/
     -> Sessions/
     -> Evidence/
     -> Reasoning/
     -> .obsidian/app.json
     -> 00_START_HERE.md
```

The graph shows that mutable runtime output is physically inside the repository root. This is a source-authority contamination risk even when those paths are untracked.

## Function Dependency Graph

```text
MemoryStore.__init__
  -> build_runtime_paths
  -> build_obsidian_vault_paths
  -> save
  -> append_vault_note("session_start")

append_history
  -> memory/history.jsonl
  -> append_vault_note

append_evidence
  -> memory/evidence_memory.jsonl
  -> _append_channel_note(obsidian_vault/Evidence)

append_reasoning
  -> memory/reasoning_trace.jsonl
  -> _append_channel_note(obsidian_vault/Reasoning)

append_browser_event
  -> logs/browser/browser_<session>.jsonl
  -> append_vault_note("browser_event")

record_command
  -> AgentMemory.previous_commands
  -> save

record_result
  -> AgentMemory.recent_outputs
  -> AgentMemory.current_browser_page
  -> AgentMemory.open_tabs
  -> AgentMemory.browser_active
  -> AgentMemory.screenshots
  -> save

append_vault_note
  -> obsidian_vault/Daily/<date>.md
  -> obsidian_vault/Sessions/<session>.jsonl

_append_channel_note
  -> obsidian_vault/<Evidence|Reasoning>/<session>.md
```

## Execution Dependency Graph

```text
AgentRuntime
  -> MemoryStore
  -> ExecutionEngine(memory_store)
  -> LocalRouter
  -> KnowledgeRouter
  -> AOIAEpistemicKernel

ExecutionEngine.execute(action)
  -> tool handler
  -> _record_execution(action, result)
     -> logs/commands/<timestamp>.json
     -> MemoryStore.record_result(result)
     -> MemoryStore.append_history("action_result", payload)
     -> MemoryStore.append_evidence("action_result", payload)
     -> MemoryStore.append_browser_event(payload) for browser actions
```

This is the most important dependency path because one runtime action fans out into L0, L1, pseudo-L4, and vault projection.

## Knowledge Retrieval Dependency Graph

```text
AgentRuntime.handle_knowledge_route(user_input)
  -> AOIAEpistemicKernel.evaluate(user_input)
     -> exact_command_lookup
     -> search_rhcsa
     -> grep_rhcsa
     -> search_by_tag
     -> runtime/provenance_registry.json
     -> runtime/contradiction_registry.json
     -> KernelDecision(reasoning, evidence)
  -> MemoryStore.append_reasoning("aoia_kernel_decision", reasoning)
  -> MemoryStore.append_evidence("aoia_kernel_evidence", artifact summary)
  -> optional KnowledgeRouter.route(user_input, active_hat)
     -> RHCSAKnowledgeEngine.retrieve_operational_memory(user_input)
     -> state/token_savings_report.json
```

Retrieval currently reads deterministic knowledge files, provenance registry, contradiction registry, and command graph. It does not read `memory/history.jsonl`, `memory/reasoning_trace.jsonl`, or `obsidian_vault/**`.

## Authority Dependency Graph

```text
runtime/knowledge/** source files
  -> tools.rhcsa_search indexes
  -> AOIAEpistemicKernel evidence candidates

runtime/provenance_registry.json
  -> AOIAEpistemicKernel._provenance_by_artifact
  -> AOIAEpistemicKernel._enrich_evidence

runtime/contradiction_registry.json
  -> AOIAEpistemicKernel._duplicate_commands
  -> AOIAEpistemicKernel._contradiction_hits

KernelDecision.evidence
  -> AgentRuntime.handle_knowledge_route
  -> MemoryStore.append_evidence("aoia_kernel_evidence", summary)
```

The authority graph is healthier than the execution graph, but the final write into `append_evidence()` loses strict L3/L4 structure because the destination is a generic JSONL append.

## Reverse Dependency Risks

Risk 1:
- Future retrieval may accidentally index `memory/` or `obsidian_vault/` because they are in the repository root.

Risk 2:
- Prompt construction reads L0 recent outputs and previous commands. Generated output can therefore influence future generated output through state continuity.

Risk 3:
- Tests assert vault initialization through `MemoryStore`, which increases refactor blast radius.

Risk 4:
- `ExecutionEngine` depends on `MemoryStore` for paths and memory writes, so splitting `memory.py` requires a compatibility facade or staged extraction.

## Refactor Dependency Constraints

Must preserve during future implementation:
- `MemoryStore` construction behavior until tests are updated.
- `memory_store.paths` shape until executor/browser/session code is migrated.
- `memory_store.memory` shape until prompt/status code is migrated.
- `/vault` output behavior until local command contract is changed.
- Command log write behavior until operational log adapter exists.

Should not preserve as doctrine:
- `append_evidence("action_result", payload)`.
- Vault projection as a default side effect of all history events.
- Evidence writes without fingerprints or provenance links.
- L0 runtime output as prompt-visible authority.
```

## `docs/refactor/MEMORY_SPLIT_PLAN.md`

- size: 15467 bytes
- sha256: `c1520671918b371afb475c27fb30a5024703af7a0c76c4934e91d6285103ba33`
- category: memory

```markdown
# Memory Split Plan

Status: Phase 1B forensic analysis
Mode: documentation only
Scope: `runtime/tools/memory.py` and direct dependency surface

## Purpose

This document maps the current `memory.py` contamination structure before any implementation work begins. It does not authorize a runtime refactor, module move, adapter extraction, provider change, routing change, or governance implementation.

Phase 1A froze the AOIA memory ontology:
- L0 Ephemeral Runtime State
- L1 Operational Logs
- L2 Reasoning Traces
- L3 Provenance Records
- L4 Immutable Evidence
- L5 Contradiction Registry

Phase 1B maps how the current runtime violates, approximates, or bypasses those layers.

## Current MemoryStore Responsibilities

`runtime/tools/memory.py` currently owns all of the following in one module:

- Runtime path creation: `build_runtime_paths()` creates `state/`, `memory/`, `screenshots/`, and `logs/**`.
- Vault path creation: `build_obsidian_vault_paths()` creates `obsidian_vault/**` and initial vault config.
- L0 state object: `AgentMemory` stores `cwd`, `current_task`, command history, recent outputs, browser state, and screenshots.
- L0 persistence: `MemoryStore.save()` serializes `AgentMemory` into `state/agent_state.json`.
- L1 history: `append_history()` appends JSONL records to `memory/history.jsonl`.
- L1 browser log: `append_browser_event()` appends JSONL records to `logs/browser/browser_<session>.jsonl`.
- L2 reasoning trace: `append_reasoning()` appends JSONL records to `memory/reasoning_trace.jsonl`.
- Evidence-like store: `append_evidence()` appends JSONL records to `memory/evidence_memory.jsonl`.
- Vault projection: `append_vault_note()` and `_append_channel_note()` convert live runtime events into human-readable Obsidian notes.

The module is therefore not a memory layer. It is a transitional compound adapter for state, logs, reasoning, evidence-like events, browser events, and human-facing projection.

## Current Write Paths

`MemoryStore.__init__()`:
- Creates mutable runtime directories and vault directories.
- Writes `state/agent_state.json` through `save()`.
- Writes a `session_start` vault note through `append_vault_note()`.
- Risk: runtime startup mutates source-root state before any user action.

`MemoryStore.save()`:
- Writes L0 state to `state/agent_state.json`.
- Risk: volatile runtime state persists inside the repository working tree.

`MemoryStore.append_history()`:
- Writes a JSONL event to `memory/history.jsonl`.
- Also writes a vault daily note and session JSONL record.
- Risk: L1 operational events are immediately projected into human-readable continuity notes.

`MemoryStore.append_evidence()`:
- Writes to `memory/evidence_memory.jsonl`.
- Also writes to `obsidian_vault/Evidence/<session>.md`.
- Risk: accepts arbitrary `kind` and `payload` with no evidence schema, fingerprint, provenance link, or promotion policy.

`MemoryStore.append_reasoning()`:
- Writes to `memory/reasoning_trace.jsonl`.
- Also writes to `obsidian_vault/Reasoning/<session>.md`.
- Risk: generated reasoning is projected as durable human-readable notes.

`MemoryStore.append_browser_event()`:
- Writes to `logs/browser/browser_<session>.jsonl`.
- Also writes a vault note through `append_vault_note("browser_event", payload)`.
- Risk: browser operations become daily continuity notes without evidence capture rules.

`MemoryStore.record_command()`:
- Mutates `AgentMemory.previous_commands`.
- Writes L0 state through `save()`.
- Risk: command history is prompt-visible runtime state and can bias planning.

`MemoryStore.record_result()`:
- Mutates `AgentMemory.recent_outputs`, browser page, open tabs, browser flag, and screenshots.
- Writes L0 state through `save()`.
- Risk: compacted tool output becomes prompt-visible runtime state.

`MemoryStore.append_vault_note()`:
- Writes `obsidian_vault/Daily/<date>.md`.
- Writes `obsidian_vault/Sessions/<session>.jsonl`.
- Risk: vault becomes a mixed projection of L0/L1/browser/session events.

`MemoryStore._append_channel_note()`:
- Writes evidence and reasoning projection notes.
- Risk: a projection channel can look like a canonical memory channel.

## Current Read Paths

Direct runtime reads:
- `AgentRuntime.build_model_request()` reads `memory_store.memory` and injects L0 runtime state into planner prompts.
- `AgentRuntime.snapshot_status()` reads `memory_store.memory`, `vault_dir`, and path metadata.
- Slash command `/vault` reads `runtime.memory_store.vault_dir`.
- `ExecutionEngine.__init__()` reads `memory_store.memory.cwd` and memory paths.

Internal read-before-write paths:
- `append_vault_note()` reads existing daily note text before appending.
- `_append_channel_note()` reads existing channel note text before appending.

No current code path was found that retrieves answer source material from:
- `memory/history.jsonl`
- `memory/reasoning_trace.jsonl`
- `memory/evidence_memory.jsonl`
- `obsidian_vault/**`

This is good for Phase 1A retrieval quarantine, but it is not enforced by a guard.

## Persistence Paths By Layer

L0 current paths:
- `state/agent_state.json`
- in-memory `AgentMemory`

L1 current paths:
- `memory/history.jsonl`
- `logs/browser/browser_<session>.jsonl`
- `logs/sessions/session_<session>.jsonl`
- `logs/commands/<timestamp>.json`
- `logs/errors/error_<timestamp>.json`

L2 current paths:
- `memory/reasoning_trace.jsonl`
- `obsidian_vault/Reasoning/<session>.md`

Pseudo-L4 current paths:
- `memory/evidence_memory.jsonl`
- `obsidian_vault/Evidence/<session>.md`

Projection current paths:
- `obsidian_vault/Daily/<date>.md`
- `obsidian_vault/Sessions/<session>.jsonl`
- `obsidian_vault/Evidence/<session>.md`
- `obsidian_vault/Reasoning/<session>.md`
- `obsidian_vault/.obsidian/app.json`
- `obsidian_vault/00_START_HERE.md`

L3 current paths outside `memory.py`:
- `runtime/provenance_registry.json`
- generated by `runtime/tools/epistemic_registry.py`

L5 current paths outside `memory.py`:
- `runtime/contradiction_registry.json`
- generated by `runtime/tools/epistemic_registry.py`

## Current State Mutation Paths

`set_current_task()`:
- Mutates `AgentMemory.current_task`.
- Writes `state/agent_state.json`.

`update_cwd()`:
- Mutates `AgentMemory.cwd`.
- Writes `state/agent_state.json`.

`record_command()`:
- Appends and truncates `previous_commands` to the last 20.
- Writes `state/agent_state.json`.

`record_result()`:
- Appends and truncates `recent_outputs` to the last 20.
- Updates browser fields from result payloads.
- Appends and truncates screenshots to the last 20.
- Writes `state/agent_state.json`.

These are valid L0 operations only if they remain continuity state. They become doctrine violations when used as source authority, evidence, provenance, or retrieval input.

## Evidence-Related Flows

Executor action result flow:
- `ExecutionEngine._record_execution()` writes a command log JSON file.
- It calls `record_result(result)`.
- It calls `append_history("action_result", payload)`.
- It calls `append_evidence("action_result", payload)`.

This is the clearest Phase 1A violation. Every tool result, rejected approval, shell output, browser event, and filesystem action can be recorded as evidence-like memory without external provenance.

AOIA kernel evidence flow:
- `AOIAEpistemicKernel.evaluate()` retrieves knowledge artifacts and enriches them with provenance and contradiction references.
- `AgentRuntime.handle_knowledge_route()` logs kernel reasoning.
- If evidence exists, it calls `append_evidence("aoia_kernel_evidence", ...)` with query, route, confidence, manual-review flag, and artifact paths.

This flow is closer to the doctrine because it starts from L3-backed knowledge artifacts. It is still incomplete because the `append_evidence()` destination does not enforce L4 immutability, fingerprints, source linkage, schema, or content addressing.

## Reasoning-Trace Flows

Planner flow:
- `create_plan()` writes `planner_request` through `log_reasoning_trace()`.
- `log_reasoning_trace()` delegates to `append_reasoning()`.

Knowledge flow:
- `handle_knowledge_route()` writes `aoia_kernel_decision` reasoning.
- `emit_epistemic_unknown()` writes `unknown_response` reasoning twice in the current flow: once through `log_reasoning_trace()` and once directly through `append_reasoning()`.

Safeguard flow:
- `log_reasoning_trace()` checks `reasoning_trace_enabled`.
- Direct calls to `append_reasoning()` bypass that helper-level gate.

No current retrieval path was found reading L2 as source material. However, L2 is persisted in repo-root runtime outputs and projected into the vault, so quarantine is conceptual rather than enforced.

## Obsidian/Vault Projection Flows

Vault startup:
- `build_obsidian_vault_paths()` creates the full vault layout.
- It writes `.obsidian/app.json` and `00_START_HERE.md` if missing.

Daily/session projection:
- `append_history()` and `append_browser_event()` call `append_vault_note()`.
- `append_vault_note()` writes both daily markdown and session JSONL.
- The vault block contains current `cwd`, current `task`, and a summary extracted from `message`, `summary`, or `error`.

Evidence/reasoning projection:
- `append_evidence()` writes to `obsidian_vault/Evidence/<session>.md`.
- `append_reasoning()` writes to `obsidian_vault/Reasoning/<session>.md`.

Risk:
- Vault notes are derivative projections, but current naming and placement make them look like memory authority.
- Daily notes mix startup events, action results, browser events, and task/cwd context.
- Projection can recursively influence operators, future prompts, or manual copy/paste into knowledge material.

## Runtime Coupling Points

`AgentRuntime.__init__()`:
- Constructs `MemoryStore`.
- Constructs `ExecutionEngine` with the same store.
- Constructs `KnowledgeRouter` and `AOIAEpistemicKernel` separately.
- Creates session log path from `memory_store.paths`.

`AgentRuntime.build_model_request()`:
- Injects L0 runtime state into the model prompt.
- Includes `previous_commands`, `recent_outputs`, browser state, screenshots, active memory hat, `rhcsa_context`, vault path, and tool names.

`ExecutionEngine.__init__()`:
- Uses memory paths for browser profile and screenshots.
- Uses memory command log directory.
- Reads initial cwd from `memory_store.memory`.

`KnowledgeRouter.__init__()`:
- Writes token savings report under `state/`.
- This is not owned by `memory.py`, but it uses the same mutable runtime state area.

## Current Doctrine Violations

Violation 1: L1 becomes pseudo-L4.
- `executor._record_execution()` records every `action_result` as both history and evidence.

Violation 2: L4 destination has no evidence contract.
- `append_evidence()` accepts arbitrary payloads with no fingerprint, source identity, CAS key, or provenance requirement.

Violation 3: L0 state persists in repo-root.
- `state/agent_state.json` is written by `save()` and mutated after routine runtime events.

Violation 4: L0 enters prompt authority.
- `build_model_request()` injects recent outputs and previous commands into planner context.
- This is acceptable as continuity only, but dangerous if planner output treats it as source truth.

Violation 5: L2 quarantine is not physical.
- `append_reasoning()` stores reasoning under `memory/` and vault projections.
- Retrieval does not currently read it, but no guard prevents future indexing.

Violation 6: Vault projection is coupled to canonical-looking channels.
- Evidence and reasoning projection notes are generated automatically.

Violation 7: Generated outputs can recursively re-enter memory.
- Model/planner responses become tool results.
- Tool results become L0 recent outputs, L1 history, pseudo-L4 evidence, and vault notes.
- Future model requests read L0 recent outputs.

## Eventual Split Targets

Ephemeral runtime adapter:
- `AgentMemory`
- `MemoryStore.save()`
- `set_current_task()`
- `update_cwd()`
- `record_command()`
- `record_result()`
- browser continuity fields in `record_result()`

Operational log adapter:
- `build_runtime_paths()` log path responsibilities
- `append_history()`
- `append_browser_event()`
- command log write in `ExecutionEngine._record_execution()`
- session/error log writes in `AgentRuntime`

Reasoning trace quarantine:
- `append_reasoning()`
- `AgentRuntime.log_reasoning_trace()`
- planner and unknown-response trace flows
- `obsidian_vault/Reasoning` projection as derivative output only

Provenance registry:
- `runtime/tools/epistemic_registry.py`
- `runtime/provenance_registry.json`
- provenance enrichment in `AOIAEpistemicKernel._enrich_evidence()`

Immutable evidence adapter:
- Future replacement for `append_evidence()`
- Kernel evidence capture policy
- CAS evidence objects and fingerprints
- Explicit rejection of `action_result` as evidence

Contradiction registry:
- `runtime/tools/epistemic_registry.py`
- `runtime/contradiction_registry.json`
- contradiction lookup in `AOIAEpistemicKernel`
- future append-only contradiction status events

Vault projection layer:
- `build_obsidian_vault_paths()`
- `append_vault_note()`
- `_append_channel_note()`
- `_vault_block()`
- all Obsidian file writes as derivative projection only

## Recommended Future Split Order

1. Stop L1-to-L4 promotion in executor.
2. Quarantine L2 physically and prevent retrieval indexing.
3. Extract L0 runtime state behind an ephemeral adapter.
4. Extract L1 operational logs behind an operational log adapter.
5. Replace `append_evidence()` with a strict evidence capture interface and CAS store.
6. Move vault generation behind a projection layer that cannot be read as authority.
7. Formalize append-only provenance evolution.
8. Formalize append-only contradiction events.
9. Add retrieval guard checks for allowed source layers.

## Highest-Risk Future Refactor Operations

Highest risk:
- Changing `executor._record_execution()` because it affects every tool action and replay trace.
- Changing `record_result()` because it affects prompt continuity and browser state.
- Changing `append_evidence()` because current callers do not supply full L4 metadata.
- Changing vault projection because tests currently expect vault initialization.
- Changing knowledge routing because there are two local routing paths: AOIA kernel and legacy `KnowledgeRouter`.

Medium risk:
- Moving path creation out of `memory.py`.
- Separating browser logs from runtime state.
- Moving token savings report out of `state/`.

Lower risk:
- Adding documentation-only layer labels.
- Adding non-runtime validation scripts later.
- Adding read-only reports that inspect current paths.

## Implementation Blockers

- No CAS evidence schema exists yet.
- No append-only provenance event schema exists yet.
- No contradiction event schema exists yet.
- No retrieval guard exists.
- No promotion policy exists for human-reviewed artifacts.
- Current tests expect `MemoryStore` to initialize vault paths.
- Current runtime passes `MemoryStore` directly into `ExecutionEngine`.
- Current `append_evidence()` has callers with incompatible evidence quality.

## Runtime Phase 2A Readiness

Runtime is not safe for Phase 2A implementation until the first future refactor explicitly removes or blocks the `action_result` to evidence flow.

Recommended readiness judgment:
- Phase 1B documentation: ready after these reports are accepted.
- Phase 2A implementation: not ready until cleanup policy for untracked `state/`, existing runtime output locations, and evidence schema is accepted.
```

## `docs/reports/FINAL_URL_HANDOFF_PATCH.md`

- size: 3824 bytes
- sha256: `a5443d228b12e5e7115272fcb6bdd34cff0a86459fe3ee47d950ff7aac660913`
- category: docs

```markdown
# Final URL Handoff Patch

Status: implemented minimal deterministic external URL handoff
Mode: final micro-patch
Date: 2026-05-23

## Scope

This patch keeps external URLs and repository inspection requests out of AOIA deterministic RHCSA/local knowledge routing.

It does not implement autonomous browsing, crawling, scraping, AI repository analysis, embeddings, retrieval redesign, orchestration redesign, provider changes, governance changes, or memory architecture changes.

## Exact Files Changed

- `runtime/main.py`
- `tests/test_routing_boundary.py`
- `docs/reports/PHASE_2B_ROUTING_BOUNDARY.md`
- `docs/reports/FINAL_URL_HANDOFF_PATCH.md`

## Old Routing Behavior

Before the boundary:

```text
external URL / GitHub request
  -> AOIA deterministic epistemic kernel
  -> local_knowledge
  -> RHCSA retrieval
  -> unrelated local Linux knowledge response
```

This allowed GitHub and external repository requests to contaminate the RHCSA path.

## New Routing Behavior

After the boundary:

```text
external URL / GitHub request
  -> deterministic external review classifier
  -> external_repository_review or external_link_review
  -> controlled browser-inspection handoff response
  -> stop before RHCSA/local knowledge retrieval
```

Current controlled responses:

```text
External repository inspection path detected. Browser inspection path available.
```

```text
External URL detected. Browser inspection path available.
```

## RHCSA Contamination Status

Fixed for this scope:

- `https://` and `http://` inputs are detected before RHCSA retrieval.
- `github.com` and `gitlab.com` inputs are detected before RHCSA retrieval.
- Repository inspection intents such as `can you inspect github repository` are detected before RHCSA retrieval.
- Matching external requests do not call `AOIAEpistemicKernel.evaluate()`.

Preserved:

- Normal non-external requests remain on the existing runtime path.
- Linux/RHCSA questions can still use deterministic local knowledge.

## Browser Handoff Status

Browser handoff now opens the detected URL through the existing browser bridge and reads the visible page text.

The patch still does not crawl a repository, perform autonomous browsing, analyze repository contents deeply, or create provenance records from external content.

## Validation

Commands:

```text
PYTHONPATH=runtime python3 -m unittest tests.test_routing_boundary
PYTHONPATH=runtime python3 -m unittest tests.test_executor_containment
```

Results:

```text
tests.test_routing_boundary: Ran 6 tests OK
tests.test_executor_containment: Ran 1 test OK
```

Expected coverage:

- `jakim jestes modelem` remains a normal runtime request.
- `https://github.com/luciferprosun/AOIA-Core` does not trigger RHCSA retrieval.
- `can you check github repository` does not trigger RHCSA retrieval.
- `can you inspect github repository` does not trigger RHCSA retrieval.
- `https://github.com/luciferprosun/AOIA-Core` is opened via browser handoff instead of local knowledge.
- `how to create folder in linux` still reaches the RHCSA/local knowledge path.

## Unresolved Browser Limitations

- No safe browser execution policy is frozen for deeper repository inspection.
- No external-source provenance capture exists for browser content.
- No contradiction handling exists for external repository claims.
- No retrieval guard exists for external browser output.
- Browser text must not become evidence without a future provenance and authority boundary.

## Safest Next Future Routing Step

Freeze a small external inspection doctrine before adding any browser execution:

- allowed external inputs
- provenance capture requirements
- browser output quarantine rules
- retrieval exclusion rules
- operator approval requirements

Do not implement autonomous browsing or repository analysis without a dedicated phase.
```

## `docs/reports/PHASE_2B_ROUTING_BOUNDARY.md`

- size: 5298 bytes
- sha256: `997ec5a2367fb4f92495e59783017347a77c0a33a986bee09aadaa670b6ab323`
- category: docs

```markdown
# Phase 2B Routing Boundary

Status: implemented minimal deterministic routing repair
Mode: surgical implementation
Date: 2026-05-23

## Objective

Prevent external URLs and GitHub/GitLab repository review requests from activating AOIA deterministic RHCSA/local Linux knowledge retrieval.

This phase only repairs the routing boundary. It does not implement external repository inspection, crawling, browser automation, embeddings, AI classification, retrieval redesign, orchestration redesign, provider changes, governance, or memory architecture changes.

## Files Changed

Runtime:

- `runtime/main.py`

Tests:

- `tests/test_routing_boundary.py`

Report:

- `docs/reports/PHASE_2B_ROUTING_BOUNDARY.md`

## Routing Flow Before

Before Phase 2B:

```text
user request
  -> local route
  -> AOIAEpistemicKernel.evaluate()
  -> RHCSA deterministic retrieval
  -> local_knowledge response if evidence found
  -> model/browser/planner fallback
```

Failure:

```text
https://github.com/luciferprosun/AOIA-Core
  -> AOIAEpistemicKernel.evaluate()
  -> RHCSA/local Linux retrieval
  -> unrelated local knowledge activation
```

This allowed external repository requests to contaminate local RHCSA routing.

## Routing Flow After

After Phase 2B:

```text
user request
  -> local route
  -> deterministic external review classification
     -> external_repository_review placeholder
     -> external_link_review placeholder
  -> AOIAEpistemicKernel.evaluate()
  -> RHCSA deterministic retrieval
```

Boundary placement:

- The new external classification runs before `handle_knowledge_route()`.
- If the input is an external URL, GitHub/GitLab URL, or repository-review intent, the request stops before RHCSA retrieval.
- The route is logged as an external review placeholder.

## Deterministic Detection Added

URL detection:

- `http://`
- `https://`

Repository host detection:

- `github.com`
- `gitlab.com`

Repository intent detection examples:

- `check github project`
- `analyze repository`
- `describe repo`
- `check this github`
- `can you check github repository`
- Polish equivalents including `sprawdź`, `przeanalizuj`, `opisz`, `repozytorium`, `projekt`

## Placeholder Routes

Implemented placeholder route names:

- `external_repository_review`
- `external_link_review`

Current controlled responses:

```text
External repository inspection path detected. Browser inspection path available.
```

```text
External URL detected. Browser inspection path available.
```

These placeholders intentionally do not inspect, crawl, browse, or analyze external repositories yet.

## RHCSA Contamination Status

Fixed:

- GitHub URLs no longer trigger `AOIAEpistemicKernel.evaluate()`.
- GitLab URLs no longer trigger `AOIAEpistemicKernel.evaluate()`.
- Explicit GitHub/repository review intents no longer trigger RHCSA retrieval.

Preserved:

- Plain Linux/RHCSA operational requests can still reach the deterministic kernel.
- Normal non-external model requests are not classified as external review.

## Validation Tests

Command:

```text
PYTHONPATH=runtime python3 -m unittest tests.test_routing_boundary
```

Result:

```text
......
----------------------------------------------------------------------
Ran 6 tests

OK
```

Covered cases:

- `jakim jestes modelem` is not classified as external review.
- `jakim jestes modelem` can still use the normal runtime response path.
- `https://github.com/luciferprosun/AOIA-Core` returns external repository placeholder and does not call RHCSA kernel.
- `can you check github repository` returns external repository placeholder and does not call RHCSA kernel.
- `can you inspect github repository` returns external repository placeholder and does not call RHCSA kernel.
- `how to create folder in linux` still calls RHCSA/local knowledge path.

Regression check:

```text
PYTHONPATH=runtime python3 -m unittest tests.test_executor_containment
```

Result:

```text
.
----------------------------------------------------------------------
Ran 1 test

OK
```

## Unresolved Routing Risks

- External repository review is only a placeholder route.
- No safe browser/repository inspection workflow exists yet.
- No external source provenance capture policy exists yet.
- URLs are blocked from RHCSA retrieval, but full external-link handling is not implemented.
- `build_plan_request()` still injects RHCSA context for model planning in non-external flows.
- Legacy `KnowledgeRouter` remains behind the AOIA kernel for Linux/RHCSA requests.

## Next Safest Routing Step

The next safe routing step should be documentation or a new narrow phase for external review capability.

Recommended next phase:

- Define external repository review doctrine before implementation.

Do not implement next without a new phase:

- crawling
- autonomous scraping
- browser-based repository inspection
- AI repository classifiers
- embeddings
- external execution
- retrieval over external content

## Final Judgment

Deterministic URL boundary exists.

External placeholder route exists.

GitHub URLs no longer trigger RHCSA deterministic retrieval.

Runtime continuity is preserved because the change only inserts a deterministic pre-knowledge-route boundary and does not alter memory, providers, routing internals, retrieval implementation, or executor behavior.
```

## `reports/linux-engineering/rhcsa_existing_state_audit.md`

- size: 5591 bytes
- sha256: `293bdc9c9c06332d43422dac7d724681efd32586e0cd83d7762f9166674163ff`
- category: reports

```markdown
# RHCSA/Linux Existing State Audit

Audit date: 2026-05-24

Scope: AIOA Core RHCSA/Linux knowledge layer, deterministic retrieval assets, evidence/provenance boundaries, and the new canonical PDF input `Library of Linux - Unified RHCSA/RHCE Linux Command Knowledge Library`.

## Audit Result

An RHCSA/Linux knowledge structure already exists. The safe action is to reuse and extend the existing `runtime/knowledge/` tree instead of creating a parallel `knowledge/linux-engineering/` archive.

## Existing RHCSA/Linux-Related Folders

- `runtime/knowledge/`
- `runtime/knowledge/source/`
- `runtime/knowledge/canonical/`
- `runtime/knowledge/raw/`
- `runtime/knowledge/parsed/`
- `runtime/knowledge/index/`
- `runtime/knowledge/context/`
- `runtime/knowledge/injection/`
- `runtime/knowledge/tools/`
- `runtime/knowledge/schema/`
- `runtime/knowledge/validator/`
- `runtime/knowledge/bash/`
- `runtime/knowledge/filesystem/`
- `runtime/knowledge/networking/`
- `runtime/knowledge/permissions/`
- `runtime/knowledge/selinux/`
- `runtime/knowledge/storage/`
- `runtime/knowledge/systemd/`
- `runtime/knowledge/users/`
- `runtime/knowledge/lvm/`
- `runtime/knowledge/podman/`
- `runtime/knowledge/troubleshooting/`
- `runtime/memory/`
- `runtime/obsidian_vault/Evidence/`
- `retrieval/`
- `provenance/`
- `memory/`

## Existing RHCSA/Linux-Related Files

Core runtime retrieval:

- `runtime/knowledge/rhcsa_engine.py`
- `runtime/tools/rhcsa_search.py`
- `runtime/memory/rhcsa_context.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/adaptive_routing/epistemic_kernel.py`

Existing source/canonical/index artifacts:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`
- `runtime/knowledge/canonical/rhcsa_commands.json`
- `runtime/knowledge/raw/rhcsa_raw.txt`
- `runtime/knowledge/parsed/rhcsa_sections.json`
- `runtime/knowledge/index/command_index.json`
- `runtime/knowledge/command_graph.json`
- `runtime/knowledge/context/context_pack.json`
- `runtime/knowledge/injection/injected_context.json`
- `runtime/knowledge/schema/command.schema.json`

Existing docs/reports:

- `runtime/knowledge/README.md`
- `docs/RHCSA_ENGINE_REVIEW.md`
- `docs/LINUX_ENGINEERING_LIBRARY.md`
- `docs/LINUX_ENGINEERING_LIBRARY_REPORT.md`
- `docs/KNOWLEDGE_PACK_RULES.md`
- `docs/KNOWLEDGE_PACK_SPEC.md`
- `AOIA_RUNTIME_MAP.md`
- `AOIA_DEPENDENCY_GRAPH.md`
- `ROUTING_AUTHORITY_ANALYSIS.md`

Existing validation/tests:

- `runtime/knowledge/validator/validation_rules.py`
- `runtime/knowledge/validator/validator.py`
- `runtime/knowledge/validator/validation_report.md`
- `tests/test_rhcsa_retrieval.py`
- `tests/test_knowledge_validator.py`

## Existing Manifests

No dedicated Linux Engineering library manifest was found under `runtime/knowledge/` before this integration. Existing manifest-like files were located in unrelated MHLM/MHSR provider export areas and should not be reused for the RHCSA/Linux runtime knowledge layer.

Created manifest:

- `runtime/knowledge/manifests/library_manifest.yaml`

## Existing Indexes

Existing:

- `runtime/knowledge/index/command_index.json`

Created as a future ingestion template only:

- `runtime/knowledge/index/command_index_template.csv`

No command rows were invented.

## Existing Provenance

Existing provenance foundations:

- `PROVENANCE_FOUNDATION.md`
- `runtime/provenance_registry.json`
- `provenance/README.md`
- `docs/architecture/AOIA_MEMORY_MODEL.md`
- `docs/architecture/FORBIDDEN_MEMORY_FLOWS.md`
- `docs/architecture/MEMORY_LAYER_ACCESS_MATRIX.md`

Created Linux Engineering source policy:

- `runtime/knowledge/provenance/PROVENANCE_POLICY.md`

## Existing PDF/Master Status

Existing older RHCSA source:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`
- SHA256: `b8092eeabbfd80489d9e5ce8b49ba4d822aa83cc360da0a8f3c76276ac21d6b7`

New canonical master source imported safely:

- `runtime/knowledge/source/linux_master_library_v1.pdf`
- SHA256: `7eab9450dd15cc5e1607c29d9fe3b19c4cf9854bb702f113534b6ec34a34dc03`
- Pages: 453
- Encrypted: no

The new PDF is not a byte-for-byte duplicate of the older RHCSA source PDF.

## Possible Duplicates And Overlaps

Potential semantic overlap exists between:

- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf`
- `runtime/knowledge/source/linux_master_library_v1.pdf`
- `runtime/knowledge/canonical/rhcsa_commands.json`
- `runtime/knowledge/index/command_index.json`
- `docs/LINUX_ENGINEERING_LIBRARY.md`

These are not treated as duplicate folder structures. They represent different generations or formats of Linux/RHCSA knowledge. The new PDF is stored as a versioned canonical source, while existing deterministic runtime artifacts are preserved for backward compatibility.

## Safe Merge Path

1. Reuse `runtime/knowledge/` as the canonical runtime knowledge root.
2. Keep the older source PDF and JSON index artifacts intact.
3. Store the new PDF as `runtime/knowledge/source/linux_master_library_v1.pdf`.
4. Store extracted text under `runtime/knowledge/extracted/`.
5. Track source lineage through `runtime/knowledge/manifests/library_manifest.yaml`.
6. Keep generated command indexes append-only and deduplicated.
7. Do not update `runtime/knowledge/canonical/rhcsa_commands.json` until a deterministic parser/index loader phase is run.
8. Keep evidence memory separate from reasoning memory.

## Decision

No duplicate `knowledge/linux-engineering/` tree was created. The existing `runtime/knowledge/` tree was extended because it already contains the live RHCSA source, canonical JSON, parsed sections, command index, retrieval engine, and validation tools.
```

