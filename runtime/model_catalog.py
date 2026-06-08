from __future__ import annotations

from dataclasses import asdict

try:
    from runtime.schemas.model_router import (
        ModelCatalogEntry,
        ProviderClass,
        RoutingDecisionStatus,
        TrustLevel,
    )
except ModuleNotFoundError:  # pragma: no cover - script launch path
    from schemas.model_router import (
        ModelCatalogEntry,
        ProviderClass,
        RoutingDecisionStatus,
        TrustLevel,
    )


CATALOG_NOTICE = "Preview only - no provider calls. Human approval required before any future provider call."


def get_static_model_catalog() -> tuple[ModelCatalogEntry, ...]:
    """Return local model/provider catalog preview entries.

    The catalog is static metadata only. It does not check keys, call providers,
    execute health checks, select routes, or perform fallback.
    """
    return (
        ModelCatalogEntry(
            model_id="gemini/gemini-2.5-flash",
            display_name="Gemini 2.5 Flash",
            provider_id="gemini",
            provider_class=ProviderClass.GEMINI,
            trust_level=TrustLevel.THIRD_PARTY_PAID,
            paid_tier=True,
            notes=(
                "Remote Google provider.",
                "Requires human approval before any future call.",
                "Not for secret-bearing prompts.",
            ),
        ),
        ModelCatalogEntry(
            model_id="openrouter/google/gemma-3-27b-it",
            display_name="Gemma 3 27B via OpenRouter",
            provider_id="openrouter",
            provider_class=ProviderClass.OPENROUTER,
            trust_level=TrustLevel.THIRD_PARTY_PAID,
            paid_tier=True,
            notes=(
                "Remote OpenRouter gateway route.",
                "Provider and model identity must remain visible.",
                "No automatic fallback.",
            ),
        ),
        ModelCatalogEntry(
            model_id="openrouter/free",
            display_name="OpenRouter free model route",
            provider_id="openrouter",
            provider_class=ProviderClass.OPENROUTER_FREE,
            trust_level=TrustLevel.THIRD_PARTY_FREE,
            free_tier=True,
            notes=(
                "Development-only preview route.",
                "Never for sensitive, core, or canonical tasks.",
                "Free cost is not a safety guarantee.",
            ),
        ),
        ModelCatalogEntry(
            model_id="local/manual-model",
            display_name="Local model placeholder",
            provider_id="local",
            provider_class=ProviderClass.LOCAL_MODEL,
            trust_level=TrustLevel.LOCAL_ONLY,
            notes=(
                "Local-only placeholder for future manual model catalog work.",
                "Not wired to execution.",
                "No provider call path exists here.",
            ),
        ),
        ModelCatalogEntry(
            model_id="disabled/unknown-provider",
            display_name="Disabled or unknown provider",
            provider_id="disabled",
            provider_class=ProviderClass.DISABLED,
            trust_level=TrustLevel.UNKNOWN,
            notes=(
                "Blocked until reviewed.",
                "Unknown cost, provider, retention, or trust status defaults to disabled.",
            ),
        ),
    )


def get_static_model_catalog_payload() -> dict[str, object]:
    return {
        "notice": CATALOG_NOTICE,
        "status": RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL.value,
        "provider_call_permitted": False,
        "automatic_fallback_permitted": False,
        "health_check_permitted": False,
        "canonical_promotion_permitted": False,
        "models": [_catalog_entry_to_dict(entry) for entry in get_static_model_catalog()],
    }


def _catalog_entry_to_dict(entry: ModelCatalogEntry) -> dict[str, object]:
    payload = asdict(entry)
    payload["provider_class"] = entry.provider_class.value
    payload["trust_level"] = entry.trust_level.value
    payload["notes"] = list(entry.notes)
    return payload
