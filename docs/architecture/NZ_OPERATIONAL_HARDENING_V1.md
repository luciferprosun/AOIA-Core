# NZ Operational Hardening v1

Status: full-suite-validated local freeze record on 2026-08-21. This file is
committed by the local `nz: freeze operational hardening architecture` commit.

This document records the implemented boundary of NZ Foundation v1 and NZ
Operational Hardening v1. It is an architecture freeze, not a claim of perfect
security, high availability, or protection from a fully compromised host.

## Scope

The frozen scope is the local AOIA runtime in this repository. It covers local
filesystem state, bounded child-process execution, explicit runtime outcomes,
the authenticated local operator HTTP service, sensitive-output projection,
and an optional offline signature layer over the P0.8 provenance ledger.

The integration started at
`4393f90b7f329d2c42e87de893f41d23105380a6` on the local branch
`nz/p1-operational-hardening`. No deployment, cloud operation, provider call,
remote publication, or real-key provisioning is part of this freeze.

## NZ Foundation v1

| Phase | Implemented boundary |
| --- | --- |
| P0.1 | Resolves and fences permitted filesystem roots; rejects traversal and unsafe path substitution. |
| P0.2 | Constructs explicit sanitized child environments rather than inheriting arbitrary ambient state. |
| P0.3 | Keeps capability and approval policy separate from model/provider output; metadata is not authority. |
| P0.4 | Gives controlled subprocess execution a finite timeout and explicit timeout behavior. |
| P0.5 | Correlates request, trace, task, action, and operation identities without accepting client identity as authority. |
| P0.6 | Uses locked, pinned, atomic persistence for runtime state. |
| P0.7 | Uses durable action idempotency records and refuses unsafe redispatch after uncertain effects. |
| P0.8 | Maintains and verifies the canonical local hash-chained provenance ledger. |
| P0.9 | Persists durable task checkpoints and task budgets. |
| P0.10 | Reconciles restart recovery and fails closed on ambiguous or conflicting evidence. |
| P0.11 | Exposes explicit terminal and non-terminal outcomes, including timeout, cancellation, malformed response, and unknown outcome. |
| P0.12 | Protects the local Web/API boundary with bearer authentication, strict JSON framing, body limits, origin policy, safe errors, and single-operator mutation serialization. |
| P0.13 | Redacts registered secret values and sensitive structured fields before model, console, HTTP, and persistence projections while preserving canonical P0.7/P0.8 hashes. |

These phases remain the authority foundation. P1 adds operational resource and
evidence controls; it does not replace or redesign P0.

## P1.1 Web Resource Governance

The local HTTP server now uses finite request and operation executors instead
of unbounded per-request threads. The default request policy is:

- 8 simultaneously executing requests, 16 queued requests, and a listen
  backlog of 16;
- at most 4 admitted (queued or running) requests per client-host-derived key;
- 5-second header, 15-second body, and 5-second write timeouts;
- a 120-second acceptance-to-response request lifecycle deadline;
- monotonic token buckets with a 60-second window: 120 health requests, 120
  authenticated reads, and 30 authenticated mutations;
- at most 256 limiter entries, automatically expired after 120 seconds; and
- one mutation executing at a time through the existing single-operator lock.

Client keys are SHA-256 hashes of the accepted socket's host/IP, not bearer
tokens or forwarded headers. Admission, queue, per-client, and rate-limit
exhaustion return bounded safe envelopes such as `WEB_SERVER_BUSY` or
`WEB_RATE_LIMITED`; they are not silently dropped. Header/body stalls return
safe timeout results.

The wall-clock deadline includes request queue time. Work that has not crossed
the mutation dispatch gate can be cancelled with a definite timeout. If a
mutation has already started and cannot safely be stopped, the HTTP response is
truthfully `UNKNOWN_OUTCOME`; the operation permit remains held until the work
actually exits, and late work cannot write a second HTTP response.

