from __future__ import annotations

import unittest
from http import HTTPStatus
from pathlib import Path

from runtime.webapp import route_get_payload, route_post_payload


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "web"
RUNTIME_WEBAPP = PROJECT_ROOT / "runtime" / "webapp.py"


class WebOperatorConsole1ATests(unittest.TestCase):
    def test_operator_status_endpoint_is_read_only_metadata(self) -> None:
        routed = route_get_payload("/api/operator/status")

        self.assertIsNotNone(routed)
        status, payload = routed
        self.assertEqual(HTTPStatus.OK, status)
        self.assertTrue(payload["ok"])
        self.assertEqual("preview-only operator console", payload["safety_mode"])
        self.assertFalse(payload["authority"]["metadata_is_authority"])
        self.assertFalse(payload["authority"]["ui_state_is_authority"])
        self.assertFalse(payload["authority"]["dispatcher_present"])
        self.assertFalse(payload["git"]["can_commit"])
        self.assertFalse(payload["git"]["can_push"])

    def test_boundary_map_endpoint_reports_non_executing_layers(self) -> None:
        status, payload = route_get_payload("/api/boundaries")

        self.assertEqual(HTTPStatus.OK, status)
        self.assertGreaterEqual(len(payload["boundaries"]), 13)
        labels = {item["label"] for item in payload["boundaries"]}
        self.assertIn("Provider agent loop boundary", labels)
        for boundary in payload["boundaries"]:
            self.assertTrue(boundary["inert_metadata"])
            self.assertFalse(boundary["can_execute"])
            self.assertFalse(boundary["can_dispatch"])
            self.assertTrue(boundary["requires_human_review"])

    def test_router_status_endpoint_is_preview_only_and_explains_disabled_state(self) -> None:
        status, payload = route_get_payload("/api/router/status")

        self.assertEqual(HTTPStatus.OK, status)
        self.assertTrue(payload["provider_call_disabled"])
        self.assertFalse(payload["provider_call_permitted"])
        self.assertFalse(payload["connection_callable"])
        self.assertFalse(payload["human_barrier_connected"])
        self.assertIn("Provider call disabled in this build", payload["notice"])
        self.assertIn("Preview only", payload["reason"])

    def test_router_preview_does_not_call_provider_and_returns_inert_metadata(self) -> None:
        status, payload = route_post_payload(
            "/api/router/preview",
            {
                "provider_id": "gemini",
                "model_id": "gemini/gemini-2.5-flash",
                "task_sensitivity": "PUBLIC_DEV",
                "user_prompt": "preview only prompt",
            },
        )

        self.assertEqual(HTTPStatus.OK, status)
        self.assertTrue(payload["ok"])
        self.assertEqual("blocked_preview_only", payload["status"])
        self.assertFalse(payload["provider_call_permitted"])
        self.assertTrue(payload["provider_call_disabled"])
        self.assertFalse(payload["call_made"])
        self.assertFalse(payload["output_trusted"])
        self.assertFalse(payload["human_barrier_connected"])
        self.assertIn("AOIA_ROUTER_PREVIEW_ONLY", payload["reason_codes"])
        self.assertIn("preview_hash", payload)

    def test_unsafe_mutation_and_execution_endpoints_do_not_exist(self) -> None:
        forbidden_paths = (
            "/api/provider/call",
            "/api/execute",
            "/api/dispatch",
            "/api/git/push",
            "/api/git/commit",
            "/api/package/install",
            "/api/browser/run",
            "/api/mcp/call-tool",
            "/api/agent/run",
            "/api/apply-patch",
            "/api/model-selection/approve-and-call",
        )

        for path in forbidden_paths:
            with self.subTest(path=path):
                status, payload = route_post_payload(path, {})
                self.assertEqual(HTTPStatus.NOT_FOUND, status)
                self.assertFalse(payload["ok"])

    def test_evidence_and_agent_loop_endpoints_are_non_authoritative(self) -> None:
        evidence_status, evidence = route_get_payload("/api/evidence/sample")
        agent_status, agent = route_get_payload("/api/agent-loop/status")

        self.assertEqual(HTTPStatus.OK, evidence_status)
        self.assertEqual("missing", evidence["evidence"]["status"])
        self.assertFalse(evidence["can_execute"])
        self.assertFalse(evidence["can_dispatch"])
        self.assertEqual(HTTPStatus.OK, agent_status)
        self.assertFalse(agent["local_loop"]["can_execute"])
        self.assertFalse(agent["provider_loop"]["can_execute"])
        self.assertTrue(agent["provider_loop"]["requires_human_review"])

    def test_ui_files_show_operator_console_and_no_secret_values(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in WEB_DIR.glob("*.*"))

        self.assertIn("AOIA Operator Console", combined)
        self.assertIn('id="chat" class="view active-view"', combined)
        self.assertIn('id="chat-history"', combined)
        self.assertIn('id="chat-input"', combined)
        self.assertIn('id="send-chat"', combined)
        self.assertIn("Provider call disabled in this build", combined)
        self.assertIn("No provider request was sent", combined)
        self.assertIn("Preview only", combined)
        self.assertIn("UI checkbox is not a hash-bound human barrier", RUNTIME_WEBAPP.read_text(encoding="utf-8"))
        self.assertNotIn("BEGIN PRIVATE KEY", combined)
        self.assertNotIn("id_rsa", combined)
        self.assertNotIn("sk-proj-", combined)
        self.assertNotIn("sk_live", combined)
        self.assertNotIn("/api/model-selection/approve-and-call", combined)

    def test_frontend_uses_preview_endpoint_and_not_provider_call_endpoint(self) -> None:
        app_source = (WEB_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn('"/api/router/preview"', app_source)
        self.assertNotIn('"/api/provider/call"', app_source)
        self.assertNotIn('"/api/execute"', app_source)
        self.assertNotIn('"/api/dispatch"', app_source)
        self.assertNotIn('"/api/git/push"', app_source)
        self.assertNotIn('"/api/package/install"', app_source)
        self.assertNotIn('"/api/browser/run"', app_source)
        self.assertNotIn('"/api/mcp/call-tool"', app_source)
        self.assertNotIn('"/api/agent/run"', app_source)


if __name__ == "__main__":
    unittest.main()
