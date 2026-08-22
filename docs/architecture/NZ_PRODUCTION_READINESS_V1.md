# NZ Production Readiness v1

Status: full-suite-validated local freeze record on 2026-08-22. This file is
committed by `nz: freeze production readiness architecture`.

This document records the implemented boundary of NZ Production Readiness v1.
It extends NZ Foundation v1 and NZ Operational Hardening v1 without replacing
their authority, containment, uncertainty, redaction, or provenance rules.

## Scope and lineage

The scope is the local AOIA runtime in this repository. P2 adds:

- P2.1 startup integrity and a versioned configuration contract;
- P2.2 local, project-scoped, verified backup and isolated restore; and
- P2.3 a deterministic local release manifest and optional Ed25519
  attestation.

The work started from the P1 freeze
`57f28f6ebb46094a4517fc70ddfc9568658a0050` on the local branch
`nz/p2-production-readiness`. The implementation lineage is:

| Boundary | Commit |
| --- | --- |
| NZ Foundation v1 integration | `4393f90b7f329d2c42e87de893f41d23105380a6` |
| NZ Operational Hardening v1 freeze | `57f28f6ebb46094a4517fc70ddfc9568658a0050` |
| P2.1 Startup Integrity | `463d739730bdb0e446996fe0fdf07c5cd4017fa5` |
| P2.2 Backup / Restore | `a4a2c727e3d5464631d60a1c742ded5326963712` |
| P2.3 Release Attestation | `7fd18bbf6ffe2f3bff717812277083ce2db4ff9a` |
| P2 integration fix: credential-store exclusions | `971f985d83368ac7fbaa98961cb1670df7d048cb` |

No deployment, external provider call, remote publication, cloud operation,
production key creation, or push is part of this freeze.

## Relationship to P0 and P1

NZ Foundation v1 remains the execution-authority and durable-state foundation:
filesystem containment, sanitized subprocess environments, capability and
approval policy, bounded execution time, trace identity, atomic persistence,
durable idempotency, hash-chained provenance, task checkpoints, restart
recovery, explicit outcomes, local Web/API safety, and sensitive-output
redaction.

NZ Operational Hardening v1 continues to provide bounded Web admission and
lifecycle controls, Linux child-process resource/tree containment, and
optional offline Ed25519 anchors over P0.8 provenance.

P2 consumes those boundaries. It does not turn configuration, a preflight
report, a backup, an anchor, a release manifest, or test evidence into
execution authority. P0.7 uncertain effects remain non-replayable, P0.11
unknown outcomes remain explicit, and P0.13 redaction remains upstream of
model, HTTP, console, and persistence projections.

## P2.1 Startup Integrity and Configuration Contract

P2.1 defines `AOIA_STARTUP_PREFLIGHT_1A`. It returns one explicit status:

- `READY`;
- `READY_DEGRADED`;
- `BLOCKED_CONFIGURATION`;
- `BLOCKED_STATE`;
- `BLOCKED_PROVENANCE`;
- `BLOCKED_SECURITY_INVARIANT`; or
- `MANUAL_REVIEW_REQUIRED`.

The contract classifies inputs as `REQUIRED`, `OPTIONAL`,
`FEATURE_REQUIRED`, `SECRET_REFERENCE`, `BOUNDED_TUNABLE`, or `DERIVED`.
Reports expose only allowlisted facts: schema and source identities, hashed
project/state identities, configured booleans, effective finite settings,
capability decisions, state-schema results, anchor status, and fixed reason
codes. They do not copy environment values, bearer tokens, API keys,
passwords, private signing keys, or secret-file contents.

### Validation and activation

Before CLI runtime construction or Web listener/service construction, the
preflight:

1. validates the canonical project/repository relationship and optional
   expected source commit;
2. strictly parses security flags, Web bounds, body and timeout limits, lock
   and recovery bounds, provider token limits, and the finite P1.2 process
   profile table;
3. derives the P0 project namespace and state root without allowing model,
   client, or provider payloads to override security settings;
4. performs bounded no-follow validation of model/provider configuration,
   memory metadata, checkpoints, idempotency records, recovery state, locks,
   the provenance ledger, and provenance outbox;
5. evaluates the public-only P1.3 anchor configuration; and
6. only after read-only checks succeed, runs a bounded atomic
   write/read/lock/cleanup availability probe.

Blocked or manual-review states keep state-changing execution and the Web
listener disabled. Diagnostics remain available. Current provider profiles do
not grant provider-call authority through preflight.

Anchor configuration is all-or-none: anchor archive path, public registry, and
an independently retained root fingerprint. A private signing key is neither
accepted nor required for verification. The exact distinctions are:

- no anchor configuration: `ANCHOR_NOT_CONFIGURED` and
  `READY_DEGRADED`;
