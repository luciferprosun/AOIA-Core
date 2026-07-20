# Provider-Independent Knowledge Context Bridge 1A

## Implemented boundary

The bridge converts a validated `KnowledgeHub1B` execution into one immutable,
deterministic `KnowledgeContextPackage`, then binds that package to a separate
explicit `ProviderTarget`. Provider identity, model identity, credentials,
machine paths, and provider payload details are absent from the context package.

The sole runtime adapter calls the existing AOIA provider envelope builder and
provider gateway. It adds no HTTP client, SDK, endpoint, headers, retry,
fallback, streaming, tool calling, subprocess, filesystem write, or background
loop. Dry-run is the CLI default; live provider testing remains subject to the
existing provider activation policy and was not authorized by this step.

## Evidence and response handling

Each selected module receives a separate context section retaining module and
instance IDs, corpus and temporal snapshots, source SHA-256, evidence IDs,
temporal state, warnings, and truncation state. Canonical JSON serialization
marks evidence as untrusted data and safely encodes control characters.
Where a deployment pins immutable source snapshots but retrieval binds evidence
to a derived factory or index snapshot, the section preserves both layers and
validates every item against the resulting provenance set.

Provider output must be exactly one strict structured JSON object. Structural
validation checks current-request evidence IDs and module ownership. It neither
repairs output nor evaluates semantic truth. Cross-module contradiction analysis
and semantic hallucination detection remain deferred.

## Authority and limits

All context, policy, failure, validation, request, answer, and result contracts
remain non-authoritative. They cannot approve, write, execute, commit, push,
call tools, change gates, satisfy a human barrier, or provide binding legal
advice.

Reviewed defaults cap context at 40 evidence items, 4,000 excerpt characters per
item, 48,000 evidence-context characters, and 64,000 serialized characters.
Allocation reserves bounded representation for each selected module, then uses
stable profile order. Truncation is deterministic and preserves provenance.
