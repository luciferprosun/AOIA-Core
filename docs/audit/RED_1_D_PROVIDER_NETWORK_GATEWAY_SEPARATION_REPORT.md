# RED-1-D Provider/Network Gateway Separation Report

Date: 2026-06-11

Branch: `feature/red1-d-provider-network-gateway-separation`

Purpose: apply the third targeted RED-1 fix by freezing provider/network-call surfaces from approved runtime/model/public flow.

## Files changed

- `runtime/provider_clients.py`
- `runtime/providers/base.py`
- `runtime/providers/config.py`
- `runtime/providers/openai_compatible.py`
- `runtime/providers/gemini_provider.py`
- `runtime/providers/gemma_provider.py`
- `tests/test_red1_provider_network_gateway_separation.py`
- `docs/audit/RED_1_D_PROVIDER_NETWORK_GATEWAY_SEPARATION_REPORT.md`

## Provider/network surfaces found

- `runtime/provider_clients.py`: one-shot Gemini/OpenRouter call helpers using `urllib.request.urlopen`.
- `runtime/model_router.py`: proposal/approval orchestration for model selection and one selected provider call.
- `runtime/webapp.py`: local API routes for model catalog, provider config status, model-selection proposal, and approve-and-call.
- `runtime/providers/config.py`: legacy `ProviderManager` with fallback routing to Gemini/OpenRouter/xAI/DeepSeek providers.
- `runtime/providers/openai_compatible.py`: OpenAI-compatible HTTP provider client.
- `runtime/providers/gemini_provider.py`: Gemini SDK provider client.
- `runtime/providers/gemma_provider.py`: legacy Gemma provider with local Ollama, Hugging Face, and OpenAI-compatible fallback paths.

## Freeze/separation method used

- Added explicit provider/network markers:
  - `PROVIDER_NETWORK_SURFACE = True`
  - `APPROVED_RUNTIME_PROVIDER_FLOW = False`
  - `PROVIDER_CALLS_FROZEN = True`
- Added default-off provider opt-in:
  - `AOIA_PROVIDER_CALLS_ENABLED`
- Added provider-call guards:
  - `runtime.provider_clients._require_provider_calls_enabled()`
  - `runtime.providers.base.require_provider_calls_enabled()`
- Guarded actual provider/network call paths before `urlopen`, provider SDK calls, and legacy fallback provider generation.
- Kept local config/catalog/proposal-only paths usable when they do not call network.
- Kept CPT transform local and provider-free.

## What remains config-only or preview-only

- `runtime/model_catalog.py` remains static metadata only and does not call providers.
- `runtime/provider_config.py` remains local environment/config status only.
- `/api/model-catalog` remains preview/catalog only.
- `/api/provider-config-status` remains local config status only.
- `/api/cpt/transform` remains local transform only and keeps `provider_call_permitted=False`.
- `/api/model-selection/propose` remains proposal/policy metadata and does not call providers.

## What is now proven

- Provider/network-capable modules carry explicit frozen/not-approved markers.
- Without `AOIA_PROVIDER_CALLS_ENABLED=1`, direct provider client calls are blocked before network.
- Without `AOIA_PROVIDER_CALLS_ENABLED=1`, legacy provider fallback generation is blocked before provider construction/network.
- Local config/catalog/CPT paths remain usable and network-free under patched network primitives.
- Existing RED-1-B, RED-1-C, and RED-1-C2 boundary tests continue to pass after this change.

## What remains unproven

- RED-1 is not closed.
- Provider approved gateway architecture is not fully implemented.
- No ProviderCallProposal exists yet unless already present as inert schema.
- No HumanApprovalDecision is wired to provider execution.
- Public chat/model execution architecture is still legacy/transitional and remains subject to future RED-1 review.
- Shell/executor freeze remains separate work.
- Memory/retrieval and canonical-promotion boundaries still require targeted follow-up.
- UI approval wording and execution separation still need a dedicated pass.

## Remaining RED-1 blockers

- Shell/executor freeze remains open.
- Memory/retrieval and canonical-promotion follow-up remains open.
- UI approval must remain separate from system execution permission.
- No sandbox exists yet.
- No approved model-to-action chain exists.

## Explicit non-claims

- RED-1 is not closed.
- No provider call was added.
- No external API call was made.
- No browser/shell/file/git action was added.
- CPT behavior was not changed.
- This is a freeze/separation, not a provider gateway implementation.

## Recommended next targeted fix

RED-1-E shell/executor freeze.
