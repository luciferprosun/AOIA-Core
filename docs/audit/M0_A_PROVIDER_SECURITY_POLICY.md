# M0-A Provider Security Policy

Date: 2026-06-08

Phase: M0-A provider security policy, docs-only.

## Purpose

M0-A defines the reviewer-safe policy boundary for future AOIA-Core model-selection expansion across Gemini, OpenRouter, free models, paid models, local models, provider keys, prompts, fallback behavior, logging, and human approval.

This document is policy only. It does not add model-router schemas, OpenRouter integration, Gemini integration, manual model selector behavior, provider health checks, runtime routes, API calls, package installs, execution behavior, or autonomous provider choice.

## Project Identity

AOIA-Core / AIOA WhiteHat remains:

- local-first
- human-led
- audit-first
- source-aware
- reviewer-auditable
- non-executing by default
- conservative about autonomy
- hostile to uncontrolled agent behavior

Provider selection must support that identity. A provider is a text generation source, not an authority surface.

## Scope

M0-A covers policy for future provider governance:

- Gemini provider use
- OpenRouter provider use
- free remote model use
- paid remote model use
- local model use
- API key handling
- prompt and response handling
- fallback chains
- health checks
- logging and redaction
- human approval gates
- reviewer-facing claims

M0-A creates no executable capability.

## Relationship To H4 And C4

H4-C froze the current browser-adjacent surface as not approved for H4 autonomous browser flow. H4-B added inert browser/file/PDF/ZIP proposal vocabulary only.

C4-A documented helper-model boundaries. C4-B added inert helper-model proposal schemas. C4-C added tests proving those proposal objects cannot write, commit, execute, call browser/runtime tools, or promote canonical knowledge.

M0-A does not weaken those boundaries. Model provider output remains advisory text or proposal material unless a human reviewer explicitly approves a separate manual action.

## Provider Classes

Future provider policy distinguishes these classes:

- `remote_free`: remote provider route using a free model or no-charge tier.
- `remote_paid`: remote provider route that may incur direct or indirect cost.
- `remote_unknown_cost`: remote provider route whose cost cannot be confirmed locally.
- `local_model`: local model route running on the operator machine.
- `disabled_provider`: configured or discovered provider that is not approved for use.

Unknown cost defaults to paid-risk handling.

## Gemini Boundary

Gemini may be used only as a human-selected remote model provider when the required local key is present and the operator understands that prompt content leaves the local machine.

Gemini output is not canonical knowledge, not verified evidence, not source provenance, and not authority over repository changes.

Gemini must not:

- browse on AOIA's behalf
- write repository files
- execute shell commands
- approve commits
- promote Hat knowledge
- verify sources without human review
- receive secrets, credentials, cookies, private tokens, or unredacted sensitive payloads

## OpenRouter Boundary

OpenRouter may be used only as a human-selected remote provider gateway when the required local key is present and the selected model is clear to the operator.

OpenRouter routing must not hide whether a model is free, paid, unknown-cost, experimental, or provider-routed through a third party.

OpenRouter output is untrusted model output. It may support drafting, critique, comparison, summarization, and proposal creation, but it cannot become canonical knowledge or repository action without human review.

## Free Model Policy

Free model availability is not a safety property.

Free models may still receive prompts, leak sensitive content to a remote provider, hallucinate, produce unsafe command advice, or change behavior without AOIA control.

Free models require the same redaction, logging, source skepticism, and human review boundaries as paid models.

## Paid Model Policy

Paid model use requires explicit human approval before first use in a session or before switching from a free/local route to a paid route.

A future paid-model approval record should capture:

- selected provider
- selected model
- operator identity or local reviewer label
- timestamp
- cost class
- prompt-risk class
- whether fallback to another paid model is allowed
- whether the approval is one-shot or session-scoped

No automatic escalation from free to paid is allowed.

## Local Model Policy

Local models are preferred when privacy, repeatability, or low-risk drafting is more important than remote model quality.

Local does not mean trusted. Local model output remains unverified and non-canonical until reviewed.

Local model use must still obey:

- no automatic execution
- no automatic file writes
- no automatic commits
- no automatic canonical promotion
- no silent provider fallback to remote models

## API Key Policy

Provider keys must remain outside the repository.

Allowed local key locations include private operator-controlled files such as:

- `~/.config/aoia/secrets/gemini.env`
- `~/.config/aoia/secrets/openrouter.env`

Key files should be readable only by the local user, preferably mode `600`, with parent secret directories restricted, preferably mode `700`.

M0-A forbids:

- committing keys
- printing keys in logs
- copying keys into docs
- storing keys in runtime state files
- sending keys to other providers
- exposing keys through UI status payloads
- using chat transcripts as secret storage

