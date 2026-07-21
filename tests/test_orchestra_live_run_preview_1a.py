from __future__ import annotations

from dataclasses import replace
import unittest

from runtime.epistemic_orchestra.canonical import EpistemicContractError
from runtime.epistemic_orchestra.live_run_preview import (
    OrchestraLiveRunPreview,
    PlannedLiveStage,
    build_live_run_confirmation_material,
    build_live_run_preview,
    validate_live_run_preview,
)
from runtime.epistemic_orchestra.role_binding import (
    build_model_role_assignment,
    build_orchestra_role_selection,
)
from runtime.providers.model_profiles import ModelProfile
from runtime.providers.user_connections import ProviderConnection


SOURCE_PROMPT = "Compare the bounded design and identify material production risks."
ALL_ROLES = ("MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER")


def connection() -> ProviderConnection:
    return ProviderConnection(
        connection_id="preview-connection",
        display_name="Preview Connection",
        api_style="openai_compatible",
        base_url="https://openrouter.ai/api/v1",
        native_adapter_id=None,
        credential_reference="preview-key",
        enabled=True,
        created_at="2026-07-20T22:00:00Z",
    )


def profile(index: int) -> ModelProfile:
    return ModelProfile(
        model_profile_id=f"preview-model-{index}",
        connection_id="preview-connection",
        display_name=f"Preview Model {index}",
        remote_model_id=f"vendor/preview-model-{index}",
        enabled=True,
        allowed_roles=ALL_ROLES,
        context_limit=32_000,
        output_limit=512,
    )


def selection(roles: tuple[str, ...]):
    selected_connection = connection()
    return build_orchestra_role_selection(
        tuple(
            build_model_role_assignment(
                ordinal=index,
                connection=selected_connection,
                model_profile=profile(index),
                role=role,
            )
            for index, role in enumerate(roles)
        )
    )


def preview(roles: tuple[str, ...], *, prompt: str = SOURCE_PROMPT):
    selected = selection(roles)
    run, value = build_live_run_preview(
        orchestra_run_id="live-preview-run-1",
        source_prompt=prompt,
        role_selection=selected,
        timeout_seconds=12,
        maximum_output_tokens=96,
        expires_at_epoch=1_790_000_000,
    )
    return selected, run, value


