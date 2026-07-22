"""Source-level contract tests for the desktop-only premium cockpit."""

from __future__ import annotations

from pathlib import Path

from apps.aoia_desktop_demo.ui.cockpit_state import CockpitState, configured_model_ids


UI_DIR = Path(__file__).resolve().parents[1] / "ui"


def test_premium_cockpit_replaces_the_small_layout_with_required_surfaces() -> None:
    source = (UI_DIR / "main_window.py").read_text(encoding="utf-8")
    for required in (
        "CONTROLLED DESKTOP DEMO",
        "CRITICAL PROMPT LOOP",
        "CONVERSATION",
        "Run Critical Review",
        "SMART ROUTER TELEMETRY — NOT CONNECTED IN THIS DEMO",
    ):
        assert required in source


def test_primary_selector_is_readonly_and_has_no_automatic_switch_path() -> None:
    source = (UI_DIR / "settings_dialog.py").read_text(encoding="utf-8")
    assert 'textvariable=self.primary_model_var, state="readonly"' in source
    assert "automatically" in source
    assert "fallback" in source.lower()


def test_three_observer_slots_are_exact_and_manual_only() -> None:
    source = (UI_DIR / "cockpit_state.py").read_text(encoding="utf-8")
    assert "if len(self.observer_slots) != 3" in source
    assert "send_chat" not in source
    assert "refresh_models" not in source


def test_primary_and_observer_model_state_do_not_overwrite_each_other() -> None:
    state = CockpitState(primary_model_id="openai/gpt-4.1-nano")
    state.observer_slots[2].model_id = "google/gemma-3-4b-it"
    state.set_primary_model("anthropic/claude-3.5-haiku")
    assert state.primary_model_id == "anthropic/claude-3.5-haiku"
    assert state.observer_slots[2].model_id == "google/gemma-3-4b-it"


def test_empty_model_state_fails_closed() -> None:
    assert configured_model_ids(provider_id="openrouter", saved_model_id="", fetched_model_ids=()) == {}


def test_api_key_widget_is_masked_and_never_prefilled() -> None:
    source = (UI_DIR / "settings_dialog.py").read_text(encoding="utf-8")
    assert "API_KEY_ENTRY_MASK" in source
    assert "self.api_key_var.set(\"\")" in source
    assert "never saved" in source


def test_no_telemetry_integration_or_automatic_observer_request_is_added() -> None:
    source = (UI_DIR / "main_window.py").read_text(encoding="utf-8")
    assert "SMART ROUTER TELEMETRY — NOT CONNECTED IN THIS DEMO" in source
    review_body = source.split("def _run_critical_review", 1)[1].split("# --- chat", 1)[0]
    assert "submit_message" not in review_body
    assert "send_chat" not in review_body
    assert "submit_critical_review" in review_body
