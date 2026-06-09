# AOIA Future Compatibility Notes

Date: 2026-05-28
Scope: notes only; no implementation.

## Future Adapters

| Adapter | Purpose | When to consider |
| --- | --- | --- |
| MCP adapter | Expose read-only provenance/retrieval tools to MCP clients. | After AOIA-Nano ledger and retrieval API are stable. |
| OpenLineage exporter | Export AOIA run/job/artifact/facet style metadata. | After ledger has stable `run_id`, event kinds, and artifact records. |
| SLSA-style provenance attestation exporter | Produce attestations for generated artifacts or knowledge packs. | After subject/material/builder naming is stable. |
| Sigstore/Rekor anchoring | Anchor signed ledger checkpoints or release artifacts in transparency logs. | After local signing and offline verification are designed. |
| DVC/lakeFS-style knowledge versioning | Version RHCSA knowledge packs and raw/build artifacts separately from runtime. | During or after `aoia-knowledge-rhcsa` split. |
| LangGraph integration | Optional adapter for external orchestration frameworks. | Only after AOIA-Nano MVP proves useful as a provenance kernel. |

## Design Boundary

MCP tools are model-invokable; LangGraph is orchestration-focused; OpenHands is a software-agent platform. AOIA-Nano should remain a provenance and approval layer underneath such systems, not an imitation of them.

## Reference URLs

- MCP tools: https://modelcontextprotocol.io/docs/concepts/tools
- OpenLineage spec: https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md
- SLSA provenance: https://slsa.dev/spec/v0.2/provenance
- Sigstore Rekor: https://docs.sigstore.dev/logging/overview/
- DVC docs: https://dvc.org/doc/user-guide/what-is-dvc
- lakeFS docs: https://docs.lakefs.io/
- LangGraph docs: https://docs.langchain.com/oss/python/langgraph