## Prompt Handling

Prompts sent to remote providers must be treated as external disclosure.

Before a future provider call, AOIA should classify prompt risk:

- public project text
- repository metadata
- private local path
- personal data
- secret-bearing content
- source material under review
- executable command text
- unknown sensitivity

Secret-bearing content must not be sent to remote providers. Unknown sensitivity should default to requiring human review.

## Response Handling

Model responses are untrusted until reviewed.

Remote or local model output may be stored only as clearly labeled operational review material, proposal material, or audit context. It must not be treated as evidence, provenance, verified source content, command authorization, canonical Hat knowledge, or runtime policy.

Model output that proposes commands, file edits, browser actions, provider changes, or knowledge promotion remains inert text.

## Fallback Policy

Fallback must be explicit and reviewer-auditable.

Future fallback logic must not:

- silently switch from local to remote
- silently switch from free to paid
- silently switch from one provider to another when prompt sensitivity changes
- hide provider or model identity
- retry sensitive prompts across multiple providers without approval
- treat successful generation as verification

Fallback failure should produce a clear error rather than an uncontrolled provider cascade.

## Health Check Policy

Provider health checks must be non-sensitive and low cost.

Allowed future health checks may verify:

- provider library import availability
- key presence without printing key value
- network reachability
- model list availability
- minimal no-secret generation if the human explicitly approves

Health checks must not send repository content, source material, credentials, private paths, personal data, or canonical knowledge records by default.

## Logging And Redaction

Logs must be useful for review without leaking secrets.

Allowed log fields include:

- provider name
- model name
- cost class
- timestamp
- request status
- failure class
- redacted prompt summary
- response length
- approval record reference

Forbidden log fields include:

- raw API keys
- authorization headers
- cookies
- session tokens
- complete secret-bearing prompts
- unredacted private payloads

Prompt and response logging should be opt-in for sensitive sessions.

## Human Approval Boundary

Humans retain final authority.

Human approval is required before:

- using a paid or unknown-cost route
- sending sensitive or source-heavy prompts to remote providers
- enabling fallback from local to remote
- enabling fallback from free to paid
- accepting model output as a proposal for repository change
- converting proposal material into manual action
- promoting candidate knowledge toward canonical review

Human approval does not authorize automatic execution unless a separate explicit execution policy exists.

## No Execution Boundary

M0-A does not approve provider-triggered execution.

No provider output may directly cause:

- shell execution
- browser action
- file write
- file deletion
- package installation
- runtime route mutation
- provider configuration mutation
- commit
- push
- canonical knowledge promotion

## No Canonical Promotion Boundary

Provider output is not canonical.

Provider output may become a candidate only after human review and source provenance checks. Candidate material must remain separate from canonical Hat 001, Hat 002, Hat 003, and Hat 004 records until a later approved manual promotion process exists.

## Reviewer Wording

Safe wording:

- human-selected provider
- provider output proposal
- model-assisted draft
- remote model disclosure boundary
- free model is not a safety guarantee
- paid model requires human approval
- fallback is explicit and auditable
- model proposes, human decides

Unsafe wording:

- autonomous provider routing
- model verifies sources
- provider output is evidence
- automatic paid fallback
- automatic canonicalization
- AI commits changes
- Gemini/OpenRouter controls the repo
- safe autonomous model selector

## Stop Conditions

M0 work stops if:

- a provider key is printed or committed
- a model/API call is introduced before approval policy is implemented
- fallback can silently change cost class
- fallback can silently change local/remote disclosure class
- provider output can write files
- provider output can execute commands
- provider output can trigger browser actions
- provider output can commit or push
- provider output can promote canonical knowledge
- logs contain unredacted secrets or sensitive prompts
- documentation overclaims production readiness or autonomy

If a stop condition is triggered, changes are reverted or quarantined and a human reviewer decides the next step.

## Validation Checklist

M0-A is valid only if:

- only this policy document is created for M0-A
- no runtime behavior is modified by M0-A
- no provider routing is changed by M0-A
- no schema or test is created by M0-A
- no browser is launched by M0-A
- no model/API provider is called by M0-A
- no package is installed by M0-A
- no key value is printed or stored in the repository
- no commit or push is performed by M0-A
- existing H4 and C4 boundaries remain intact

## Non-implementation Statement

M0-A is docs-only.

M0-A does not implement OpenRouter support.

M0-A does not implement Gemini support.

M0-A does not implement model-router schemas.

M0-A does not implement a manual model selector.

M0-A does not implement provider health checks.

M0-A does not call APIs or models.

M0-A does not install packages.

M0-A does not change runtime behavior.
