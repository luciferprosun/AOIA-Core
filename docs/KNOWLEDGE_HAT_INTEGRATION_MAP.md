# Knowledge HAT Integration Map

The runtime catalog is the machine-readable source of truth. This map explains
the bounded integration without storing corpus files or private operator paths.

## German Federal Law 1A

- Logical HAT id: `german_federal_employment_worker_law`
- Public display name: `German Federal Law`
- Domain: German federal employment-law evidence
- Adapter: `apps/aoia_desktop_demo/knowledge/hats/adapters/german_federal_employment_worker_law.py`
- Catalog: `apps/aoia_desktop_demo/knowledge/hats/catalog_entries/german_federal_employment_worker_law.json`
- External resource: yes; corpus committed to this repository: no
- Local binding key: `german_federal_employment_worker_law_local`
- Required library identity: `de-law-federal-1a`, version `1a`
- Required manifest identity: `federal-temporal-1a-fe9ce34784e92af97651fe0378672d4c`
- Required manifest digest: `602922920c30dcae567a1bc4f8459060a24ae507b4d432ebf82673320e20a7a2`
- Required index identity: `german-law-fts5+federal-temporal-graph-1a`
- Required index digest: `8491438dd28a428a69a9bf5c49b215f63ff35507124378f0c635bf11b2448f19`
- Evidence schema version: `1`
- Authority: evidence only; non-authoritative

The adapter validates the external manifest, the FTS5 index, the temporal-index
metadata, corpus-relative document records, and content-addressed source
objects. It opens SQLite with `mode=ro&immutable=1`; it does not import or
execute code from the external resource.

## Generic runtime components

- Contracts and protocol: `apps/aoia_desktop_demo/knowledge/hats/contracts.py`
- Canonical serialization and hashing: `apps/aoia_desktop_demo/knowledge/hats/canonical.py`
- Static catalog parser: `apps/aoia_desktop_demo/knowledge/hats/catalog.py`
- Explicit trusted registry: `apps/aoia_desktop_demo/knowledge/hats/registry.py`
- Private local-binding loader: `apps/aoia_desktop_demo/knowledge/hats/bindings.py`
- Attachment service: `apps/aoia_desktop_demo/knowledge/hats/service.py`
- Fixed prompt boundary: `apps/aoia_desktop_demo/knowledge/hats/prompt_rendering.py`
- Settings integration: `apps/aoia_desktop_demo/ui/settings_dialog.py`
- Generic evidence preview: `apps/aoia_desktop_demo/ui/hat_evidence_dialog.py`
- Controller integration: `apps/aoia_desktop_demo/app.py`
- Focused tests: `apps/aoia_desktop_demo/tests/test_knowledge_hats_*.py`
- Sanitized binding example: `config/knowledge_hats/local_bindings.example.json`

## Adding a future HAT

A future HAT adds one adapter implementing `KnowledgeHatAdapter`, one catalog
entry, focused adapter tests, and one private operator binding. The explicit
trusted registry receives the adapter factory. No domain-specific branch is
added to the application controller, Critic Loop runner, finalizer, generic
preview, provider routing, or Conversation delivery path.

Catalog entries are display and validation metadata. They cannot import code,
dispatch, approve, write, execute, call a provider, or satisfy a human barrier.
The private binding file stays outside Git. Corpus files, large data files,
provider secrets, and absolute local machine paths are not stored here.

## Offline acceptance prompt

The prepared manual prompt is:

> Under current German law, can an employment contract be concluded orally,
> and what documentation of the essential working conditions must the employer
> provide?
>
> Please distinguish the validity of the employment contract from the
> employer's documentation obligations and mention relevant statutory
> provisions, form requirements and important exceptions.
>
> Do not browse the internet. State any remaining uncertainty.

Preparing this prompt does not execute a provider request.
