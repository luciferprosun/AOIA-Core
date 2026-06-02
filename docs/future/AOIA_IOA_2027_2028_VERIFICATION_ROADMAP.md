# AOIA / IOA 2027–2028 Verification Roadmap

Subtitle: NiFe Synapses, symbolic knowledge tags, open-source linked references, and future model verification layer

## 1. Status

This is a future planning document only.

- Not implemented in runtime.
- Not part of the current Bash Safety execution path.
- No server integration yet.
- No model-ranking implementation yet.
- No public LLM conversation links are treated as validated knowledge.
- No execution authority.
- No shell execution, Android tooling, trading bot integration, or provider routing changes.
- No Cloudflare changes yet.

## 2. Current AOIA-Core Priority

The current AOIA-Core priority remains Bash Safety and pre-execution command inspection. The active runtime hardening path is focused on inert command representation, classification, approval boundaries, audit event shape, and the no-execution boundary.

Current work centers on:

- Bash Safety
- pre-execution command inspection
- `CommandProposal`
- classification
- `ApprovalDecision`
- `ApprovalAuditEvent`
- no-execution boundary
- tests -> commit -> push workflow

NiFe Synapses and model verification are future-facing concepts. They must not disrupt the current runtime hardening work or weaken the no-execution boundary.

## 3. Why This Roadmap Exists

AOIA is not only intended as a Codex-like assistant. Long-term, AOIA may become an epistemic-control framework and a "school for models," where models are wrapped with validated knowledge hats, source discipline, contradiction handling, provenance, and safety boundaries.

This roadmap records a future concept that is planned for careful design and audit. It is not implemented yet. Every part of this direction requires source review, benchmark design, contradiction checks, and independent validation before it can influence runtime behavior.

This document intentionally avoids claims of guaranteed hallucination removal, validated model ranking, or safe autonomous agency.

## 4. NiFe Synapses Project

NiFe Synapses Project is a future AOIA knowledge-addressing concept.

The core idea is that knowledge hats should stay lightweight. Hats should store symbolic tags or pheromone keys, not full knowledge blobs. Full knowledge may later live in local knowledge bases, repositories, or server-side knowledge oceans. Tags would act as compact references to validated knowledge entries.

Pheromone tags are symbolic string identifiers, not biological measurements and not floating-point numbers.

The first symbolic knowledge spark is:

- `mV:-70`

Future tags may expand as strings:

- `mV:-70.000001`
- `mV:-70.000002`

These tags are strings. They are not floats. No float math is planned for them. This avoids precision and collision bugs that could appear if symbolic knowledge IDs were treated as numerical values. There is no runtime integration yet.

## 5. Hat-Based Knowledge Structure

Planned knowledge hats may include:

- Hat 001: Bash Safety / Pre-Execution Command Inspection
- Hat 002: RHCSA / Linux Administration
- Python Engineering
- Git / Repository Engineering
- Android Engineering
- Security Review
- Evidence Memory
- Reasoning Memory
- Provenance / Contradiction Handling

Hat 001 can begin as conceptual tagging now because it is based on validated AOIA-Core GT-RUNTIME work. Other hats are planning shells unless validated sources, tests, and reviewed reports exist.

## 6. 2027 Plan — Knowledge Tagging and Hat Registry

2027 is the planning and buildout year for the conceptual knowledge-tagging and hat-registry layer.

Planned 2027 areas:

- conceptual tag registry
- hat manifest format
- tag status vocabulary
- source registry format
- validation workflow
- linking tags to commits and tests
- linking tags to `docs/api` reports
- keeping runtime separate from the future knowledge layer

Suggested 2027 deliverables:

- `docs/future/NIFE_SYNAPSES_PROJECT_PLAN.md`
- `docs/future/NIFE_TAG_STATUS_VOCABULARY.md`
- `docs/future/NIFE_HAT_001_BASH_TAG_MAP.md`
- `docs/future/NIFE_HAT_002_RHCSA_LINUX_ADMIN_TAG_MAP.md`
- `docs/future/NIFE_SOURCE_REGISTRY_CONCEPT.md`
- `docs/future/NIFE_VALIDATION_WORKFLOW.md`

