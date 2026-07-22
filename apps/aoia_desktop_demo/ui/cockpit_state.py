"""Inert, UI-only state for the desktop cockpit.

This module deliberately has no provider imports and cannot dispatch a model
request. It keeps primary and observer selections and results separate from
the controller that owns the bounded provider workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ..critical_review import ObserverReviewResult

OBSERVER_ROLES = (
    "Logic & Claims",
    "Safety & Authority",
    "Evidence & Consistency",
)


@dataclass
class ObserverSlot:
    role: str
    enabled: bool = False
    provider_id: str = ""
    model_id: str = ""
    state: str = "Not configured"
    result: str = "No review has run. METADATA ONLY — NO AUTHORITY."
    review_result: ObserverReviewResult | None = None

    def is_complete(self, configured_providers: Iterable[str], models: dict[str, tuple[str, ...]]) -> bool:
        return (
            self.enabled
            and self.provider_id in set(configured_providers)
            and self.model_id in models.get(self.provider_id, ())
            and bool(self.role)
        )


@dataclass
class CockpitState:
    """Local UI state with narrowly persisted non-secret operator choices.

    Review results and provider output remain session-only.  Only the fixed
    observer slots' enabled, role, provider, and model selections may be
    exported to the settings layer.
    """

    primary_model_id: str = ""
    observer_slots: list[ObserverSlot] = field(
        default_factory=lambda: [ObserverSlot(role=role) for role in OBSERVER_ROLES]
    )

    def __post_init__(self) -> None:
        if len(self.observer_slots) != 3:
            raise ValueError("The desktop cockpit has exactly three observer slots.")

    def set_primary_model(self, model_id: str) -> None:
        self.primary_model_id = model_id

    def restore_observer_preferences(self, preferences: Iterable[dict[str, object]]) -> None:
        records = tuple(preferences)
        if not records:
            return
        if len(records) != len(self.observer_slots):
            raise ValueError("observer preferences must describe exactly three slots")
        for slot, record in zip(self.observer_slots, records, strict=True):
            slot.enabled = bool(record["enabled"])
            slot.role = str(record["role"])
            slot.provider_id = str(record["provider_id"])
            slot.model_id = str(record["model_id"])
            slot.state = "Ready for manual review" if slot.enabled and slot.provider_id and slot.model_id else "Not configured"

    def observer_preferences(self) -> list[dict[str, object]]:
        return [
            {
                "enabled": slot.enabled,
                "role": slot.role,
                "provider_id": slot.provider_id,
                "model_id": slot.model_id,
            }
            for slot in self.observer_slots
        ]

    def clear_review_results(self) -> None:
        """Clear stale session results after an operator changes routing."""
        for slot in self.observer_slots:
            slot.review_result = None
            slot.state = (
                "Ready for manual review"
                if slot.enabled and slot.provider_id and slot.model_id
                else "Not configured"
            )
            slot.result = "No review has run. METADATA ONLY — NO AUTHORITY."

    def models_for_provider(self, provider_id: str, models: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
        return models.get(provider_id, ())

    def review_status(self, configured_providers: Iterable[str], models: dict[str, tuple[str, ...]]) -> str:
        enabled = [slot for slot in self.observer_slots if slot.enabled]
        if not enabled or any(not slot.is_complete(configured_providers, models) for slot in enabled):
            return "OBSERVER CONFIGURATION INCOMPLETE"
        return "READY FOR MANUAL REVIEW"

    def apply_review_results(self, results: Iterable[ObserverReviewResult]) -> None:
        """Apply each immutable result only to its matching fixed card slot."""
        by_slot = {result.slot_id: result for result in results}
        for index, slot in enumerate(self.observer_slots, start=1):
            result = by_slot.get(f"observer-{index}")
            if result is None:
                continue
            slot.review_result = result
            slot.state = result.execution_status.value
            slot.result = result.concise_summary


def configured_model_ids(
    *,
    provider_id: str,
    saved_model_id: str,
    fetched_model_ids: Iterable[str],
    additional_saved_model_ids: Iterable[str] = (),
) -> dict[str, tuple[str, ...]]:
    """Return only models tied to an actual saved provider connection.

    A manually saved model is valid even before an operator explicitly refreshes
    the provider catalog.  Fetched values are merged, never invented.
    """
    if not provider_id:
        return {}
    values = tuple(
        dict.fromkeys(
            model_id
            for model_id in (saved_model_id, *additional_saved_model_ids, *fetched_model_ids)
            if model_id
        )
    )
    return {provider_id: values} if values else {}
