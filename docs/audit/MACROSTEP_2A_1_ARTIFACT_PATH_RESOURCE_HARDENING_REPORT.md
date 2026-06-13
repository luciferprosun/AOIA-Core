# Macrostep 2A-1 Artifact Path & Resource Hardening Report

## Summary

AOIA-Core v0 remains a local deterministic controlled flow. Macrostep 2A-1 hardens the artifact write surface against path/resource abuse and adds adversarial tests. It does not add shell execution, provider calls, browser automation, git automation, cloud execution, durable audit persistence, workspace registry, generalized file writer, or new agent capability.

## What Changed

- Hardened sandbox artifact path normalization and validation.
- Added explicit artifact path depth and filename byte limits.
- Kept the existing artifact content size ceiling and enforced it before opening any output file.
- Changed artifact writes to a same-directory temporary file followed by atomic publish.
- Added adversarial path safety tests.
- Added adversarial resource limit tests.

## Path Hardening Details

- Paths are Unicode-normalized with NFC before validation.
- Absolute artifact paths are rejected before workspace joining.
- `..` path traversal is rejected before workspace joining.
- Empty path components are rejected.
- Control characters are rejected.
- `.git` path components are rejected.
- Artifact suffixes remain limited to `.txt`, `.md`, and `.json`, with case-insensitive suffix handling.
- Final containment uses canonical real paths and `commonpath` against the explicit workspace root.
- Symlink output paths and symlink parent directories are blocked.
- Output paths are still required to resolve inside the explicit sandbox workspace.

## Resource Limits

- Maximum artifact content size remains `64 * 1024` bytes.
- Maximum artifact path depth is `8` components.
- Maximum path segment byte length is `128` bytes.
- Existing file overwrite remains blocked by default.
- Overwrite is only allowed when explicitly requested and still inside the validated workspace.
- Atomic write uses a temporary file in the target directory, flush/fsync, and final link or replace.
- Oversized content and rejected paths do not create partial target files.

## What Did Not Change

- No shell execution was added.
- No subprocess, `Popen`, or `os.system` was added.
- No provider/API/network calls were added.
- No API key or secrets handling was added.
- No browser, git, GCP, or cloud capability was added.
- No DB, ORM, or sqlite3 capability was added.
- No durable audit persistence was added.
- No workspace registry was added.
- No generalized file writer was added.
- No UI or web endpoint was added.
- No structural contract guard was implemented in this step.

## Adversarial Test Summary

- Path safety tests cover absolute paths, traversal, parent components, empty path components, control characters, null-like strings, Unicode normalization, symlink escape, realpath/commonpath containment, unsafe extensions, double extensions, overwrite prevention, and partial-file prevention.
- Resource tests cover exact artifact size limit, one-byte-over rejection, exact path depth, one-over-depth rejection, exact filename byte length, one-over filename rejection, deeply nested path rejection, and large payload partial-file prevention.

## Known Residual Risks

- Direct runner call / control-flow bypass is not fully resolved until Macrostep 2A-2.
- Durable approval binding and persistent audit trail remain unresolved until a later macrostep.
- Max one artifact per run remains deferred because Macrostep 2A-1 does not introduce run-level state or a workspace registry.

## Next Step

Recommended next normal AOIA-Core production step: Macrostep 2A-2 structural contract/call-site guard.
