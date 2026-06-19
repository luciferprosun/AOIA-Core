# AOIA Cleanup Repo Identity

Date: 2026-05-28
Scope: analysis only; no runtime changes.

## Repository Identity

| Field | Value |
| --- | --- |
| Current path | `/home/l/Desktop/AOIA-Core` |
| Branch | `main` |
| HEAD | `ee6f64a` |
| Remote | `origin https://github.com/luciferprosun/AOIA-Core.git` |
| Public canonical URL | `https://github.com/luciferprosun/AOIA-Core` |
| Working tree before reports | clean |

## Naming Check

The canonical public repository is `AOIA-Core`, not `AIOA-Core`.

Recommendation: use `AOIA` consistently in public URLs, docs, package names, and future AOIA-Nano naming. Treat `AIOA` as a typo/legacy alias only. If any external references use `AIOA`, document them as redirects or historical mismatches rather than adopting the spelling.

## AOIA-Nano Positioning

Recommended public positioning:

> AOIA-Nano is a deterministic local provenance kernel for auditable AI-assisted workflows.

Rejected positioning:

- autonomous agent framework
- AGI system
- multi-agent swarm
- biological intelligence simulation
- speculative cognition system

## Web-Informed Boundary

AOIA should not compete with agent orchestration frameworks. LangGraph describes itself as focused on agent orchestration, while MCP exposes model-invokable tools/resources, and OpenHands targets software-development agents. AOIA-Nano should stay below that layer: deterministic routing, local provenance, approval and replay.

Reference URLs:

- LangGraph docs: https://docs.langchain.com/oss/python/langgraph
- MCP tools docs: https://modelcontextprotocol.io/docs/concepts/tools
- OpenHands SDK docs: https://docs.openhands.dev/sdk/index
