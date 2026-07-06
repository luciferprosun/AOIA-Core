from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.integration_boundaries.mcp_boundary import (
    MCP_BOUNDARY_BLOCKED,
    MCP_BOUNDARY_BLOCKED_AUTHORITY_CLAIM,
    MCP_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE,
    MCP_BOUNDARY_BLOCKED_EFFECT_EVIDENCE,
    MCP_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE,
    MCP_BOUNDARY_BLOCKED_HASH_MISMATCH,
    MCP_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE,
    MCP_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE,
    MCP_BOUNDARY_BLOCKED_POLICY_CAPABILITY,
    MCP_BOUNDARY_BLOCKED_STALE_EVIDENCE,
    MCP_BOUNDARY_BLOCKED_UNSAFE_TRANSPORT,
    MCP_BOUNDARY_BLOCKED_UNKNOWN_FIELD,
    MCP_BOUNDARY_READY_METADATA_ONLY,
    MCP_BOUNDARY_REASON_READY_METADATA_ONLY,
    MCP_BOUNDARY_RISK_BLOCKED,
    MCP_BOUNDARY_RISK_MEDIUM,
    MCPBoundaryReviewResult,
    canonical_mcp_boundary_json,
    create_mcp_interaction_proposal,
    create_mcp_resource_declaration,
    create_mcp_server_declaration,
    create_mcp_tool_declaration,
    review_mcp_boundary,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "integration_boundaries" / "mcp_boundary.py"


class MCPBoundary1ATests(unittest.TestCase):
    def test_valid_mcp_metadata_review_is_inert_hash_bound_and_not_authority(self):
        evidence = self.evidence()

        result = review_mcp_boundary(**evidence, now_tick=12)

        self.assertEqual(MCP_BOUNDARY_READY_METADATA_ONLY, result.status)
        self.assertEqual((MCP_BOUNDARY_REASON_READY_METADATA_ONLY,), result.reason_codes)
        self.assertEqual(MCP_BOUNDARY_RISK_MEDIUM, result.risk_tier)
        self.assertEqual(evidence["server_declaration"].declaration_hash, result.server_declaration_hash)
        self.assertEqual((evidence["tool_declarations"][0].declaration_hash,), result.tool_declaration_hashes)
        self.assertEqual((evidence["resource_declarations"][0].declaration_hash,), result.resource_declaration_hashes)
        self.assertEqual(evidence["interaction_proposal"].proposal_hash, result.proposal_hash)
        self.assertIn("explicit_hash_bound_human_approval", result.required_future_evidence)
        self.assertIn("separate_controlled_mcp_runtime", result.required_future_evidence)
        self.assert_metadata_only(result.to_dict())

    def test_hashes_and_canonical_json_are_deterministic(self):
        first = review_mcp_boundary(**self.evidence(), now_tick=12)
        second = review_mcp_boundary(**self.evidence(), now_tick=12)

        self.assertEqual(first.review_hash, second.review_hash)
        self.assertEqual(
            canonical_mcp_boundary_json({"b": 1, "a": ("x",)}),
            canonical_mcp_boundary_json({"a": ["x"], "b": 1}),
        )

    def test_forbidden_capabilities_and_transport_fail_closed_as_metadata(self):
        blocked = self.evidence(server_capabilities=("call_tool", "start_server"))
        unsafe_transport = self.evidence(transport_kind="stdio")

        blocked_result = review_mcp_boundary(**blocked, now_tick=12)
        unsafe_result = review_mcp_boundary(**unsafe_transport, now_tick=12)

        self.assertEqual(MCP_BOUNDARY_BLOCKED, blocked_result.status)
        self.assertIn(MCP_BOUNDARY_BLOCKED_POLICY_CAPABILITY, blocked_result.reason_codes)
        self.assertEqual(MCP_BOUNDARY_RISK_BLOCKED, blocked_result.risk_tier)
        self.assertEqual(("call_tool", "start_server"), blocked_result.blocked_capabilities)
        self.assertEqual(MCP_BOUNDARY_BLOCKED, unsafe_result.status)
        self.assertIn(MCP_BOUNDARY_BLOCKED_UNSAFE_TRANSPORT, unsafe_result.reason_codes)
        self.assert_metadata_only(blocked_result.to_dict())
        self.assert_metadata_only(unsafe_result.to_dict())

    def test_missing_stale_unknown_non_json_and_hash_tampering_fail_closed(self):
        evidence = self.evidence()
        bad_proposal = evidence["interaction_proposal"].to_dict()
        bad_proposal["proposal_hash"] = "0" * 64
        cases = (
            ({**evidence, "server_declaration": {}}, MCP_BOUNDARY_BLOCKED_MALFORMED_EVIDENCE),
            ({**evidence, "interaction_proposal": {**evidence["interaction_proposal"].to_dict(), "unknown": "field"}}, MCP_BOUNDARY_BLOCKED_UNKNOWN_FIELD),
            ({**evidence, "interaction_proposal": {**evidence["interaction_proposal"].to_dict(), "metadata": {"bad": object()}}}, MCP_BOUNDARY_BLOCKED_NON_JSON_SERIALIZABLE),
            ({**evidence, "interaction_proposal": bad_proposal}, MCP_BOUNDARY_BLOCKED_HASH_MISMATCH),
            (
                {
                    **evidence,
                    "interaction_proposal": self.proposal(
                        evidence["server_declaration"],
                        evidence["tool_declarations"],
                        evidence["resource_declarations"],
                        created_at_tick=1,
                        expires_at_tick=5,
                    ),
                },
                MCP_BOUNDARY_BLOCKED_STALE_EVIDENCE,
            ),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = review_mcp_boundary(**altered, now_tick=12)

                self.assertEqual(MCP_BOUNDARY_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_authority_effect_executable_and_autonomous_claims_fail_closed(self):
        evidence = self.evidence()
        cases = (
            ({**evidence, "interaction_proposal": {**evidence["interaction_proposal"].to_dict(), "can_call_tool": True}}, MCP_BOUNDARY_BLOCKED_AUTHORITY_CLAIM),
            ({**evidence, "interaction_proposal": {**evidence["interaction_proposal"].to_dict(), "mcp_tool_called": True}}, MCP_BOUNDARY_BLOCKED_EFFECT_EVIDENCE),
            ({**evidence, "interaction_proposal": {**evidence["interaction_proposal"].to_dict(), "metadata": {"command": "mcp call server.tool"}}}, MCP_BOUNDARY_BLOCKED_EXECUTABLE_EVIDENCE),
            ({**evidence, "interaction_proposal": {**evidence["interaction_proposal"].to_dict(), "metadata": {"auto_call": True}}}, MCP_BOUNDARY_BLOCKED_AUTONOMOUS_EVIDENCE),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = review_mcp_boundary(**altered, now_tick=12)

                self.assertEqual(MCP_BOUNDARY_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_result_cannot_satisfy_gate_or_grant_authority_even_if_replaced(self):
        result = review_mcp_boundary(**self.evidence(), now_tick=12)
        forced = replace(
            result,
            mcp_server_started=True,
            mcp_server_connected=True,
            mcp_tool_called=True,
            mcp_resource_read=True,
            stdio_opened=True,
            http_called=True,
            sse_connected=True,
            websocket_connected=True,
            socket_opened=True,
            process_started=True,
            shell_called=True,
            provider_called=True,
            browser_opened=True,
            package_manager_called=True,
            git_action_performed=True,
            tool_call_invoked=True,
            dispatcher_created=True,
            async_io_started=True,
            agent_loop_started=True,
            approval_created=True,
            gate_satisfied=True,
            human_barrier_satisfied=True,
            mcp_allowed=True,
            can_call_tool=True,
            can_read_resource=True,
            can_execute=True,
            can_write=True,
            can_call_provider=True,
            can_change_gate=True,
        )

        self.assert_metadata_only(forced.to_dict())
        for method_name in ("run", "execute", "dispatch", "call_tool", "read_resource", "connect", "start_server"):
            self.assertFalse(hasattr(result, method_name))

    def test_boundary_result_rejects_invalid_status_and_risk(self):
        result = review_mcp_boundary(**self.evidence(), now_tick=12)
        data = result.to_dict()

        with self.assertRaises(ValueError):
            MCPBoundaryReviewResult(**{**data, "status": "EXECUTE"})
        with self.assertRaises(ValueError):
            MCPBoundaryReviewResult(**{**data, "risk_tier": "APPROVED"})

    def test_module_static_surface_is_boundary_only(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        scan = scan_module(RUNTIME_FILE)

        for forbidden_import in (
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "aiohttp",
            "webbrowser",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
            "runtime.providers.gateway",
            "runtime.provider_live_adapter",
            "runtime.control_write",
            "runtime.execution",
            "runtime.git_ops",
            "runtime.package_ops.controlled_package_install",
        ):
            self.assertNotIn(forbidden_import, scan.imports)
        for forbidden_call in (
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "eval",
            "exec",
            "__import__",
            "importlib.import_module",
        ):
            self.assertNotIn(forbidden_call, scan.calls)
        for forbidden_text in ("shell=true", "os.environ", "getenv", "api_key", "step 50", "step 51", "step 52", "step 53", "step 54"):
            self.assertNotIn(forbidden_text, source)

    def evidence(self, *, server_capabilities=("summarize_server_metadata", "propose_tool_call_metadata"), transport_kind="metadata_only"):
        tool = create_mcp_tool_declaration(
            tool_id="search",
            server_id="local-metadata-server",
            tool_kind="read_only_metadata",
            input_schema_hash="2" * 64,
            declared_capabilities=("declare_tool_metadata", "propose_tool_call_metadata"),
        )
        resource = create_mcp_resource_declaration(
            resource_id="docs",
            server_id="local-metadata-server",
            resource_kind="static_metadata",
            resource_uri_template="aoia://docs/{name}",
            declared_capabilities=("declare_resource_metadata", "propose_resource_read_metadata"),
        )
        server = create_mcp_server_declaration(
            server_id="local-metadata-server",
            server_kind="local_metadata",
            transport_kind=transport_kind,
            declared_tools=(tool.tool_id,),
            declared_resources=(resource.resource_id,),
            declared_capabilities=server_capabilities,
        )
        proposal = self.proposal(server, (tool,), (resource,))
        return {
            "server_declaration": server,
            "tool_declarations": (tool,),
            "resource_declarations": (resource,),
            "interaction_proposal": proposal,
        }

    def proposal(self, server, tools, resources, *, created_at_tick=10, expires_at_tick=20):
        return create_mcp_interaction_proposal(
            proposal_id="mcp-proposal",
            server_declaration_hash=server.declaration_hash,
            tool_declaration_hashes=tuple(tool.declaration_hash for tool in tools),
            resource_declaration_hashes=tuple(resource.declaration_hash for resource in resources),
            interaction_kind="propose_tool_call",
            target_id=tools[0].tool_id,
            arguments={"query": "metadata only"},
            reason="Propose MCP interaction as inert metadata.",
            requested_by="tester",
            created_at_tick=created_at_tick,
            expires_at_tick=expires_at_tick,
            metadata={"source": "unit-test"},
        )

    def assert_metadata_only(self, data):
        for field in (
            "mcp_server_started",
            "mcp_server_connected",
            "mcp_tool_called",
            "mcp_resource_read",
            "stdio_opened",
            "http_called",
            "sse_connected",
            "websocket_connected",
            "socket_opened",
            "process_started",
            "shell_called",
            "provider_called",
            "browser_opened",
            "package_manager_called",
            "git_action_performed",
            "tool_call_invoked",
            "dispatcher_created",
            "async_io_started",
            "agent_loop_started",
            "approval_created",
            "gate_satisfied",
            "human_barrier_satisfied",
            "mcp_allowed",
            "can_call_tool",
            "can_read_resource",
            "can_execute",
            "can_write",
            "can_call_provider",
            "can_change_gate",
        ):
            self.assertIs(data[field], False)
        self.assertIs(data["human_review_required"], True)


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, ast.Call):
            calls.add(call_name(node.func))
    return type("Scan", (), {"imports": tuple(sorted(imports)), "calls": tuple(sorted(calls))})()


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


if __name__ == "__main__":
    unittest.main()
