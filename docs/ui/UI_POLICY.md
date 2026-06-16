# AOIA-Core UI Policy — M6-A Pre-UI Boundary

## Purpose

AOIA-Core must not become an uncontrolled chatbot, unchecked tool runner, or UI bypass around the 5A–5F approval foundation. The first UI/CLI/TUI/web surfaces must be review-packet-first and must not authorize execution, artifact writes, provider calls, or knowledge canonicalization outside the approved gates.

## Scope

This policy defines the pre-UI boundary for future CLI, TUI, web, and other interactive approval surfaces. It does not approve UI implementation, runtime changes, provider calls, shell execution, database persistence, browser automation, or new artifact-writing paths.

## Policy Rules

### POLICY-01 - UI-safe facade only

The UI layer, CLI layer, TUI layer, and future web approval surface may only call runtime functions through an explicit UI-safe facade once that facade exists.

Until the facade exists, no new interactive surface may import runtime internals directly.

Consequence of violation: hard stop.

### POLICY-02 - Artifact writes only through gated durable approval flow

Artifact writes must only happen through the approved 5F gated durable artifact flow.

A UI must never directly call artifact write functions, old non-durable compatibility paths, or filesystem write helpers.

Required chain:

```text
HumanApprovalReviewPacket -> HumanDecisionCapture -> ApprovalDecision -> durable ApprovalDecision audit handoff -> evaluate_pre_artifact_approval_gate(...) -> gated durable artifact write
```

Consequence of violation: hard stop.

### POLICY-03 - Explicit human action required

Approval requires explicit user-initiated action.

Forbidden:

- auto-approval
- default approve button focus
- approval on page load
- approval by retry loop
- approval by provider/model output
- approval by CPT output
- approval by knowledge hat output
- approval through hidden keyboard shortcut

Consequence of violation: hard stop.

### POLICY-04 - Packet id/hash must be visible

Any approval or review surface must display:

- packet id
- packet hash
- decision status
- source/action summary

The hash must not be hidden. It must not be removed for cleaner design. It must not be truncated below 16 hex characters.

Consequence of violation: hard stop.

### POLICY-05 - Provider/network calls disabled by default

Provider/API/network calls remain disabled until a separate provider safety policy exists and is reviewed.

UI must not add:

- fetch requests
- httpx
- aiohttp
- urllib
- network paths
- SDK calls
- hidden provider/model calls

Consequence of violation: hard stop.

### POLICY-06 - Provider output is always UNTRUSTED

When provider output exists in a future milestone, it must be marked UNTRUSTED at the data layer before rendering.

Provider output must never:

- approve
- execute
- write artifacts
- canonicalize knowledge
- bypass review
- mutate ApprovalDecision
- style itself as a system/safety message

Consequence of violation: hard stop.

### POLICY-07 - Knowledge hats are not authority

Knowledge hats / knowledge overlays may provide retrieval context, prompt shaping, or review packet enrichment only after later approved milestones.

Knowledge hats must never:

- grant execution authority
- grant approval authority
- be treated as truth
- canonicalize provider output
- override evidence/provenance
- bypass 5F

In the first UI surface, hats may be read-only metadata only, if included at all.

Consequence of violation: hard stop.

### POLICY-08 - CPT output is draft only

Critic Prompt Transformer output must be treated as:

- DRAFT
- NOT_SENT
- UNTRUSTED
- HUMAN REVIEW REQUIRED

CPT must not auto-send. CPT must not call providers while provider calls are disabled. CPT output must not become an ApprovalDecision without explicit human promotion into a review packet.

Consequence of violation: hard stop.

### POLICY-09 - Emergency stop must fail closed

A future emergency stop / local lockout must block all artifact writes and provider calls for the rest of the session.

It must not be silently reset by rerender, reload, exception handling, or retry logic.

Consequence of violation: hard stop.

### POLICY-10 - Web UI localhost-only by default

Any future web approval UI must bind to:

```text
127.0.0.1
```

by default.

Binding to:

- 0.0.0.0
- LAN address
- public address

requires explicit documented user configuration and a visible startup warning.

Consequence of violation: hard stop.

### POLICY-11 - Audit failures must be visible and blocking

Audit handoff failure, mismatch, missing handoff, forged handoff, or hash mismatch must block artifact write and show explicit failure state.

UI must never show audit failure as success, neutral, or warning-only.

Consequence of violation: hard stop.

### POLICY-12 - REJECT must block all artifact writes

A REJECT decision must block artifact write completely.

Forbidden:

- partial write
- temp write
- cache write
- preview write that modifies workspace
- background write
- retry write

Consequence of violation: hard stop.

### POLICY-13 - UI must not become a generic assistant first

The first interactive surface must be review-first.

Forbidden in first interactive milestone:

- general chat/composer
- functional provider picker
- functional model picker
- functional knowledge hat switching
- CPT auto-send
- tool execution
- browser automation
- shell execution

Consequence of violation: milestone block.

### POLICY-14 - Safety indicators must be visible

Future UI must visibly show important runtime status such as:

- LOCAL-ONLY
- PROVIDER DISABLED / PROVIDER ENABLED
- OUTPUT UNTRUSTED
- APPROVAL REQUIRED
- ARTIFACT WRITE GATED
- selected provider/model if any
- selected hat if any
- last audit event hash if available

The first UI does not need all advanced indicators, but packet id/hash and approval/audit status are mandatory.

### POLICY-15 - Geometry / tetrahedral hat model is research-only for now

The proposed tetrahedral / four-triangle knowledge-hat model is research-only until separately audited.

It must not affect:

- ApprovalDecision
- artifact write gating
- execution authority
- truth/canonicalization
- provider trust
- runtime permission

Any future geometry/tetrahedral hat structure must enter through a separate architecture audit and schema milestone.
