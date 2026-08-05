# NVIDIA Inert Integration Foundation 1A

## Status

This document describes a structural integration boundary. It does not declare
an NVIDIA product integration, runtime capability, compatibility result, or
deployment.

The foundation is disabled by default, local-first, deterministic,
non-authoritative, and fail-closed. Its implementation is isolated in
`runtime/integration_boundaries/nvidia_inert_foundation.py`.

## Purpose

The foundation reserves typed contracts for a possible future NVIDIA advisory
source without connecting AOIA-Core to an SDK, model, endpoint, GPU, process,
tool, filesystem writer, approval path, or ledger writer.

It separates:

- disabled configuration;
- active and deferred capability declarations;
- availability status;
- advisory request structure;
- advisory response structure;
- evidence and provenance metadata;
- fail-closed failure results.

## Trust boundary

NVIDIA remains outside AOIA-Core authority. Any future result must be labelled
`EXTERNAL ADVISORY - NON-AUTHORITY`. It may eventually be reviewed as provider
data, critic metadata, a guardrail suggestion, a policy signal, or evidence
source. It cannot approve, execute, write, mutate the Durable Audit Ledger,
create a Memory Patch, bypass the Global Write Kill-Switch, bypass Workspace
Guard, or activate a capability.

The foundation does not create an `ActionProposal` or an approval. A future
advisory cannot be converted automatically into either object.

## Disabled-by-default behavior

- Missing configuration resolves to `DISABLED`.
- Explicit disabled configuration resolves to `DISABLED`.
- Activation requests, unknown fields, non-empty capability requests, and
  malformed configuration resolve to `BLOCKED_INVALID_CONFIGURATION`.
- Invalid input values are not retained or reflected in failure evidence.
- The inert adapter returns no advisory payload.
- Active external capabilities are always the empty tuple.
- The existing provider registry and provider selector are not modified.

Caller-supplied correlation identifiers, evidence hashes, and deterministic
ticks provide request/provenance binding without clocks, UUID generation, or
ambient environment access.

## Deliberately absent components

This foundation does not include:

- NVIDIA NeMo, NeMo Guardrails, NIM, CUDA, or any NVIDIA SDK;
- model or guardrail runtime;
- local or remote endpoint;
- GPU discovery or access;
- authentication or credential discovery;
- network, socket, subprocess, container, or package-install behavior;
- retry, fallback, streaming, telemetry, or automatic provider selection;
- integration with Memory Patch, CockroachDB, Visual Hub, or image generation.

No external dependency is required.

## Conditions before a real adapter

A real adapter requires a separate production task and separate certification.
At minimum it must define and validate the exact capability, transport,
configuration reference, redaction rules, resource limits, provider gateway,
human-review path, kill-switch precedence, Workspace Guard behavior, ledger
evidence, and rollback boundary. It must not reuse this structural foundation
as activation authority.

## Roadmap relationship

The active repository handoff documents do not assign this work a formal
`Step 18` number. The historical H22 feasibility audit recommended keeping
NVIDIA tooling out of runtime/provider/router/executor code until a separate
integration review. This feature implements only the subsequently authorized
inert boundary and does not rename or renumber the repository roadmap.

The next permitted activity after this candidate is a separate formal
certification of the candidate. A concrete NVIDIA adapter remains deferred.
