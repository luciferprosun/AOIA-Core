# User-Configured Provider Connections + Orchestra Role Selection + Controlled Live Smoke 1A

## Scope and baseline

This bounded production step starts from
`89e1e0b17694c2f7465702f16cb4fc4f9087de21` and preserves the AUTH identity
repair ancestor `037373f8204533ccdead521df70b4a6f9886db2c`. It adds operator-owned
provider connections, dynamic model profiles, explicit Orchestra role binding,
one exact-model connection test, and one single-use sequential live
demonstration. It does not add autonomous routing, retry, fallback, background
calls, provider tools, execution, write authority, or approval authority.

## Existing provider gateway reuse

- The existing `OpenAICompatibleProvider` and provider gateway remain the only
  OpenAI-compatible network implementation. OpenRouter is a metadata preset for
  its existing endpoint, not a new client.
- Exact Orchestra invocation is a single-attempt path beside the legacy
  fallback flow. It consumes a stage-specific transport receipt and cannot
  select a different connection or model.
- The strict request path rejects redirects and implicit reconnects, applies an
  absolute timeout, bounds response bytes, and accepts only a complete
  `finish_reason` of `stop`.
- Existing deterministic CPT transformation and hash-bound Orchestra run and
  stage contracts are reused. No second critic transformer or provider adapter
  was introduced.

## User configuration and secrets

- A provider connection owns endpoint metadata and one credential reference.
  One connection can own multiple model profiles.
- Model profiles are loaded from the external user store at request time; a
  fixed production catalog is not authoritative for the Orchestra table.
- Default normal state is outside the repository under the isolated project
  path `~/.local/state/aoia/AOIA-Core-<project-path-sha12>/runtime/state/`;
  default credentials are outside the repository under
  `~/.config/aoia/secrets/provider-connections/`.
- Normal configuration stores only the credential reference. Masked
  `configured`/`missing` status is derived for display. Credential values are
  excluded from metadata, canonical hashes, responses, errors, logs, and
  snapshots.
- Metadata mutations are process-serialized. Credentials are published through
  a fresh private inode and atomic replace; unsafe permissions, symlinks,
  hardlinks, and project-contained secret roots fail closed.

## Selection and manual live boundary

The operator selects two to five enabled model profiles and explicitly assigns
`MAIN`, `CRITIC`, `AUDITOR`, or `SYNTHESIZER`. Exactly one `MAIN` and at least
one `CRITIC` or `AUDITOR` are required. A role must be allowed by the selected
model profile. Connection revision, model revision, assignment, selection,
source prompt, run, stage, parent response, and preview hashes remain exact.

A preview is non-authoritative and cannot permit a call. The server retains the
usable preview, requires three exact preview-hash confirmations plus an actual
boolean Run action, and mints one expiring, single-use session. The additional
`AOIA_PROVIDER_CALLS_ENABLED=1` technical switch cannot replace that evidence.
Failures expose the exact failed stage without automatic retry or fallback.

The bounded sequential demonstration supports:

1. one `MAIN` initial response;
2. one or more CPT-derived `CRITIC` calls;
3. an optional `AUDITOR` call over the initial response and critic evidence;
4. an optional `SYNTHESIZER` call producing only a draft for human review.

Every provider response is untrusted and non-authoritative. It cannot approve,
execute, write, mutate a gate, or satisfy a human barrier.

## Operator-only real smoke command

After connections and model profiles have been saved through the local UI, an
operator may deliberately run:

```bash
AOIA_PROVIDER_CALLS_ENABLED=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=runtime:. \
PYTHONNOUSERSITE=1 \
python3 -m runtime.orchestra_live_smoke_cli \
  --prompt-file /absolute/path/to/bounded-prompt.txt \
  --model MAIN_PROFILE_ID=MAIN \
  --model CRITIC_PROFILE_ID=CRITIC \
  --timeout-seconds 10 \
  --maximum-output-tokens 64
```

The command prints the inert preview, then interactively requires the operator
to retype its exact hash and enter `RUN ORCHESTRA`. It never accepts or prints
an API key. No real or paid provider call is part of automated validation.

## Validation record

- New focused feature modules: 139 passed, 0 failed, 0 errors, 0 skipped.
- Provider-pattern regression suite: 167 passed, 0 failed, 0 errors, 0 skipped.
- Existing Epistemic Orchestra regression suite: 90 passed, 0 failed, 0
  errors, 0 skipped.
- Static capability boundary: 50 passed, 0 failed, 0 errors, 0 skipped.
- Complete suite inventory: 3672 discovered; the canonical closure expectation
  is 3668 passed and 4 pre-existing skips, with 0 failures and 0 errors.

Canonical architect-handoff and final-freeze manifests are regenerated only
after this report and all source, UI, and test inputs are final. Their metadata
remains evidence only. Commit and push evidence is reported externally after
validation to avoid circular manifest input.

## Deferred work

`Orchestra Session View + Critic/Audit Result Presentation 1A` is the next exact
step and is not started here.