These deliverables are docs and concepts first, not runtime code.

## 7. 2028 Plan — IOA / LLM Model Verification Layer

The future 2028 direction may become an IOA Model Verification Layer. 2028 is the IOA / LLM model-verification layer direction.

Its purpose would be to evaluate models by epistemic behavior, not only benchmark score.

Potential metrics:

- factual discipline
- source discipline
- uncertainty handling
- contradiction handling
- provenance compliance
- safety-boundary compliance
- code/test reliability
- hallucination resistance
- ability to separate fact, hypothesis, and model-generated suggestion

This is not a normal leaderboard. It is a trust and epistemic discipline layer.

Potential outputs:

- model trust profile
- domain-specific model reliability
- hat-specific model behavior score
- source-use quality
- contradiction response quality
- safety-boundary respect score

This is a future concept and requires rigorous design, benchmarks, source registries, and audits before implementation.

## 8. Public Linked References and Open-Source Knowledge

AOIA may later use public open-source references and public conversation links as low-cost knowledge references.
Public LLM conversation links are deferred until a proper source registry and validation workflow exist.

Important boundaries:

- Public LLM conversations may be stored as reference links later.
- They must not be treated as validated knowledge by default.
- Model output is not validated knowledge by default.
- They start as `reference_only`.
- They start as `model_generated_unverified`.
- They can be promoted only after review, tests, source validation, and contradiction checks.

Open source matters because it supports:

- transparency
- auditability
- low-cost knowledge sharing
- public review
- reproducible reasoning trails
- community validation
- reduced dependence on closed private memory systems

Open-source links are useful only if AOIA keeps strict source-status boundaries.

## 9. Knowledge Status Vocabulary Preview

Preview statuses:

- `planned`
- `reference_only`
- `model_generated_unverified`
- `reviewed`
- `validated_by_tests`
- `validated_by_commit`
- `contradicted`
- `deprecated`
- `promoted`

Promotion path:

```text
planned
-> reference_only
-> reviewed
-> validated_by_tests
-> validated_by_commit
-> promoted
```

Side paths:

- `contradicted`
- `deprecated`

## 10. What We Can Start Now

Safe current actions:

- docs-only future planning
- conceptual tag maps
- Hat 001 Bash tag registry
- Hat 002 RHCSA planning shell
- status vocabulary
- source registry concept
- validation workflow concept
- linking future tags to existing commits/reports
- no runtime integration

## 11. What Must Wait

These items must wait:

- tag resolver
- server storage
- public LLM chat link ingestion
- model ranking implementation
- IOA verification engine
- hat marketplace/sharing
- Android engineering workflows
- trading bot knowledge hat
- trading bot integration
- autonomous execution
- execution authority
- shell execution
- Cloudflare/provider/routing changes

## 12. Public Framing

Safe public wording:

"AOIA is exploring a future knowledge-verification roadmap where lightweight knowledge hats may use symbolic tags to point to validated knowledge entries, while future model-verification layers may assess models by epistemic discipline, source handling, contradiction behavior, and safety-boundary compliance."

Polish version:

"AOIA bada przyszły kierunek weryfikacji wiedzy, w którym lekkie czapki wiedzy mogą używać symbolicznych tagów jako kluczy do zweryfikowanych wpisów wiedzy, a przyszłe warstwy weryfikacji modeli mogą oceniać modele według dyscypliny epistemicznej, pracy ze źródłami, obsługi sprzeczności i respektowania granic bezpieczeństwa."

## 13. Non-Goals

This document does not implement:

- runtime changes
- tag resolver
- server KB
- source registry runtime
- model ranking engine
- public LLM link ingestion
- execution
- trading logic
- Android tooling
- GUI
- Cloudflare integration

## 14. Next Immediate Step

Next immediate docs-only step after this roadmap:

Create detailed NiFe Synapses plan and first two tag maps:

- Hat 001 Bash Safety / Bash Domain
- Hat 002 RHCSA / Linux Administration Domain