- current valid anchor: `ANCHOR_VALID`;
- valid historical anchor: `ANCHOR_STALE` and `READY_DEGRADED`;
- partial configuration: blocked configuration; and
- invalid signature, ledger mismatch, unknown key, unsupported schema, or
  unavailable crypto for a configured anchor: `BLOCKED_PROVENANCE`.

An absent or stale anchor is therefore never called valid. It is an explicit
degraded local policy that may still allow local state changes. A configured
invalid or unknown-key anchor blocks activation.

### P2.1 limits

The reported source commit is local `HEAD` identity. It is not, by itself, a
clean-tree or source-content attestation unless the caller supplies and the
preflight matches an expected commit. Preflight establishes startup
coherence, not perfect state correctness, malware detection, or hostile-host
resistance.

## P2.2 Verified Local Backup and Restore

P2.2 defines the deterministic manifest `AOIA_STATE_BACKUP_1A` and exact
verification results `BACKUP_VALID`, `BACKUP_CORRUPT`,
`BACKUP_INCOMPLETE`, `BACKUP_SCHEMA_UNSUPPORTED`, and
`BACKUP_PROJECT_MISMATCH`. Restore reports `RESTORE_VALIDATED`,
`RESTORE_MANUAL_REVIEW_REQUIRED`, or `RESTORE_REJECTED`.

### Explicit resource policy

The backup is not a blind state-directory archive.

| Classification | Resources |
| --- | --- |
| `REQUIRED_FOR_RECOVERY` | task checkpoints, idempotency records, runtime provenance and outbox, and configured public anchor/rotation evidence |
| `OPTIONAL_REBUILDABLE` | legacy provenance and strict non-secret model/provider configuration |
| `CACHE` | runtime logs and browser state |
| `EXCLUDED_SECRET` | agent memory, memory hats, private signing material |
| `EXCLUDED_EPHEMERAL` | state locks, recovery claims, execution locks, temporary and partial files |

The manifest contains a content-derived backup ID, schema and NZ generation,
project identity, the source commit when discoverable (otherwise explicit
null/degraded evidence), sorted portable relative paths, classification, size
and SHA-256 for every payload, provenance count/tip, and the latest configured
public anchor identity. It contains no absolute source paths or private key.

Creation uses an explicit allowlist and bounded same-descriptor reads. It
rejects traversal, backslashes, symlinks, special files, hardlinks, ownership
violations, path/inode swaps, duplicate paths, source mutation, excessive file
counts, and size overflow. Payload files are staged with no-follow exclusive
writes, fsynced, and followed by the canonical manifest. The staging bundle is
self-verified before Linux `renameat2(RENAME_NOREPLACE)` finalization. A
partial staging directory is never a valid backup, and an existing final
bundle is never silently overwritten.

Verification independently checks canonical schema and identity, the exact
file/directory set, hashes and sizes, checkpoint/idempotency schemas,
provenance chain/tip/count, and configured public anchor history using an
independently supplied trust-root fingerprint. It does not invoke
state-mutating store constructors.

Restore first verifies the backup, then rejects the live state root, any
ancestor/descendant overlap, an existing destination, and a foreign project
identity. It copies only to an explicit isolated AOIA-home-shaped destination,
rehashes and revalidates the restored files, runs provenance/state checks, and
runs P2.1 against the final destination before reporting success. It does not
automatically migrate between project identities or overwrite live state.

The offline DR drill constructs controlled local state, appends one synthetic
provenance event, creates and verifies a backup, restores it to a separate
destination, re-verifies it, runs startup preflight, and cleans its scratch
tree. It uses no provider or external service.

### P2.2 limits

Backups are local owner-only plaintext, not encryption, remote backup, WORM
storage, high availability, or remote disaster recovery. Retained checkpoints
and provenance can still be operationally sensitive even though known secret
resources are excluded.

P1.3 ledger identity includes the resolved absolute ledger path. Consequently,
an anchor copied to an isolated restore is verified as historical source
evidence, but cannot be reported as the current anchor for the relocated
ledger. Re-anchoring requires an explicit operator action and an external
private key; restore never does it automatically.

If a post-promotion independent validation fails, the isolated rejected
destination may remain for operator inspection. It is never activated or
reported as a successful restore.

## P2.3 Reproducible Release Manifest and Local Attestation

P2.3 defines `AOIA_RELEASE_MANIFEST_1A` with a deterministic
`AOIA_RELEASE_CORE_1A` and separate metadata. The content-derived release ID
and core hash are stable across different metadata clocks when source,
environment inventory, schemas, and test evidence are unchanged.

### Source and dependency scope

The release builder uses fixed, offline, read-only Git commands through the
P1.2 bounded `GIT` process profile, with a hardened environment,
`shell=False`, and a finite timeout. It requires a clean committed snapshot
and independently binds:

- full source commit and Git tree identity;
- committed blob identity and executable mode;
- per-file size, SHA-256, classification, and an aggregate scope hash;
- runtime, TUI, scripts, build support, tests, data, knowledge, apps, the
  directly served `web/` root, selected root launch/metadata files, and NZ
  architecture documents; and
- configuration, checkpoint, idempotency, provenance, anchor, backup, and
  release schema generations.

Untracked release source, dirty tracked source anywhere in the repository,
skip-worktree/assume-unchanged flags, malformed paths, symlinks, hardlinks,
special files, mode changes, missing files, and source movement fail closed.
Because the local HTTP handler can serve arbitrary files under `web/`, even a
policy-excluded tracked or untracked file beneath that root blocks release
construction rather than being silently omitted.

Explicit path policy excludes recognized credential stores, private-key
forms, runtime state, caches, test/build output, temporary files, and
user/editor metadata. This is a path-policy boundary, not arbitrary secret
content discovery: secret bytes hidden in an innocuously named allowed source
file are not automatically detected.

Dependency evidence is offline and distinguishes
`DECLARED_DEPENDENCY`, `PINNED_DEPENDENCY`, and
`OBSERVED_INSTALLED_DEPENDENCY`. Exact pins are not inferred from ranges.
Declaration file hashes, `requires-python`, Python implementation and patch
version, and the observed installed distribution name/version inventory are
part of the deterministic core. Dynamic dependency declarations that cannot
be reproduced offline fail closed.

### Tests, verification, and signing

The caller supplies bounded test counts plus hashes of failure, error, skip,
and output-log evidence. Counts must be coherent, nonzero, and contain at
least one pass. Evidence is bound to the exact source commit and Git tree.
Nonzero failure/error counts produce
`VERIFIED_WITH_KNOWN_BASELINE_FAILURES`; they are never relabeled green.
Baseline name equality is established separately by the freeze comparison,
not inferred by generic manifest verification.

Verification returns exact states including `RELEASE_VALID`,
`RELEASE_UNSIGNED`, `RELEASE_SOURCE_MISMATCH`,
`RELEASE_FILE_MISMATCH`, `RELEASE_DEPENDENCY_MISMATCH`,
`RELEASE_SCHEMA_UNSUPPORTED`, `RELEASE_INCOMPLETE`,
`RELEASE_SIGNATURE_INVALID`, `RELEASE_UNKNOWN_KEY`, and
`RELEASE_CRYPTO_UNAVAILABLE`. Unsigned valid content is
`RELEASE_UNSIGNED`, never `RELEASE_VALID`.

Optional Ed25519 signing reuses P1.3's external owner-only private-key and
independently pinned public-key registry. Only the active key can sign through
the API; historical keys remain verification keys. The signature covers the
domain-separated deterministic core. No production key is generated, no
release is signed automatically, and nothing is published.

### P2.3 limits

Wall-clock metadata is outside the deterministic signed core and is not a
trusted timestamp. Supplied test-evidence hashes are structurally bound but do
not independently prove that tests were honestly executed. Historical-key
signatures have no trusted-time revocation or freshness claim.

Observed installed dependencies and the Python patch version are host-local;
verification intentionally requires the current local environment to match.
This is local environment attestation, not cross-host bit-for-bit
reproducibility. P2.3 describes and verifies a candidate; it does not package,
deploy, publish, or externally notarize one.

## Trust boundaries

- Operator-owned startup inputs cross into a strict preflight parser. Secret
  references are reported only as presence/classification, never values.
- Mutable local state crosses a read-only bounded validator before any
  startup persistence probe or runtime constructor.
- Live durable state crosses a same-file-descriptor capture boundary into a
  content-addressed local backup. An untrusted backup must pass complete
  verification before any restore write.
- An isolated restore remains untrusted until hashes, state schemas,
  provenance, historical anchor evidence, recovery classification, and
  startup preflight agree.
- Git worktree/index/HEAD state crosses the bounded local Git and pinned-file
  capture boundary into the deterministic release core.
- Test evidence is operator-supplied evidence, not authority and not a remote
  attestation service.
- A release private key crosses only the external key-file-to-Ed25519 signer
  boundary. Public trust still begins with an independently retained root
  fingerprint.
- P0/P1 capability, approval, idempotency, recovery, uncertainty, redaction,
  Web, and process boundaries remain authoritative.

## Verified evidence

The first clean starting-tree full run observed one transient extra P1.2
containment error in
`test_controlled_git_push_1a.ControlledGitPush1ATests.test_non_fast_forward_fails_closed_and_remote_remains_unchanged`:

| Run | Pass | Fail | Error | Skip |
| ---: | ---: | ---: | ---: | ---: |
| 3663 | 3619 | 16 | 24 | 4 |