Authentication, origin validation, JSON framing, safe errors, and P0.13
redaction remain in force. Operator-token rotation intentionally remains
restart-only. A live reload mechanism was not added because the current token
source is process configuration and introducing a second secret lifecycle
would broaden the P0.12 trust boundary.

## P1.2 Process Resource Containment

All active Python runtime subprocess callsites use the centralized boundary and
select one finite profile: `CONTROLLED_TEST`, `GIT`, `PDF`, `PACKAGE`,
`SCEMDA`, or `INTERNAL_UTILITY`. Profiles bound relevant CPU time, address
space, sampled tree memory, open files, task count, file size where safe, and
captured output. Git intentionally has no `RLIMIT_FSIZE` because applying it to
repository/index/pack writes could corrupt repository state; its captured
stdout and stderr remain bounded.

On supported Linux hosts a small single-threaded supervisor:

1. becomes a child subreaper;
2. starts the supervisor in a fresh session and places the target in its own
   process group inside that session, without Python `preexec_fn`;
3. applies `RLIMIT_CPU`, `RLIMIT_AS`, `RLIMIT_NOFILE`, `RLIMIT_NPROC`,
   `RLIMIT_FSIZE` when selected, and `RLIMIT_CORE=0` before exec;
4. tracks processes by PID plus start time and uses pidfds where available;
5. monitors sampled aggregate RSS and live task count; and
6. on timeout or cancellation sends TERM, waits a bounded grace interval,
   freezes and rescans, escalates to KILL, and reaps the owned tree.

The boundary owns a separate cancellation pipe and bounded input/output
collectors. Invalid, missing, truncated, reordered, or inconsistent supervisor
reports fail closed. Explicit reasons include `PROCESS_CPU_LIMIT`,
`PROCESS_MEMORY_LIMIT`, `PROCESS_FILE_LIMIT`, `PROCESS_COUNT_LIMIT`,
`PROCESS_TREE_TERMINATED`, `PROCESS_CONTAINMENT_SETUP_FAILED`, and
`PROCESS_CONTAINMENT_LOST`. P0.11 maps an ordinary hard timeout to `TIMEOUT`, a
proven pre-dispatch cancellation to `CANCELLED`, and CPU/memory/file/count/tree
or lost-containment uncertainty to `UNKNOWN_OUTCOME`. A proven pre-dispatch
`PROCESS_CONTAINMENT_SETUP_FAILED` is `FAILED`. P0.7 therefore does not silently
replay a possibly effectful action.

This is not a container or kernel-enforced aggregate control plane. It requires
Linux `/proc`. `RLIMIT_NPROC` is a per-real-UID backstop, not a per-tree quota;
aggregate RSS/task checks are sampled. Without a delegated cgroup, PID
namespace, or seccomp boundary, a deliberately hostile same-UID child can kill
the supervisor after detaching. That case is unsupported and returns
`PROCESS_CONTAINMENT_LOST`/`UNKNOWN_OUTCOME`, never success, but complete
descendant reclamation cannot be guaranteed. Profiles are finite defaults and
may require reviewed host-specific tuning.

## P1.3 Trusted Local Provenance Anchor

P1.3 adds an optional local/offline Ed25519 signature layer over canonical P0.8
ledger checkpoints. It is evidence only: anchors do not approve actions, alter
idempotency, authorize recovery, or establish task success.

### Keys and trust

- The signing key is an explicitly supplied PKCS#8 Ed25519 private-key file
  outside the repository, project state, ledger, anchor archive, and public-key
  registry.
- The key file must be a unique owner-only regular file (`0600`) under an
  owner-only directory; reads are no-follow and inode-bound.
- The verifier requires an independently retained root public-key fingerprint.
  It never treats a public key embedded in an anchor as a trust root.
- Public keys and dual-signed rotation records are immutable. Rotation requires
  authorization by the old key and proof of possession by the new key. Old
  anchors remain verifiable, while retired keys cannot sign the current tip.

