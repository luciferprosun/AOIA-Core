# AOIA Constraints

These constraints are locked for the AOIA foundation. Any change requires an
ADR and explicit review.

## Stateless Router

Definition: The router must not store request history or mutate internal state
between requests.

Rationale: Stateless behavior keeps outputs reproducible and debugging simple.

Violation consequences: Runtime behavior can become order-dependent and hard to
test.

## Immutable Runtime Config

Definition: Configuration is loaded at startup, validated once, and treated as
read-only during runtime.

Rationale: Static configuration prevents hidden behavior changes while requests
are being processed.

Violation consequences: Routing decisions may differ during the same process
without a code or config restart boundary.

## Three Depth Limit

Definition: AOIA supports exactly three routing depths: LOCAL, MID, and PREMIUM.

Rationale: A small fixed set keeps decisions understandable and testable.

Violation consequences: Extra depths increase policy ambiguity and make
determinism harder to verify.

## Deterministic Routing

Definition: The same input and validated configuration must always return the
same routing result.

Rationale: AOIA is a request-routing component, not an adaptive runtime.

Violation consequences: Users cannot reproduce, audit, or confidently test
routing behavior.

## No Runtime Learning

Definition: AOIA must not learn from requests, update models, tune weights, or
modify rules during runtime.

Rationale: Runtime learning would break immutable configuration and stateless
routing.

Violation consequences: The system becomes non-reproducible and may drift from
documented behavior.

## Fail-Fast Behavior

Definition: Invalid input, invalid config, and unsupported states must fail
immediately with clear errors.

Rationale: Early failure is easier to debug than silent fallback behavior.

Violation consequences: Bad states may propagate into execution paths and hide
configuration defects.

## No Autonomous Adaptation

Definition: AOIA must not independently change providers, schedules, policies,
or routing rules at runtime.

Rationale: Routing behavior must remain explicit and governed by static rules.

Violation consequences: The system can start acting outside documented operator
intent.

## Request-Routing Only

Definition: AOIA classifies requests into routing depths and does not execute
shell commands, call providers, or perform side effects by itself.

Rationale: Keeping classification separate from execution limits blast radius.

Violation consequences: Router defects could trigger unintended actions.

## Local-First Default

Definition: AOIA must prefer local configuration, local validation, and local
knowledge before external dependency paths are considered.

Rationale: Local-first behavior improves reproducibility, privacy, and offline
operation.

Violation consequences: Routine requests may become unnecessarily dependent on
network state or third-party services.

## Lightweight Foundation

Definition: AOIA additions must stay small, readable, and dependency-minimal
unless a later ADR justifies expansion.

Rationale: The architecture should grow through controlled modules, not broad
redesigns.

Violation consequences: Maintenance cost grows faster than verified capability.
