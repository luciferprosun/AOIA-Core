from apps.aoia_desktop_demo.ui.cockpit_state import CockpitState, configured_model_ids


def test_catalog_entries_do_not_become_configured_models() -> None:
    assert configured_model_ids(provider_id="", saved_model_id="", fetched_model_ids=("vendor/model",)) == {}


def test_operator_saved_model_is_the_only_initial_configured_model() -> None:
    assert configured_model_ids(
        provider_id="openrouter", saved_model_id="openai/gpt-4.1-nano", fetched_model_ids=()
    ) == {"openrouter": ("openai/gpt-4.1-nano",)}


def test_primary_and_three_observers_are_independent() -> None:
    state = CockpitState(primary_model_id="openai/gpt-4.1-nano")
    state.observer_slots[0].enabled = True
    state.observer_slots[0].provider_id = "openrouter"
    state.observer_slots[0].model_id = "google/gemma-3-4b-it"

    assert len(state.observer_slots) == 3
    assert state.primary_model_id == "openai/gpt-4.1-nano"
    assert state.observer_slots[1].model_id == ""


def test_observer_models_are_filtered_by_their_selected_provider() -> None:
    state = CockpitState()
    models = {"openrouter": ("openai/gpt-4.1-nano",), "other": ("other/model",)}
    assert state.models_for_provider("openrouter", models) == ("openai/gpt-4.1-nano",)
    assert state.models_for_provider("missing", models) == ()


def test_complete_observer_configuration_is_ready_only_for_manual_review() -> None:
    state = CockpitState()
    slot = state.observer_slots[0]
    slot.enabled = True
    slot.provider_id = "openrouter"
    slot.model_id = "openai/gpt-4.1-nano"
    models = {"openrouter": ("openai/gpt-4.1-nano",)}

    assert state.review_status(("openrouter",), models) == "READY FOR MANUAL REVIEW"
