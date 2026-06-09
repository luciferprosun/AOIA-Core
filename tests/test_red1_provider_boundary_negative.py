"""
RED-1-D provider/network boundary negative tests.
These tests do not call real providers.
They patch network/provider primitives and verify that unapproved or policy-rejected
router/proposal paths do not invoke provider/network calls.
This file targets RED-1 BLOCKER-05 only.
"""

from __future__ import annotations

import socket
import unittest
import urllib.request
from unittest.mock import patch

from runtime import provider_clients
from runtime.model_catalog import get_static_model_catalog_payload
from runtime.model_router import (
    create_model_selection_proposal,
    evaluate_model_selection_policy,
    execute_approved_model_call_once,
)
from runtime.provider_audit import ProviderAuditEvent
from runtime.schemas.model_router import RoutingDecisionStatus, TaskSensitivity


def _network_patches():
    return (
        patch.object(urllib.request, "urlopen", side_effect=AssertionError("urllib.request.urlopen called")),
        patch.object(socket, "create_connection", side_effect=AssertionError("socket.create_connection called")),
        patch.object(provider_clients, "urlopen", side_effect=AssertionError("provider_clients.urlopen called")),
    )


class Red1ProviderBoundaryNegativeTests(unittest.TestCase):
    def test_model_catalog_and_selection_proposal_do_not_call_provider_network(self) -> None:
        urlopen_patch, socket_patch, provider_urlopen_patch = _network_patches()
        with urlopen_patch as urlopen_mock, socket_patch as socket_mock, provider_urlopen_patch as provider_urlopen_mock:
            catalog = get_static_model_catalog_payload()
            proposal = create_model_selection_proposal(
                provider_id="gemini",
                model_id="gemini/gemini-2.5-flash",
                task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
                user_prompt="public diagnostic prompt",
            )
            decision = evaluate_model_selection_policy(proposal=proposal)

        self.assertFalse(catalog["provider_call_permitted"])
        self.assertFalse(proposal["provider_call_permitted"])
        self.assertEqual(RoutingDecisionStatus.PROPOSED.value, proposal["status"])
        self.assertEqual(RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL.value, decision["status"])
        urlopen_mock.assert_not_called()
        socket_mock.assert_not_called()
        provider_urlopen_mock.assert_not_called()

    def test_provider_call_path_blocks_without_human_approval_before_network(self) -> None:
        urlopen_patch, socket_patch, provider_urlopen_patch = _network_patches()
        with urlopen_patch as urlopen_mock, socket_patch as socket_mock, provider_urlopen_patch as provider_urlopen_mock:
            result = execute_approved_model_call_once(
                provider_id="gemini",
                model_id="gemini/gemini-2.5-flash",
                task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
                user_prompt="public diagnostic prompt",
                human_approved=False,
            )

        self.assertFalse(result["call_made"])
        self.assertFalse(result["output_trusted"])
        self.assertFalse(result["approval"]["provider_call_permitted"])
        self.assertIn("human approval", result["error"])
        urlopen_mock.assert_not_called()
        socket_mock.assert_not_called()
        provider_urlopen_mock.assert_not_called()

    def test_policy_rejected_openrouter_free_route_blocks_before_network(self) -> None:
        urlopen_patch, socket_patch, provider_urlopen_patch = _network_patches()
        with urlopen_patch as urlopen_mock, socket_patch as socket_mock, provider_urlopen_patch as provider_urlopen_mock:
            result = execute_approved_model_call_once(
                provider_id="openrouter",
                model_id="openrouter/free",
                task_sensitivity=TaskSensitivity.SENSITIVE.value,
                user_prompt="sensitive diagnostic prompt",
                human_approved=True,
            )

        self.assertFalse(result["call_made"])
        self.assertFalse(result["output_trusted"])
        self.assertFalse(result["approval"]["provider_call_permitted"])
        self.assertEqual(RoutingDecisionStatus.REJECTED_BY_POLICY.value, result["decision"]["status"])
        urlopen_mock.assert_not_called()
        socket_mock.assert_not_called()
        provider_urlopen_mock.assert_not_called()

    def test_provider_audit_rejects_trusted_output_or_canonical_promotion(self) -> None:
        base = {
            "event_id": "red1d-provider-audit",
            "timestamp_utc": "2026-06-09T13:00:00Z",
            "provider_id": "openrouter",
            "model_id": "openrouter/free",
            "status": "CALL_BLOCKED",
            "reason": "policy rejected",
        }

        with self.assertRaises(ValueError):
            ProviderAuditEvent(**base, provider_output_trusted=True)

        with self.assertRaises(ValueError):
            ProviderAuditEvent(**base, canonical_promotion_triggered=True)


if __name__ == "__main__":
    unittest.main()
