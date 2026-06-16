# AOIA-Core UI Threat Model — M6-A Pre-UI Boundary

## Purpose

This threat model describes UI-specific risks before AOIA-Core adds any CLI/TUI/web approval surface. Each threat references UI policy rules and defines impact, mitigation, and status.

## Status Values

- MITIGATED
- OPEN
- DEFERRED

## Threats

### THREAT-UI-01 - Stale path reachability

Threat ID: THREAT-UI-01

Related policy rules: POLICY-01, POLICY-02

Attack vector / failure mode: A future UI handler calls an old non-durable compatibility path or direct artifact writer instead of the 5F gated durable artifact flow.

Impact: Artifact write can occur without full approval/audit gate.

Mitigation: Create UI-safe facade in later milestone. Add static import tests proving web/cli/ui code can only reach approved functions. Add tests proving old non-durable path is not reachable from UI.

Status: OPEN

### THREAT-UI-02 - Auto-approval

Threat ID: THREAT-UI-02

Related policy rules: POLICY-03

Attack vector / failure mode: Button focus, Enter key, form submission, debounce retry, page load event, programmatic click, or default state creates approval without explicit human action.

Impact: Human approval boundary collapses.

Mitigation: Require explicit two-step approve interaction in later UI. Add tests proving render alone and single programmatic click cannot approve.

Status: OPEN

### THREAT-UI-03 - Packet hash hidden or truncated

Threat ID: THREAT-UI-03

Related policy rules: POLICY-04

Attack vector / failure mode: UI design removes or hides packet id/hash for cleaner layout, or truncates hash too aggressively.

Impact: Human cannot verify what is being approved.

Mitigation: DOM tests requiring packet id/hash visible before decision controls become active. Minimum visible hash length: 16 hex chars.

Status: OPEN

### THREAT-UI-04 - Provider output rendered as trusted message

Threat ID: THREAT-UI-04

Related policy rules: POLICY-05, POLICY-06

Attack vector / failure mode: Provider output is styled or positioned like a system/safety message, or provider text injects misleading labels.

Impact: User may treat untrusted model output as authorization, truth, or safety instruction.

Mitigation: Provider output must be wrapped in future ProviderOutputRecord with trust_level="UNTRUSTED". UI must inject trust labels outside provider-controlled content.

Status: DEFERRED

### THREAT-UI-05 - Hidden provider/model switch

Threat ID: THREAT-UI-05

Related policy rules: POLICY-05, POLICY-06, POLICY-14

Attack vector / failure mode: Selected provider/model changes silently through UI state, default settings, reload, or previous session state.

Impact: Audit provenance becomes unreliable; user may not know which model influenced output.

Mitigation: Future ProviderConfigChangeEvent must be audited before any call under new configuration. UI must display selected provider/model.

Status: DEFERRED

### THREAT-UI-06 - Knowledge hat treated as truth authority

Threat ID: THREAT-UI-06

Related policy rules: POLICY-07, POLICY-15

Attack vector / failure mode: Hat output or hat validation badge is treated as proof, truth, execution authority, or approval.

Impact: Knowledge overlay bypasses evidence/provenance and human decision.

Mitigation: HatDisplayRecord and HatSelectionEvent later. Hats may only provide retrieval/prompt-shaping/review enrichment. Hat context must be labeled separately from provider output and approval decisions.

Status: DEFERRED

### THREAT-UI-07 - CPT auto-send

Threat ID: THREAT-UI-07

Related policy rules: POLICY-08, POLICY-13

Attack vector / failure mode: CPT transform completion automatically sends a transformed prompt to a provider, queue, or packet generator.

Impact: Draft content becomes action-driving without explicit human review.

Mitigation: CPT output must be DRAFT/NOT_SENT/UNTRUSTED. Add tests proving transform does not create ApprovalDecision, does not call provider, and cannot auto-send.

Status: DEFERRED

### THREAT-UI-08 - Secrets/API key leakage

Threat ID: THREAT-UI-08

Related policy rules: POLICY-05, POLICY-06

Attack vector / failure mode: API key or provider secret is rendered in DOM, stored in localStorage/sessionStorage, logged in browser history, written to audit logs, or exposed in error messages.

Impact: Credential compromise.

Mitigation: No provider/key UI until provider safety policy. Future secrets boundary must be separate from runtime controls and must not allow read-back of secret values.

Status: DEFERRED

### THREAT-UI-09 - Web UI exposed beyond localhost

Threat ID: THREAT-UI-09

Related policy rules: POLICY-10

Attack vector / failure mode: Developer binds web UI to 0.0.0.0 or LAN address during testing.

Impact: Approval surface may be reachable by other devices, browser extensions, or hostile local network actors.

Mitigation: Default bind to 127.0.0.1. Add startup warning and tests for binding behavior before web UI approval surface ships.

Status: DEFERRED

### THREAT-UI-10 - Audit handoff failure shown as success

Threat ID: THREAT-UI-10

Related policy rules: POLICY-11

Attack vector / failure mode: UI swallows audit error, mismatch, forged handoff, missing handoff, or exception and displays success/neutral state.

Impact: User believes artifact write was correctly gated when it was not.

Mitigation: UI must render explicit failure state and block artifact writes. Tests must simulate mismatch/missing/forged handoff.

Status: OPEN

### THREAT-UI-11 - REJECT still writes artifact

Threat ID: THREAT-UI-11

Related policy rules: POLICY-12

Attack vector / failure mode: Reject path still triggers partial write, temporary write, cache write, preview write, or retry write.

Impact: Reject no longer means block.

Mitigation: Test REJECT path end-to-end. Assert no workspace artifact, temp file, cache file, or partial output is created.

Status: OPEN

### THREAT-UI-12 - Emergency stop reset or bypass

Threat ID: THREAT-UI-12

Related policy rules: POLICY-09

Attack vector / failure mode: Emergency stop flag is reset by reload, rerender, exception recovery, new component state, or user action inside same session.

Impact: Emergency stop gives false sense of control.

Mitigation: Future emergency stop must be session-level fail-closed flag. Add tests proving it blocks subsequent artifact writes and provider calls for remainder of session.

Status: DEFERRED

### THREAT-UI-13 - UI becomes generic chatbot too early

Threat ID: THREAT-UI-13

Related policy rules: POLICY-13

Attack vector / failure mode: First UI adds composer/chat/provider send button before approval surface is proven.

Impact: AOIA becomes uncontrolled assistant interface and loses its review-first safety purpose.

Mitigation: First interactive milestones must be approval/review-only. Chat/composer enters only after provider policy, UI-safe facade, and approval tests exist.

Status: OPEN

### THREAT-UI-14 - Geometry/tetrahedral hat model becomes fake authority

Threat ID: THREAT-UI-14

Related policy rules: POLICY-15, POLICY-07

Attack vector / failure mode: Future geometry/tetrahedral hat model is treated as proof, compression magic, truth structure, or execution authority before audit/schema validation.

Impact: Metaphor contaminates runtime authority and reviewer trust.

Mitigation: Keep tetrahedral hat model research-only until separate audit and schema milestone. It must not affect approval, execution, provider trust, or artifact writes.

Status: DEFERRED