The implementation uses the locally installed `cryptography` Ed25519 backend
(41.0.7 on the verified host). The project currently declares no Python
dependencies; a host without that backend fails explicitly with
`ANCHOR_CRYPTO_UNAVAILABLE`. No fallback algorithm or OpenSSL subprocess is
used. No operator/private key or production anchor was created during this
run; tests used ephemeral synthetic fixtures only.

### Anchor and verification

Each signed anchor binds an exact schema version, random anchor ID, monotonic
anchor sequence, prior-anchor hash, local timestamp, project identity, resolved
ledger identity, latest entry hash, entry count, P0.8 schema generation,
signature algorithm, public-key fingerprint, and Ed25519 signature.

Creation is serialized and ordered as follows:

1. validate and serialize registry, anchor-creation, and canonical P0.8 ledger
   state under their stable locks;
2. verify the complete P0.8 chain and compare the previous signed ledger prefix;
3. derive the current tip/count and canonical signed archive tip;
4. construct and sign the canonical domain-separated payload;
5. pin the atomic-write target directories and persist an immutable archive
   record;
6. re-read and verify the signature; and
7. atomically advance the latest pointer.

Offline verification checks the complete P0.8 chain, exact bounded schemas,
project and ledger identity, archive sequence/parent hashes, trusted-key
rotation, signature, fingerprint, and the ledger hash at the recorded count.
The first anchor attests the then-current self-consistent P0.8 chain; continuity
against a prior trusted history begins once a retained anchor lineage exists.
Appending ledger entries after an anchor keeps that anchor valid as a
historical checkpoint (`is_current=false`). Rewriting or truncating the
anchored prefix is `ANCHOR_LEDGER_MISMATCH`. Other exact results include
`ANCHOR_VALID`, `ANCHOR_SIGNATURE_INVALID`, `ANCHOR_UNKNOWN_KEY`,
`ANCHOR_SCHEMA_UNSUPPORTED`, and `ANCHOR_CRYPTO_UNAVAILABLE`.

The local archive is bounded at 4096 anchors and the key registry at 128
generations; exhaustion fails closed and requires an explicit rollover design.
Ledger identity includes the resolved absolute path, so relocation requires a
reviewed new trust lineage.

### P1.3 freshness limit

Ed25519 authenticates retained content; it does not independently prove
freshness. If an attacker coherently rolls back the ledger, deletes every newer
anchor archive record, restores the matching pointer and registry state, and no
separate trusted latest sequence/hash was retained, an older legitimately
signed checkpoint can verify as current. Detecting that attack requires an
operator-retained freshness checkpoint, WORM/HSM storage, or an external
witness. None is created automatically here.

## Trust boundaries

- Human approval and hash-bound runtime policy remain the execution-authority
  boundary. Provider/model output, web input, critic results, and anchors are
  not authority.
- The local HTTP socket is untrusted input until P0.12 authentication and
  framing, then P1.1 admission and lifecycle controls.
- Child code is untrusted relative to the P1.2 supervisor, but shares the host
  UID and kernel; unsupported supervisor destruction is fail-closed, not
  magically contained.
- The P0.8 ledger is mutable local evidence. P1.3 trusts only a valid chain
  relative to retained signed anchors, an independently retained root pin, and
  the local code/host assumptions.
- The external signing key crosses only the local key-file-to-Ed25519 signer
  boundary. It must not enter logs, provenance, model context, HTTP, or source.

## Verified evidence

The authoritative pre-edit baseline was:

| Gate | Run | Pass | Fail | Error | Skip |
| --- | ---: | ---: | ---: | ---: | ---: |
| Starting full suite | 3587 | 3544 | 16 | 23 | 4 |
| P1.1 focused | 19 | 19 | 0 | 0 | 0 |
| P1.2 focused | 31 | 31 | 0 | 0 | 0 |
| P1.3 focused | 24 | 24 | 0 | 0 | 0 |
| Integrated negative-path matrix | 181 | 181 | 0 | 0 | 0 |
| Final full suite | 3663 | 3620 | 16 | 23 | 4 |

