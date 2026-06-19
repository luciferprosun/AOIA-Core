# Macrostep 2A-2 Structural Contract Guard Report

## Summary

AOIA-Core v0 remains a local deterministic controlled flow. Macrostep 2A-2 adds structural call-site guardrails so the artifact runner is harder to misuse directly. It does not add shell execution, provider calls, browser automation, git automation, cloud execution, durable audit persistence, workspace registry, generalized file writer, cryptographic approval tokens, or new agent capability.

## What Changed

- Added a local structural artifact contract to `SandboxArtifactRequest`.
- Added runner-side contract validation before path validation or any file write.
- Updated M9 dry-run artifact integration to populate the structural contract from the existing dry-run and sandbox records.
- Added adversarial state-bypass tests for missing, malformed, denied, and mismatched contract state.

## Structural Guard

The artifact runner now requires the request to carry:

- artifact contract version;
- artifact-write-allowed marker;
- human approval marker;
- dry-run identifiers;
- approval decision id;
- sandbox request id;
- sandbox policy decision id;
- sandbox result id;
- eligible sandbox result state;
- content hash binding;
- audit event binding.

The runner fails closed when the contract version is missing or malformed, artifact write is not allowed, approval is missing, sandbox result state is not eligible, content hash does not match the contract payload hash, or the request audit event does not match the contract audit event.

This is a structural code-review guardrail. It is not cryptographic authorization.

## Direct-Call Bypass Tests

Added `tests/adversarial/test_state_bypass.py` covering:

- missing contract marker rejection;
- malformed contract marker rejection;
- policy-denied artifact-write contract rejection;
- invalid sandbox result state rejection;
- audit relationship mismatch rejection;
- content hash mismatch rejection;
- missing dry-run identifier rejection;
- M9 dry-run artifact integration still succeeds;
- M10 controlled agent demo still succeeds;
- no new forbidden runtime capability imports.

## 2A-1 Hardening Still Preserved

The 2A-1 path and resource hardening remains active:

- NFC path normalization;
- absolute path rejection;
- traversal rejection;
- empty component rejection;
- control character rejection;
- `.git` rejection;
- extension allowlist;
- realpath/commonpath containment;
- symlink rejection;
- overwrite block by default;
- atomic write;
- 64 KiB max artifact size;
- path depth limit of 8;
- filename/path segment byte limit of 128.

## What Did Not Change

- No shell execution was added.
- No subprocess, `Popen`, or `os.system` was added.
- No provider/API/network calls were added.
- No API key or secrets handling was added.
- No browser, git, GCP, or cloud capability was added.
- No DB, ORM, or sqlite3 capability was added.
- No durable audit persistence was added.
- No audit JSONL or audit fsync persistence was added.
- No workspace registry was added.
- No generalized file writer was added.
- No cryptographic approval token, key management, or durable nonce store was added.
- No UI or web endpoint was added.

## Known Residual Risks

Durable approval binding and persistent audit trail remain unresolved until Macrostep 2B. This structural guard reduces accidental/refactor bypass risk but is not cryptographic authorization.

The guard does not prove real-world identity or durable approval history. It only requires the local request object to carry the expected controlled-flow shape before the workspace-bound artifact runner can write.

## Next Step

Recommended next normal AOIA-Core production step: Macrostep 2B durable approval binding and persistent audit trail, or a smaller preparatory macrostep if 2B is split.