That test passed 3/3 immediately in isolation. A second full run on the exact
same clean starting commit produced `3663 / 3620 / 16 / 23 / 4` and exactly
matched the P1 freeze failure, error, and skip multisets. The stabilized
starting comparison therefore uses that repeat while preserving the first
observation in this record.

| Gate | Run | Pass | Fail | Error | Skip |
| --- | ---: | ---: | ---: | ---: | ---: |
| P2.1 focused | 42 | 42 | 0 | 0 | 0 |
| P2.2 focused | 20 | 20 | 0 | 0 | 0 |
| P2.3 focused | 25 | 25 | 0 | 0 | 0 |
| Integrated P2 + recovery/idempotency/provenance/outcomes | 184 | 184 | 0 | 0 | 0 |
| Agent D independent negative paths | 18 | 18 | 0 | 0 | 0 |
| Agent E independent invariant matrix | 9 | 9 | 0 | 0 | 0 |
| Final full suite | 3750 | 3707 | 16 | 23 | 4 |

The final integrated log SHA-256 is
`b0786619f4f10df2de5fba0cfd13393aff9efa14ec82a32833d7a18d3b98589c`.
Agent D's captured matrix hash is
`562e105be28996c8a0271323e22d4f1e7a581267716f632861f6dd4d4853cb68`.
Agent E's matrix hash is
`8199921ec06877a2dcb72e6de706c6244dbe393b6f5d00986d1bc30f94e54563`.

Compared with the stabilized starting run, the final suite adds 87 runs and
87 passes. The failure, error, and skip identity multisets are byte-identical
to that baseline: no new names, no removed names, and no unexplained skip
changes. Their SHA-256 hashes are respectively:

- failures:
  `f6ed224cb3cbdeb52b19b676652da1447013aeda17a7c72aa4a9a82c34290d10`;
- errors:
  `6f80522c6ea44eee243fc72a709ea710f57d0b9ee471b027845b96de39dd0502`;
  and
- skips:
  `17e7459d24f86ed7a92c82b4126bd1e0aaaecb2ac3df35a47a705db363291458`.

The final full-output log SHA-256 is
`ccaf5eddc07471fa26b2b9e7fb516a924aa0aa6f2555f5a206137a06963cd3b1`.
`python3 -m compileall -q runtime tests tui scripts` and
`git diff --check` both pass.

A preceding full-suite candidate run found two new failures solely in stale
static allowlists that did not yet name P2.3's bounded Git callsite. The final
freeze updates those two exact test entries. Independent review confirmed the
runtime call still uses the centralized P1.2 boundary, hardened environment,
`GIT` profile, 30-second timeout, and `shell=False`, while raw subprocess
calls remain forbidden. The two affected tests pass 2/2, and the authoritative
full-suite rerun above has no new failure or error identity.

The integrated and independent matrices cover invalid/missing startup
configuration, unsafe tunables, corrupt checkpoints and provenance, absent,
invalid, stale, and unknown-key anchors, manifest/file/anchor tampering,
interrupted backup, restore-to-live and cross-project rejection, isolated
restore, the full DR drill, source/dependency tampering, unsigned truth,
wrong signing trust, credential canaries, restart recovery, idempotency
replay, and unknown outcomes.

## Repository safety at the final gate

- Push attempted: NO.
- Remote refs changed: NO.
- Upstream configured: NO.
- Frozen hackathon, jury, archive, and evidence trees changed: NO.
- External provider/cloud/network operation: NO.
- Real credentials or production signing keys used: NO.
- Scope violations: NO.

The canonical remote-ref fingerprint remains
`4f830bb1a3bfc550e68c1b13e1d1cd848adc7d2817e011eee3d0c7d1d5dcfd70`.

## Guarantees

Within the tested local threat model, NZ Production Readiness v1:

- verifies bounded startup configuration and local state coherence before
  CLI/Web activation;
- exposes degraded, blocked, and manual-review states without false success;
- creates content-addressed allowlisted local backups and validates isolated
  restores before success;
- detects manifest, payload, provenance, anchor, project, and unsafe-path
  mismatches covered by the versioned backup contract; and
- builds and verifies an offline deterministic release core over clean
  committed allowlisted source, dependency declarations and observed local
  environment, schema generations, and supplied test-evidence digests.

## Non-goals and residual limits

NZ Production Readiness v1 does not claim:

- perfect security or protection from a fully compromised host, kernel,
  runtime, trust registry, and keys;
- production HA, multi-host recovery, remote disaster recovery, or
  distributed exactly-once execution;
- automatic deployment, packaging, external publication, WORM retention, or
  trusted external timestamping;
- encrypted backups or availability against deletion;
- hostile-code VM/container isolation;
- automatic anchor freshness after coordinated local rollback;
- proof that supplied test evidence was honestly executed;
- cross-host dependency/environment reproducibility; or
- arbitrary secret discovery by content.

No P3 work is part of this freeze.
