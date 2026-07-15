# AOIA-Core Current State

Status: complete development-prototype handoff under controlled repository cleanup

Audience: architects, programmers, reviewers, and security reviewers

Last updated: 2026-07-14

AOIA-Core is a local-first, human-controlled epistemic control system. It is not
an autonomous agent and no metadata object, route, score, preview, freeze, or
test result grants execution or write authority.

## Implemented state

- Provider Runtime, Selector, and Critic preserve provider output as untrusted.
- Artifact Preview and ActionProposal remain metadata-only.
- Controlled write remains bound to the separate canonical human barrier.
- Durable Audit Ledger and static capability boundaries are test-protected.
- Knowledge Foundation records carry exact provenance without authority.
- Linux, Bash, Python, and UNIX Hats are retained and validated.
- The UNIX flow performs deterministic local ingestion, retrieval, inert routing, and offline static review.
- The current UNIX freeze is `aoia-unix-unit-1a-r1`.
- The complete handoff inventory is `data/architect_handoff_manifest_1a.json`.

## Verified baseline

The baseline entering Cleanup 1E was 3,255 passed, 4 skipped, 0 failures, and
0 errors. Stable installed entrypoints and the updated suite are validated by
the Cleanup 1E report; this file intentionally avoids binding to a branch or
commit so it remains useful after a controlled checkpoint.

## Canonical developer path

Use `README.md` for installation and the five tested commands. Use
`START_HERE_ARCHITECT.md` for the short architecture map. `pyproject.toml` is
the only canonical dependency and console-entrypoint declaration.

## Boundaries and limitations

Provider and critic output, knowledge, Hats, routing, retrieval, previews,
ledger entries, manifests, and freeze evidence are non-authoritative. The UNIX
corpus is bounded, lexical retrieval is not guaranteed correct, and the offline
prototype executes nothing. Historical reports remain evidence of prior states
and must not override current code, tests, or governance.
