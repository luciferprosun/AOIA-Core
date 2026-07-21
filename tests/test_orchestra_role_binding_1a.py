from __future__ import annotations

from dataclasses import replace
import unittest

from runtime.epistemic_orchestra.canonical import EpistemicContractError
from runtime.epistemic_orchestra.role_binding import (
    ModelRoleAssignment,
    OrchestraOperatorRole,
    OrchestraRoleSelection,
    build_model_role_assignment,
    build_orchestra_role_selection,
    validate_role_selection_against_current_profiles,
)
from runtime.providers.model_profiles import ModelProfile
from runtime.providers.user_connections import ProviderConnection


ALL_ROLES = ("MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER")
SECRET_SENTINEL = "sk-or-v1-never-bind-this-secret-value"


def connection(*, enabled: bool = True, display_name: str = "My OpenRouter") -> ProviderConnection:
    return ProviderConnection(
        connection_id="my-openrouter",
        display_name=display_name,
        api_style="openai_compatible",
        base_url="https://openrouter.ai/api/v1",
        native_adapter_id=None,
        credential_reference="my-openrouter-key",
        enabled=enabled,
        created_at="2026-07-20T22:00:00Z",
    )


def profile(
    ordinal: int,
    *,
    enabled: bool = True,
    allowed_roles: tuple[str, ...] = ALL_ROLES,
    display_name: str | None = None,
) -> ModelProfile:
    return ModelProfile(
        model_profile_id=f"model-{ordinal}",
        connection_id="my-openrouter",
        display_name=display_name or f"Review Model {ordinal}",
        remote_model_id=f"vendor/review-model-{ordinal}",
        enabled=enabled,
        allowed_roles=allowed_roles,
        context_limit=32_000,
        output_limit=512,
    )


def assignments(roles: tuple[str, ...]):
    selected_connection = connection()
    profiles = tuple(profile(index) for index in range(len(roles)))
    values = tuple(
        build_model_role_assignment(
            ordinal=index,
            connection=selected_connection,
            model_profile=profiles[index],
            role=role,
        )
        for index, role in enumerate(roles)
    )
    return selected_connection, profiles, values


