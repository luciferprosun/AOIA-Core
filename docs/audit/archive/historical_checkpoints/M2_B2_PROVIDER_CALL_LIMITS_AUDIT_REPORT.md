# M2-B2 Provider Call Limits Audit Report

Date: 2026-06-12

Branch: `feature/m2-b0-provider-critic-inert-core`

## Summary

M2-B2 implemented local-only provider call ceiling helpers and blocked provider attempt audit records.

Defaults allow zero provider calls. No live provider call was added. No API key loading was added. No network or provider SDK import was added.

## Safety Boundary

- Provider call budgets default to zero calls, zero tokens, zero input characters, and zero cost.
- Provider call limit checks block by default and raise before any provider capability exists.
- Blocked call accounting increments local attempted and blocked counters only.
- Provider attempt audit records are serializable local dataclasses.
- Attempt audit records redact synthetic provider secrets and store request hashes instead of request text.
- Provider output remains `UNTRUSTED` under M2-B0.
- Gateway remains blocked by default under M2-B1.

## Out Of Scope

- No Gemini/GPT integration.
- No provider networking.
- No GCP/cloud change.
- No shell, browser, git, or filesystem capability.
- No Evidence Memory write path.
- No canonical promotion, action approval, or execution path.

## Validation

Intended validation:

```bash
python3 -m compileall -q runtime tests
python3 -m unittest tests.test_m2_b0_provider_critic_inert_core -v
python3 -m unittest tests.test_m2_b1_provider_gateway_redaction -v
python3 -m unittest tests.test_m2_b2_provider_call_limits_audit -v
python3 -m unittest discover -s tests
node --check web/app.js
git diff --check
git status -sb
```

## Next Step

M2-B3 should add the CPT no-auto-send boundary or the Evidence Memory intake boundary, still with no live provider call.