class OrchestraLiveRunPreview1ATests(unittest.TestCase):
    def test_two_model_preview_uses_three_stage_inert_spine(self):
        selected, run, value = preview(("MAIN", "CRITIC"))
        self.assertEqual(run.orchestration_mode, "INDEPENDENT_PANEL_V1")
        self.assertEqual(run.planned_stage_roles, ("PRIMARY", "CRITIC", "PRIMARY"))
        self.assertEqual(len(value.planned_calls), 2)
        self.assertTrue(value.final_primary_is_inert)
        self.assertNotIn(
            value.final_primary_stage_id,
            tuple(item.stage_id for item in value.planned_calls),
        )
        self.assertEqual(value.role_selection_hash, selected.role_selection_hash)

    def test_three_model_main_critic_auditor_preview(self):
        _, run, value = preview(("MAIN", "CRITIC", "AUDITOR"))
        self.assertEqual(
            run.planned_stage_roles,
            ("PRIMARY", "CRITIC", "CRITIC", "PRIMARY"),
        )
        self.assertEqual(
            tuple(item.operator_role for item in value.planned_calls),
            ("MAIN", "CRITIC", "AUDITOR"),
        )
        self.assertTrue(value.final_primary_is_inert)

    def test_five_model_preview_binds_synthesizer_to_final_primary(self):
        _, run, value = preview(
            ("MAIN", "CRITIC", "CRITIC", "AUDITOR", "SYNTHESIZER")
        )
        self.assertEqual(len(value.planned_calls), 5)
        self.assertEqual(len(run.planned_stage_ids), 5)
        self.assertFalse(value.final_primary_is_inert)
        self.assertEqual(value.planned_calls[-1].operator_role, "SYNTHESIZER")
        self.assertEqual(value.planned_calls[-1].stage_id, value.final_primary_stage_id)
        self.assertEqual(run.planned_stage_ids[-1], value.final_primary_stage_id)

    def test_preview_is_deterministic_and_round_trips(self):
        selected = selection(("MAIN", "CRITIC", "AUDITOR"))
        first_run, first = build_live_run_preview(
            orchestra_run_id="deterministic-live-run",
            source_prompt=SOURCE_PROMPT,
            role_selection=selected,
            timeout_seconds=10,
            maximum_output_tokens=64,
            expires_at_epoch=1_790_000_000,
        )
        second_run, second = build_live_run_preview(
            orchestra_run_id="deterministic-live-run",
            source_prompt=SOURCE_PROMPT,
            role_selection=selected,
            timeout_seconds=10,
            maximum_output_tokens=64,
            expires_at_epoch=1_790_000_000,
        )
        self.assertEqual(first_run, second_run)
        self.assertEqual(first, second)
        self.assertEqual(OrchestraLiveRunPreview.from_dict(first.to_dict()), first)
        self.assertEqual(
            PlannedLiveStage.from_dict(first.planned_calls[0].to_dict()),
            first.planned_calls[0],
        )

    def test_prompt_change_changes_source_request_run_and_preview_hashes(self):
        _, first_run, first = preview(("MAIN", "CRITIC"))
        _, changed_run, changed = preview(
            ("MAIN", "CRITIC"), prompt=SOURCE_PROMPT + " Changed."
        )
        self.assertNotEqual(first.source_prompt_hash, changed.source_prompt_hash)
        self.assertNotEqual(first.source_request_hash, changed.source_request_hash)
        self.assertNotEqual(first_run.run_hash, changed_run.run_hash)
        self.assertNotEqual(first.preview_hash, changed.preview_hash)

    def test_role_change_changes_selection_run_and_preview_hashes(self):
        critic_selection, critic_run, critic_preview = preview(("MAIN", "CRITIC"))
        auditor_selection, auditor_run, auditor_preview = preview(("MAIN", "AUDITOR"))
        self.assertNotEqual(
            critic_selection.role_selection_hash,
            auditor_selection.role_selection_hash,
        )
        self.assertNotEqual(critic_run.run_hash, auditor_run.run_hash)
        self.assertNotEqual(critic_preview.preview_hash, auditor_preview.preview_hash)

    def test_call_bounds_and_expiry_are_hash_bound(self):
        selected = selection(("MAIN", "CRITIC"))
        first_run, first = build_live_run_preview(
            orchestra_run_id="bounded-run",
            source_prompt=SOURCE_PROMPT,
            role_selection=selected,
            timeout_seconds=10,
            maximum_output_tokens=64,
            expires_at_epoch=1_790_000_000,
        )
        changed_run, changed = build_live_run_preview(
            orchestra_run_id="bounded-run",
            source_prompt=SOURCE_PROMPT,
            role_selection=selected,
            timeout_seconds=11,
            maximum_output_tokens=64,
            expires_at_epoch=1_790_000_000,
        )
        self.assertNotEqual(first_run.run_hash, changed_run.run_hash)
        self.assertNotEqual(first.preview_hash, changed.preview_hash)
        self.assertTrue(all(item.timeout_seconds == 10 for item in first.planned_calls))

    def test_invalid_timeout_output_limit_or_expiry_fails_closed(self):
        selected = selection(("MAIN", "CRITIC"))
        cases = (
            {"timeout_seconds": 0, "maximum_output_tokens": 64, "expires_at_epoch": 10},
            {"timeout_seconds": 61, "maximum_output_tokens": 64, "expires_at_epoch": 10},
            {"timeout_seconds": 10, "maximum_output_tokens": 0, "expires_at_epoch": 10},
            {"timeout_seconds": 10, "maximum_output_tokens": 513, "expires_at_epoch": 10},
            {"timeout_seconds": 10, "maximum_output_tokens": 64, "expires_at_epoch": 0},
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(EpistemicContractError):
                build_live_run_preview(
                    orchestra_run_id="invalid-bounds-run",
                    source_prompt=SOURCE_PROMPT,
                    role_selection=selected,
                    **values,
                )

    def test_confirmation_material_binds_exact_preview_but_cannot_authorize(self):
        _, _, value = preview(("MAIN", "CRITIC", "AUDITOR"))
        material = build_live_run_confirmation_material(value)
        self.assertEqual(material["action"], "RUN_ORCHESTRA_ONCE")
        self.assertEqual(material["preview_hash"], value.preview_hash)
        self.assertEqual(material["run_hash"], value.run_hash)
        self.assertEqual(material["role_selection_hash"], value.role_selection_hash)
        self.assertTrue(material["human_action_required"])
        self.assertFalse(material["provider_call_permitted"])
        self.assertNotIn("approved", material)

    def test_changed_selection_changes_confirmation_material(self):
        _, _, critic = preview(("MAIN", "CRITIC"))
        _, _, auditor = preview(("MAIN", "AUDITOR"))
        self.assertNotEqual(
            build_live_run_confirmation_material(critic),
            build_live_run_confirmation_material(auditor),
        )

    def test_exact_preview_validation_accepts_exact_material(self):
        selected, run, value = preview(("MAIN", "CRITIC", "AUDITOR"))
        validate_live_run_preview(
            value,
            run=run,
            source_prompt=SOURCE_PROMPT,
            role_selection=selected,
        )

    def test_stale_preview_run_or_selection_fails_closed(self):
        selected, run, value = preview(("MAIN", "CRITIC"))
        changed_selection = selection(("MAIN", "AUDITOR"))
        with self.assertRaises(EpistemicContractError):
            validate_live_run_preview(
                value,
                run=run,
                source_prompt=SOURCE_PROMPT,
                role_selection=changed_selection,
            )
        changed_preview = replace(
            value,
            expires_at_epoch=value.expires_at_epoch + 1,
            preview_hash="",
        )
        with self.assertRaises(EpistemicContractError):
            validate_live_run_preview(
                changed_preview,
                run=run,
                source_prompt=SOURCE_PROMPT,
                role_selection=selected,
            )

    def test_preview_and_planned_calls_remain_non_authoritative(self):
        _, run, value = preview(("MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER"))
        self.assertFalse(run.provider_call_permitted)
        self.assertFalse(value.provider_call_permitted)
        self.assertFalse(value.multi_model_agreement_is_authority)
        self.assertTrue(value.human_review_required)
        for item in value.planned_calls:
            self.assertEqual(item.authority_status, "NON_AUTHORITATIVE")
            self.assertFalse(item.provider_call_permitted)
            self.assertFalse(item.execution_permitted)
            self.assertFalse(item.write_permitted)
            self.assertTrue(item.human_review_required)


if __name__ == "__main__":
    unittest.main()