class OrchestraRoleBinding1ATests(unittest.TestCase):
    def test_two_model_main_critic_selection_succeeds(self):
        _, _, values = assignments(("MAIN", "CRITIC"))
        selection = build_orchestra_role_selection(values)
        self.assertEqual(tuple(item.role for item in selection.assignments), ("MAIN", "CRITIC"))
        self.assertEqual(len(selection.role_selection_hash), 64)

    def test_three_model_main_critic_auditor_selection_succeeds(self):
        _, _, values = assignments(("MAIN", "CRITIC", "AUDITOR"))
        selection = build_orchestra_role_selection(values)
        self.assertEqual(len(selection.assignments), 3)

    def test_five_model_selection_with_last_synthesizer_succeeds(self):
        _, _, values = assignments(
            ("MAIN", "CRITIC", "CRITIC", "AUDITOR", "SYNTHESIZER")
        )
        selection = build_orchestra_role_selection(values)
        self.assertEqual(len(selection.assignments), 5)
        self.assertEqual(selection.assignments[-1].role, "SYNTHESIZER")

    def test_one_model_selection_fails(self):
        _, _, values = assignments(("MAIN",))
        with self.assertRaises(EpistemicContractError):
            build_orchestra_role_selection(values)

    def test_six_model_selection_fails(self):
        _, _, values = assignments(
            ("MAIN", "CRITIC", "CRITIC", "AUDITOR", "AUDITOR", "SYNTHESIZER")
        )
        with self.assertRaises(EpistemicContractError):
            build_orchestra_role_selection(values)

    def test_zero_main_roles_fail(self):
        _, _, values = assignments(("CRITIC", "AUDITOR"))
        with self.assertRaises(EpistemicContractError):
            build_orchestra_role_selection(values)

    def test_two_main_roles_fail(self):
        _, _, values = assignments(("MAIN", "MAIN", "CRITIC"))
        with self.assertRaises(EpistemicContractError):
            build_orchestra_role_selection(values)

    def test_main_must_be_first(self):
        _, _, values = assignments(("CRITIC", "MAIN"))
        with self.assertRaises(EpistemicContractError):
            build_orchestra_role_selection(values)

    def test_at_least_one_critic_or_auditor_is_required(self):
        _, _, values = assignments(("MAIN", "SYNTHESIZER"))
        with self.assertRaises(EpistemicContractError):
            build_orchestra_role_selection(values)

    def test_synthesizer_must_be_unique_and_last(self):
        _, _, middle = assignments(("MAIN", "SYNTHESIZER", "CRITIC"))
        with self.assertRaises(EpistemicContractError):
            build_orchestra_role_selection(middle)
        _, _, duplicate = assignments(("MAIN", "CRITIC", "SYNTHESIZER", "SYNTHESIZER"))
        with self.assertRaises(EpistemicContractError):
            build_orchestra_role_selection(duplicate)

    def test_unsupported_or_disallowed_role_fails(self):
        selected_connection = connection()
        selected_profile = profile(0, allowed_roles=("MAIN",))
        with self.assertRaises(EpistemicContractError):
            build_model_role_assignment(
                ordinal=0,
                connection=selected_connection,
                model_profile=selected_profile,
                role="ROUTER",
            )
        with self.assertRaises(EpistemicContractError):
            build_model_role_assignment(
                ordinal=0,
                connection=selected_connection,
                model_profile=selected_profile,
                role="CRITIC",
            )

    def test_disabled_connection_or_model_fails(self):
        with self.assertRaises(EpistemicContractError):
            build_model_role_assignment(
                ordinal=0,
                connection=connection(enabled=False),
                model_profile=profile(0),
                role="MAIN",
            )
        with self.assertRaises(EpistemicContractError):
            build_model_role_assignment(
                ordinal=0,
                connection=connection(),
                model_profile=profile(0, enabled=False),
                role="MAIN",
            )

    def test_duplicate_model_profile_selection_fails(self):
        selected_connection = connection()
        selected_profile = profile(0)
        values = tuple(
            build_model_role_assignment(
                ordinal=index,
                connection=selected_connection,
                model_profile=selected_profile,
                role=role,
            )
            for index, role in enumerate(("MAIN", "CRITIC"))
        )
        with self.assertRaises(EpistemicContractError):
            build_orchestra_role_selection(values)

    def test_changed_role_changes_assignment_and_selection_hashes(self):
        selected_connection = connection()
        first_profile = profile(0)
        second_profile = profile(1)
        main = build_model_role_assignment(
            ordinal=0,
            connection=selected_connection,
            model_profile=first_profile,
            role=OrchestraOperatorRole.MAIN,
        )
        critic = build_model_role_assignment(
            ordinal=1,
            connection=selected_connection,
            model_profile=second_profile,
            role=OrchestraOperatorRole.CRITIC,
        )
        auditor = build_model_role_assignment(
            ordinal=1,
            connection=selected_connection,
            model_profile=second_profile,
            role=OrchestraOperatorRole.AUDITOR,
        )
        self.assertNotEqual(critic.role_assignment_hash, auditor.role_assignment_hash)
        self.assertNotEqual(
            build_orchestra_role_selection((main, critic)).role_selection_hash,
            build_orchestra_role_selection((main, auditor)).role_selection_hash,
        )

    def test_current_revision_validation_accepts_exact_metadata(self):
        selected_connection, profiles, values = assignments(("MAIN", "CRITIC", "AUDITOR"))
        selection = build_orchestra_role_selection(values)
        validate_role_selection_against_current_profiles(
            selection,
            connections_by_id={selected_connection.connection_id: selected_connection},
            model_profiles_by_id={item.model_profile_id: item for item in profiles},
        )

    def test_changed_connection_or_model_revision_fails_closed(self):
        selected_connection, profiles, values = assignments(("MAIN", "CRITIC"))
        selection = build_orchestra_role_selection(values)
        changed_connection = replace(
            selected_connection,
            display_name="Changed Connection",
            connection_revision_hash="",
        )
        with self.assertRaises(EpistemicContractError):
            validate_role_selection_against_current_profiles(
                selection,
                connections_by_id={changed_connection.connection_id: changed_connection},
                model_profiles_by_id={item.model_profile_id: item for item in profiles},
            )
        changed_profile = replace(
            profiles[1],
            remote_model_id="vendor/changed-model",
            model_revision_hash="",
        )
        with self.assertRaises(EpistemicContractError):
            validate_role_selection_against_current_profiles(
                selection,
                connections_by_id={selected_connection.connection_id: selected_connection},
                model_profiles_by_id={
                    profiles[0].model_profile_id: profiles[0],
                    changed_profile.model_profile_id: changed_profile,
                },
            )

    def test_assignment_and_selection_round_trip_exactly(self):
        _, _, values = assignments(("MAIN", "CRITIC"))
        selection = build_orchestra_role_selection(values)
        restored_assignment = ModelRoleAssignment.from_dict(values[0].to_dict())
        restored_selection = OrchestraRoleSelection.from_dict(selection.to_dict())
        self.assertEqual(restored_assignment, values[0])
        self.assertEqual(restored_selection, selection)

    def test_secret_value_never_enters_assignment_or_selection_material(self):
        _, _, values = assignments(("MAIN", "CRITIC"))
        selection = build_orchestra_role_selection(values)
        self.assertNotIn(SECRET_SENTINEL, repr(selection.to_dict()))
        self.assertNotIn("api_key", repr(selection.to_dict()).casefold())
        for item in selection.assignments:
            self.assertFalse(item.provider_call_permitted)
            self.assertEqual(item.authority_status, "NON_AUTHORITATIVE")
        self.assertTrue(selection.human_review_required)


if __name__ == "__main__":
    unittest.main()
