# AUTH Identity Path Redaction False-Positive Repair 1A

## Scope

This bounded baseline-security repair preserves safe, human-readable repository,
worktree and branch identity text before hash-bound AUTH evaluation. It does not
change approval semantics, identity equality, gates, execution, writes, provider
calls, network access or any authority flag.

## Root cause

The generic high-entropy token candidate matched a complete long worktree path.
The approval record therefore bound `[REDACTED]` while the request retained the
original path. AUTH-1C rejected the changed identity and AUTH-1E correctly failed
closed; AUTH-1F and AUTH-1G failures were downstream consequences.

## Correction

The shared redactor now recognizes conservative lexical structure in absolute
paths, branch-like identities and multi-component readable slugs. The classifier
is private, deterministic and pure. It does not inspect the filesystem,
environment or active repository and contains no literal identity allowlist.

Explicit credentials and known secrets are still redacted before the identity
classifier runs. Opaque high-entropy candidates remain redacted, including
Base64, Base64URL and mixed symbol forms. Existing terminal/control sanitization
and hash-bound identity equality checks remain unchanged.

## Authority boundary

Readable identity is not approval or authority. Human approval remains separate,
explicit and hash-bound. Stale or mismatched evidence continues to fail closed.
No provider, network, execution, write, dispatch, GitHub, gate, Control Write or
Orchestra capability is added.

## Validation

Final focused, regression, static, freeze, compile and full-suite results are
recorded in the production handoff accompanying the commit.
