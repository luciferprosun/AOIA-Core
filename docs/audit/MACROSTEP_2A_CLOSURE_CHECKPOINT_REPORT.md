# Macrostep 2A Closure Checkpoint - Artifact Surface Hardening

## Status

Macrostep 2A is complete.

AOIA-Core currently provides a local deterministic controlled flow that can produce a workspace-bound artifact after proposal, approval, audit, sandbox decision, path/resource validation, and structural contract validation. Macrostep 2A hardened the artifact write surface and added adversarial tests, but durable approval binding and persistent audit trail remain open.

## Branch and Commits

- Branch: `feature/m2-b0-provider-critic-inert-core`
- 2A-1 commit: `0a5dc95 test: harden sandbox artifact path surface`
- 2A-2 commit: `2ffb398 test: add sandbox artifact contract guard`
- Current HEAD at checkpoint creation: `2ffb398 test: add sandbox artifact contract guard`

## What Macrostep 2A Changed

### 2A-1 - Artifact Path/Resource Hardening

2A-1 hardened the workspace-bound artifact write surface:

- NFC Unicode path normalization.
- Absolute path rejection.
- `..` traversal rejection.
- Empty path component rejection.
- Control character rejection.
- `.git` path rejection.
- Extension allowlist: `.txt`, `.md`, `.json`.
- Explicit case handling for allowed extensions.
- Canonical realpath/commonpath containment.
- Symlink output and symlink parent rejection.
- Overwrite blocked by default.
- Atomic same-directory temporary write with fsync and final link/replace.
- No partial target file on blocked size/path cases.

2A-1 resource limits:

- Maximum artifact size: `64 KiB`.
- Maximum path depth: `8` components.
- Maximum filename/path segment byte length: `128` bytes.

### 2A-2 - Structural Contract/Call-Site Guard

2A-2 added a minimal local structural guard before artifact writes:

- `SandboxArtifactRequest` now carries structural artifact contract fields.
- The contract includes version, artifact-write-allowed marker, approval decision id, sandbox policy decision id, sandbox result state, content hash binding, and audit event binding.
- `write_sandbox_artifact()` fails closed before path validation or file write if the structural contract is missing, malformed, denied, hash-mismatched, audit-mismatched, or has an ineligible sandbox result state.
- M9 dry-run artifact integration populates the structural contract from the existing dry-run/sandbox flow.

## What Macrostep 2A Did Not Add

- No shell execution.
- No subprocess, `Popen`, or `os.system`.
- No provider/API/network calls.
- No API key or secrets handling.
- No browser, git, or cloud capability.
- No DB, SQLite, or ORM.
- No SafeFileWriter.
- No durable audit persistence.
- No audit JSONL or audit fsync persistence.
- No workspace registry.
- No cryptographic approval token, key management, or durable nonce store.
- No new UI.
- No new autonomous agent capability.

## Current Validation

Latest validation state from Macrostep 2A closure:

- `python3 -m compileall -q runtime tests`: OK.
- M2-B0 focused suite: OK.
- M2-B1 focused suite: OK.
- M2-B2 focused suite: OK.
- M2-B3 focused suite: OK.
- Evidence-1 focused suite: OK.
- M3-A focused suite: OK.
- M4-A focused suite: OK.
- M5-A focused suite: OK.
- M5-B focused suite: OK.
- M6-A focused suite: OK.
- M7-A focused suite: OK.
- M8-A focused suite: OK.
- M9-A focused suite: OK.
- M10-A focused suite: OK.
- Adversarial path safety: `16 OK`.
- Adversarial resource limits: `8 OK`.
- Adversarial state bypass: `10 OK`.
- Full suite: `1039 OK / 4 skipped`.
- `node --check web/app.js`: OK.
- `git diff --check`: OK.
- Static forbidden scan: no real forbidden runtime import or capability added; broad grep may show literal documentation/test strings and pre-existing text.

## Current Safety State

- Artifact writer is path/resource hardened.
- Artifact writer has a structural contract guard.
- The runner fails closed before path validation/write if the artifact contract is invalid.
- Artifact writes remain limited to safe text/Markdown/JSON artifacts inside an explicit sandbox workspace.
- The 2A structural guard is a code-review and refactor guardrail only, not cryptographic authorization.

## Residual Risks

- Durable approval binding is not yet implemented.
- Persistent audit trail is not yet implemented.
- Audit remains non-durable/in-memory for this flow.
- Max one artifact per run is deferred.
- Workspace/project registry is deferred.
- The structural guard reduces accidental/refactor bypass risk but is not a cryptographic security boundary.

## Recommended Next Step

Macrostep 2B: durable approval binding and persistent audit trail.

Recommended 2B constraints:

- Keep scope narrow.
- No UI, browser, provider, shell, or cloud capability.
- No workspace registry until 2B is closed.
