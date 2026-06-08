# M0-B Model Router Decision Record

Date: 2026-06-08

## Status

DRAFT / DOCS-ONLY / NO IMPLEMENTATION

## Baseline

M0-A provider security policy exists at `docs/audit/M0_A_PROVIDER_SECURITY_POLICY.md`.

The current branch checkpoint before M0-B is clean at:

```text
6c50185 fix: resolve web UI static asset path
```

No model router is implemented yet.

No transparent model selection UI is implemented yet.

No provider health check implementation is approved by this document.

No automatic provider fallback is approved by this document.

## Purpose

M0-B defines how AOIA-Core will introduce transparent model and provider selection safely.

The goal is to prepare reviewer-auditable architecture boundaries before any model-router schema, provider call, health check, runtime integration, or UI behavior is added.

Provider selection must remain human-led, explicit, auditable, and conservative about autonomy.

## Non-goals

M0-B does not implement:

- active routing
- provider API calls
- Gemini calls
- OpenRouter calls
- local model execution
- automatic fallback
- free or random model routing for sensitive or canonical tasks
- canonical promotion from model output
- execution from provider response
- secret logging
- budget automation
- model-router schemas
- health checks
- UI that implies real routing before routing exists

M0-B does not modify runtime behavior.

## Provider Classes

Future model-router work must distinguish provider classes before selection or fallback is allowed.

### Gemini

Gemini is a remote provider class.

Gemini use requires explicit human approval before any prompt is sent. Gemini output is untrusted model output, not evidence, not provenance, not canonical knowledge, and not execution authority.

### OpenRouter

OpenRouter is a remote provider gateway class.

OpenRouter use requires visible model identity, visible cost/trust class, and explicit human approval before any prompt is sent. OpenRouter must not hide third-party routing, paid status, or unknown model risk.

### OpenRouter Free Models

OpenRouter free models are development-only unless a later review explicitly approves a narrower use.

Free cost is not a safety guarantee. Free models must never be used for sensitive, core, canonical, secret-bearing, source-verification, or repository-authority tasks.

### Paid Models

Paid models require explicit human approval before use.

Paid model approval must identify provider, model, expected cost class, prompt risk class, and whether the approval is one-shot or session-scoped.

### Local Models

Local models are preferred for low-risk drafting, privacy-sensitive experiments, and offline review.

Local model output remains untrusted. Local models must not trigger execution, file writes, commits, browser actions, or canonical promotion.

### Disabled Or Unknown Providers

Disabled and unknown providers are not allowed for routing.

Unknown cost, unknown provider identity, unknown logging policy, or unknown data retention policy must default to blocked until human review.

## Safety Principles

Future model-router work must follow these principles:

- human approval is required before any provider call
- no automatic fallback across trust classes
- no automatic fallback from local to remote
- no automatic fallback from free to paid
- no automatic fallback from known provider to unknown provider
- provider response is untrusted input
- no secrets in logs
- no canonical knowledge promotion without human review
- no execution from model output
- all future calls must be auditable
- free and random providers are development-only
- free and random providers are never used for sensitive, core, canonical, source-verification, or repository-authority tasks
- model output may propose, but humans decide

## Trust Classes

Future routing decisions must treat provider class, cost class, and disclosure class as separate dimensions.

Minimum planned trust dimensions:

- local versus remote
- free versus paid versus unknown cost
- known provider versus unknown provider
- sensitive prompt versus non-sensitive prompt
- canonical task versus draft task
- operator-approved versus not approved

No fallback may cross any trust boundary unless a human explicitly approves that crossing.

## Prompt And Response Handling

Prompts sent to remote providers are external disclosure.

Sensitive prompts must be blocked until human review. Secret-bearing prompts must not be sent.

Provider responses are not verified facts. They are draft material, critique material, comparison material, proposal material, or operator-facing text until reviewed.

Provider responses must not directly:

- write files
- execute commands
- trigger browser actions
- mutate runtime configuration
- stage commits
- commit
- push
- promote canonical knowledge

## Logging And Auditability

Future provider calls must be auditable without leaking secrets.

Allowed future audit fields may include:

- timestamp
- provider name
- model name
- cost class
- trust class
- prompt-risk class
- approval reference
- request status
- redacted prompt summary
- response length or checksum
- failure class

Forbidden audit fields include:

- raw API keys
- authorization headers
- cookies
- session tokens
- complete secret-bearing prompts
- unredacted sensitive payloads

## Planned Future Milestones

### M0-C Inert Model-router Schemas Only

Define proposal-only model-router data shapes.

No provider calls. No routing. No health checks. No runtime integration.

### M0-D Local Transparent Model Catalog / UI Preview Only

Show local catalog and model-selection preview text.

No actual provider selection, no model call, and no implied active routing.

### M0-E Human Approval Model-selection Proposal

Define how a human approves a proposed provider/model selection.

Approval remains a proposal boundary unless later implementation explicitly wires a controlled call path.

### M1-A Provider Health Check Design

Design health checks while still avoiding automatic routing.

Health checks must be non-sensitive, redacted, explicit, and reviewer-auditable.

### M1-B First Controlled Manual Provider Call

Allow the first controlled manual provider call only after approval policy, prompt-risk classification, logging/redaction, and stop conditions are in place.

This milestone is not approved by M0-B. It is a future target that requires separate review.

## Stop Conditions

M0 work stops if:

- any API call appears
- any provider/model call appears
- any secret is printed
- any automatic fallback appears
- any runtime execution appears
- provider output is treated as trusted
- provider output is treated as evidence
- provider output is treated as canonical knowledge
- UI implies real routing before it exists
- free or random models are allowed for sensitive tasks
- runtime files are modified during this docs-only milestone
- provider routing files are modified during this docs-only milestone
- schema files are created during this docs-only milestone
- tests are created during this docs-only milestone

If a stop condition is triggered, changes must be reverted or quarantined and a human reviewer decides the next step.

## Reviewer Statement

This document prepares safe model-router implementation but does not implement routing.

M0-B is docs-only. It does not call providers, does not route prompts, does not implement fallback, does not add schemas, does not add tests, does not launch browsers, does not install packages, does not log secrets, and does not change runtime behavior.

Provider output remains untrusted unless reviewed by a human. Model output cannot execute, commit, push, or promote canonical knowledge.

## Validation Checklist

M0-B is valid only if:

- only `docs/audit/M0_B_MODEL_ROUTER_DECISION_RECORD.md` is created
- no runtime files are modified
- no provider files are modified
- no tests are created
- no schemas are created
- no browser is launched
- no provider/API/model call is made
- no packages are installed
- no secrets are printed
- no commit includes files outside this document