Compared with the starting suite, the final run adds 76 runs and 76 passes.
The sorted failure-name, error-name, and skip-name multisets are byte-identical
to the baseline: 0 new failure names, 0 new error names, and 0 changed skip
names. Their SHA-256 hashes remain respectively
`f6ed224cb3cbdeb52b19b676652da1447013aeda17a7c72aa4a9a82c34290d10`,
`6f80522c6ea44eee243fc72a709ea710f57d0b9ee471b027845b96de39dd0502`,
and `17e7459d24f86ed7a92c82b4126bd1e0aaaecb2ac3df35a47a705db363291458`.
The final full-output log hash is
`5e62ba41f03179cf8b20018802401bec53754e702c1eff0d4192787b787887e9`.

The integrated matrix covered unauthenticated and wrongly authenticated HTTP,
queue/concurrency/rate exhaustion, limiter expiry, slow headers, stalled
bodies, request deadlines, process timeouts/cancellation/tree cleanup,
CPU/RSS/FD/file/task limits, explicit containment loss, ledger and anchor
tampering, wrong trust pins, rotation, redaction canaries, recovery,
idempotency replay, and unknown outcomes. It found no surviving synthetic
supervisor/child process and no canary in captured evidence.

## Commit lineage

The relevant first-parent lineage is:

| Boundary | Commit |
| --- | --- |
| P0.1 | `4ec0a88ac00b2bfc7c9c13a79280c73c2895a8bb` |
| P0.2 | `4fb7e3abbc3e7473a2cefa65fd699e3ed73fe68b` |
| P0.3 | `172febcc6d2c171d825ced87da0f23b914e0dca5` |
| P0.4 | `93e2a00b4bbdb6ef164277c0096904d3155be4a7` |
| P0.5 | `9f74f1b5842c2f0547c1c5319eb0f48625697807` |
| P0.6 | `ca80a9df059a91c256b943a1f589164cba5959c2` |
| P0.7 | `7e3c601ac34ad1c34c7e7e340a0e8a5abd51d558` |
| P0.8 | `ed1412faca456fd595508037aa2a81a7e92c2e28` |
| P0.9 | `e20545fbb25ea38631fdd4ba1f53703ece19b5a7` |
| P0.10 | `4e11a2566626a00872efc5be34b78ca28060ab60` |
| P0.11 | `43e8cb13f5adf57240221f7cad2c5df18c59c891` |
| P0.12 | `b8a66e5f43fa2968eb4ee3d705dfa8e6ee881385` |
| P0.13 | `3d248e66a4949668803372bc6508a00d871802a2` |
| P0 integration boundary | `4393f90b7f329d2c42e87de893f41d23105380a6` |
| P1.1 | `ab4aec214efde0aa6b8d58ad9f38dfa7e69d4b99` |
| P1.2 | `04e5c271ee30ba20f18cfb22da48c54fd038d5a6` |
| P1.3 | `0ad741d35a0b57206238a9afcee5d3a35e2043cb` |

## Guarantees and non-goals

Within the tested local threat model, NZ provides fail-closed authority checks,
finite HTTP and controlled-process resource boundaries, explicit uncertainty,
durable local state/idempotency/recovery, redacted operational projections,
and offline verification of retained signed provenance checkpoints.

NZ does not guarantee perfect security, distributed exactly-once execution,
multi-host recovery, production HA, availability against deletion, a trusted
timestamp, external notarization, complete anti-rollback freshness, or
protection when an attacker controls the host kernel, runtime code, all data,
all trust records, and all keys. Python cannot guarantee complete private-key
zeroization. A partial first-time trust-root enrollment can fail closed and
require manual repair. P2 is outside this freeze.
