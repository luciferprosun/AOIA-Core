from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from runtime.epistemic_orchestra.live_run_preview import build_live_run_preview
from runtime.epistemic_orchestra.live_session import (
    LiveSessionUseRegistry,
    run_live_orchestra_session,
)
from runtime.epistemic_orchestra.role_binding import (
    build_model_role_assignment,
    build_orchestra_role_selection,
)
from runtime.providers.exact_invocation import (
    ExactProviderInvoker,
    consume_gateway_transport_authorization,
    consume_gateway_transport_receipt,
)
from runtime.providers.user_connections import UserProviderStore


NO_ISSUES = '{"critic_outcome":"NO_MATERIAL_ISSUE_FOUND","issues":[]}'


class OrchestraLiveSmoke1ATests(unittest.TestCase):
    def run_mocked_transport_flow(self, roles: tuple[str, ...]):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        store = UserProviderStore(
            root / "project",
            state_root=root / "state",
            secrets_root=root / "secrets",
        )
        connection = store.create_connection(
            connection_id="smoke-connection",
            display_name="Smoke Connection",
            api_style="openai_compatible",
            base_url="https://openrouter.example.test/api/v1",
            credential_reference="smoke-credential",
            created_at="operator-time",
            api_key="sk-test-smoke-secret-123456789",
        )
        profiles = tuple(
            store.create_model_profile(
                model_profile_id=f"smoke-model-{index}",
                connection_id=connection.connection_id,
                display_name=f"Smoke Model {index}",
                remote_model_id=f"vendor/smoke-{index}",
                allowed_roles=(role,),
            )
            for index, role in enumerate(roles)
        )
        selection = build_orchestra_role_selection(
            tuple(
                build_model_role_assignment(
                    ordinal=index,
                    connection=connection,
                    model_profile=profile,
                    role=role,
                )
                for index, (profile, role) in enumerate(zip(profiles, roles))
            )
        )
        source_prompt = "Run the mocked transport demonstration."
        run, preview = build_live_run_preview(
            orchestra_run_id=f"smoke-run-{len(roles)}",
            source_prompt=source_prompt,
            role_selection=selection,
            timeout_seconds=6,
            maximum_output_tokens=48,
            expires_at_epoch=200,
        )
        gateway_calls: list[dict] = []

        def mocked_gateway(**kwargs):
            gateway_calls.append(kwargs)
            material = {
                key: value
                for key, value in kwargs.items()
                if key not in {"api_key", "transport_authorization"}
            }
            receipt = consume_gateway_transport_authorization(
                kwargs["transport_authorization"],
                **material,
            )
            consume_gateway_transport_receipt(receipt, **material)
            index = len(gateway_calls) - 1
            role = roles[index]
            if role == "MAIN":
                response = "Mocked main response"
            elif role in {"CRITIC", "AUDITOR"}:
                response = NO_ISSUES
            else:
                response = "Mocked synthesis draft"
            return SimpleNamespace(
                connection_id=kwargs["connection_id"],
                model_profile_id=kwargs["model_profile_id"],
                remote_model_id=kwargs["remote_model_id"],
                response_text=response,
                trust_status="UNTRUSTED",
                authority_status="NON_AUTHORITATIVE",
                authoritative=False,
                can_approve=False,
                can_write=False,
                can_execute=False,
                can_satisfy_gate=False,
            )

        invoker = ExactProviderInvoker(store, gateway_call=mocked_gateway)
        registry = LiveSessionUseRegistry()
        confirmation = registry.issue_confirmation(
            preview=preview,
            confirmed_preview_hash=preview.preview_hash,
            explicit_run_action=True,
            issued_at_epoch=100,
        )
        result = run_live_orchestra_session(
            run=run,
            preview=preview,
            source_prompt=source_prompt,
            role_selection=selection,
            confirmation=confirmation,
            registry=registry,
            current_epoch=100,
            exact_invoker=invoker.invoke_exact,
        )
        return result, gateway_calls

    def test_two_model_mocked_transport_flow(self) -> None:
        result, calls = self.run_mocked_transport_flow(("MAIN", "CRITIC"))
        self.assertEqual(2, len(calls))
        self.assertEqual("Mocked main response", result.final_draft)

    def test_three_model_mocked_transport_flow(self) -> None:
        result, calls = self.run_mocked_transport_flow(("MAIN", "CRITIC", "AUDITOR"))
        self.assertEqual(3, len(calls))
        self.assertFalse(result.provider_output_is_authority)
        self.assertTrue(result.human_review_required)

    def test_five_model_mocked_transport_flow(self) -> None:
        roles = ("MAIN", "CRITIC", "CRITIC", "AUDITOR", "SYNTHESIZER")
        result, calls = self.run_mocked_transport_flow(roles)
        self.assertEqual(5, len(calls))
        self.assertEqual("Mocked synthesis draft", result.final_draft)
        self.assertTrue(result.synthesis_performed)
        self.assertTrue(all(call["remote_model_id"] == f"vendor/smoke-{index}" for index, call in enumerate(calls)))
        self.assertTrue(all("fallback" not in call for call in calls))


if __name__ == "__main__":
    unittest.main()
