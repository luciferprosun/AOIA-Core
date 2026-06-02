# GT-RUNTIME Roadmap

## Completed

### GT-RUNTIME-6

Controlled classification regression harness and audit baseline.

This milestone established a controlled command classification regression test on 12 curated internal shell-command cases. The current regex or rule logic matched all 12 internal test cases. This is an internal regression harness and a basis for seeking initial external technical review.

### GT-RUNTIME-7A

Docs-only honesty pack.

This milestone adds reviewer-facing documentation to clarify scope, limitations, reproduction steps, terminology, and next-step boundaries without changing runtime code.

## Planned Next, But Not Part of GT-RUNTIME-7A

### GT-RUNTIME-7B

- Inert CommandProposal DTO or schema.
- Approval-gate control-flow tests using mocks.
- Adversarial corpus v0.2 taxonomy or stub.
- Ledger schema documentation.

## Explicit Exclusions

- No shell execution.
- No sudo.
- No autonomous terminal agent.
- No `shell_tools.py` expansion.
- No `executor.py` changes.
- No `event_ledger.py` changes unless separately justified later.
- No GUI, provider, or Cloudflare expansion.
