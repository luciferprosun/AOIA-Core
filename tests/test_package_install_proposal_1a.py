from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.package_ops.package_install_proposal import (
    PACKAGE_INSTALL_PROPOSAL_BLOCKED,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_AUTHORITY_CLAIM,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_COMMAND_LIKE_EVIDENCE,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_DANGEROUS_METADATA,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_HASH_MISMATCH,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_CANONICAL_PACKAGE,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_JSON_SERIALIZABLE,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_STALE_EVIDENCE,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNKNOWN_FIELD,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNPINNED_PACKAGE,
    PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNSUPPORTED_ECOSYSTEM,
    PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY,
    PACKAGE_INSTALL_PROPOSAL_REASON_READY_METADATA_ONLY,
    PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION,
    PackageInstallProposalRequest,
    compute_package_install_request_hash,
    compute_package_install_toctou_evidence_hash,
    propose_package_install,
)


RUNTIME_FILE = Path(__file__).resolve().parents[1] / "runtime" / "package_ops" / "package_install_proposal.py"


class PackageInstallProposal1ATests(unittest.TestCase):
    def test_valid_pip_npm_and_apt_requests_are_inert_hash_bound_metadata(self):
        cases = (
            ("pip", "requests", "2.32.3", "pip:requests==2.32.3"),
            ("npm", "@types/node", "20.11.30", "npm:@types/node==20.11.30"),
            ("apt", "curl", "8.5.0-2ubuntu10.6", "apt:curl==8.5.0-2ubuntu10.6"),
        )

        for ecosystem, package_name, version, package_ref in cases:
            with self.subTest(ecosystem=ecosystem):
                request = self.request(ecosystem=ecosystem, package_name=package_name, version=version)
                proposal = propose_package_install(request, now_tick=15)

                self.assertEqual(PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY, proposal.status)
                self.assertEqual((PACKAGE_INSTALL_PROPOSAL_REASON_READY_METADATA_ONLY,), proposal.reason_codes)
                self.assertEqual(package_ref, proposal.normalized_package_ref)
                self.assertEqual(
                    compute_package_install_toctou_evidence_hash(request.toctou_evidence),
                    proposal.toctou_evidence_hash,
                )
                self.assertEqual(compute_package_install_request_hash(request), proposal.request_hash)
                self.assert_metadata_only(proposal.to_dict())

    def test_request_hash_is_deterministic_and_bound_to_exact_reviewed_evidence(self):
        request = self.request()
        first = propose_package_install(request, now_tick=15)
        second = propose_package_install(request, now_tick=15)
        changed = propose_package_install(replace(request, reason="Different reason."), now_tick=15)

        self.assertEqual(first.request_hash, second.request_hash)
        self.assertEqual(first.proposal_hash, second.proposal_hash)
        self.assertNotEqual(first.request_hash, changed.request_hash)
        self.assertNotEqual(first.proposal_hash, changed.proposal_hash)

    def test_supplied_request_hash_mismatch_fails_closed(self):
        payload = self.request_dict()
        payload["request_hash"] = "0" * 64

        proposal = propose_package_install(payload, now_tick=15)

        self.assertEqual(PACKAGE_INSTALL_PROPOSAL_BLOCKED, proposal.status)
        self.assertIn(PACKAGE_INSTALL_PROPOSAL_BLOCKED_HASH_MISMATCH, proposal.reason_codes)
        self.assert_metadata_only(proposal.to_dict())

    def test_now_tick_is_mandatory_and_ttl_evidence_fails_closed_when_stale(self):
        valid = propose_package_install(self.request(), now_tick=15)
        no_now = propose_package_install(self.request(), now_tick=None)
        future = propose_package_install(replace(self.request(), created_at_tick=20), now_tick=15)
        expired = propose_package_install(replace(self.request(), expires_at_tick=14), now_tick=15)
        inverted = propose_package_install(replace(self.request(), created_at_tick=20, expires_at_tick=10), now_tick=15)

        self.assertEqual(PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY, valid.status)
        for proposal in (no_now, future, expired, inverted):
            with self.subTest(proposal=proposal.reason_codes):
                self.assertEqual(PACKAGE_INSTALL_PROPOSAL_BLOCKED, proposal.status)
                self.assertTrue(
                    {
                        PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE,
                        PACKAGE_INSTALL_PROPOSAL_BLOCKED_STALE_EVIDENCE,
                    }
                    & set(proposal.reason_codes)
                )

    def test_missing_unknown_or_malformed_required_evidence_fails_closed(self):
        missing_reason = self.request_dict()
        missing_reason.pop("reason")
        missing_requested_by = self.request_dict()
        missing_requested_by["requested_by"] = ""
        unknown = self.request_dict()
        unknown["extra"] = "unknown"
        missing_toctou = self.request_dict()
        missing_toctou["toctou_evidence"] = {}

        cases = (
            (missing_reason, PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE),
            (missing_requested_by, PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE),
            (unknown, PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNKNOWN_FIELD),
            (missing_toctou, PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE),
        )
        for payload, reason in cases:
            with self.subTest(reason=reason):
                proposal = propose_package_install(payload, now_tick=15)

                self.assertEqual(PACKAGE_INSTALL_PROPOSAL_BLOCKED, proposal.status)
                self.assertIn(reason, proposal.reason_codes)

    def test_unsupported_ecosystem_non_canonical_name_and_unpinned_version_fail_closed(self):
        cases = (
            (replace(self.request(), ecosystem="brew"), PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNSUPPORTED_ECOSYSTEM),
            (replace(self.request(), package_name="Requests"), PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_CANONICAL_PACKAGE),
            (replace(self.request(), package_name="requests>=2"), PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_CANONICAL_PACKAGE),
            (replace(self.request(), version="latest"), PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNPINNED_PACKAGE),
            (replace(self.request(), version=">=2.0"), PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNPINNED_PACKAGE),
            (replace(self.request(), version="^1.2.3"), PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNPINNED_PACKAGE),
        )

        for request, reason in cases:
            with self.subTest(reason=reason):
                proposal = propose_package_install(request, now_tick=15)

                self.assertEqual(PACKAGE_INSTALL_PROPOSAL_BLOCKED, proposal.status)
                self.assertIn(reason, proposal.reason_codes)

    def test_command_like_package_manager_shell_network_and_python_smuggling_fail_closed(self):
        cases = (
            replace(self.request(), reason="Run pip install requests."),
            replace(self.request(), reason="Use npm install left-pad."),
            replace(self.request(), reason="sudo apt install curl"),
            replace(self.request(), package_name="requests;rm"),
            replace(self.request(), version="1.0.0 && echo bad"),
            replace(self.request(), metadata={"note": "curl https://example.invalid"}),
            replace(self.request(), toctou_evidence={"python": "__import__('os').system('id')"}),
            replace(self.request(), toctou_evidence={"runtime": "eval('1+1')"}),
        )

        for request in cases:
            with self.subTest(request=request):
                proposal = propose_package_install(request, now_tick=15)

                self.assertEqual(PACKAGE_INSTALL_PROPOSAL_BLOCKED, proposal.status)
                self.assertIn(PACKAGE_INSTALL_PROPOSAL_BLOCKED_COMMAND_LIKE_EVIDENCE, proposal.reason_codes)

    def test_authority_claims_and_dangerous_metadata_are_blocked_not_interpreted(self):
        cases = (
            ({**self.request_dict(), "approved": True}, PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNKNOWN_FIELD),
            (replace(self.request(), metadata={"can_install": True}), PACKAGE_INSTALL_PROPOSAL_BLOCKED_AUTHORITY_CLAIM),
            (replace(self.request(), reason="Approved and safe to install."), PACKAGE_INSTALL_PROPOSAL_BLOCKED_AUTHORITY_CLAIM),
            (replace(self.request(), metadata={"registry_url": "https://registry.invalid"}), PACKAGE_INSTALL_PROPOSAL_BLOCKED_DANGEROUS_METADATA),
            (replace(self.request(), toctou_evidence={"package_json": "would change dependencies"}), PACKAGE_INSTALL_PROPOSAL_BLOCKED_DANGEROUS_METADATA),
        )

        for request, reason in cases:
            with self.subTest(reason=reason):
                proposal = propose_package_install(request, now_tick=15)

                self.assertEqual(PACKAGE_INSTALL_PROPOSAL_BLOCKED, proposal.status)
                self.assertIn(reason, proposal.reason_codes)
                self.assert_metadata_only(proposal.to_dict())

    def test_non_json_serializable_evidence_fails_closed(self):
        proposal = propose_package_install(
            replace(self.request(), metadata={"bad": {object()}}),
            now_tick=15,
        )

        self.assertEqual(PACKAGE_INSTALL_PROPOSAL_BLOCKED, proposal.status)
        self.assertIn(PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_JSON_SERIALIZABLE, proposal.reason_codes)

    def test_result_authority_fields_are_forced_false_even_if_constructed_true(self):
        proposal = propose_package_install(self.request(), now_tick=15)
        forced = replace(
            proposal,
            install_performed=True,
            package_manager_called=True,
            network_called=True,
            process_started=True,
            shell_called=True,
            dependency_file_modified=True,
            can_install=True,
            can_execute=True,
            can_write=True,
            gate_satisfied=True,
            human_barrier_satisfied=True,
        )

        self.assert_metadata_only(forced.to_dict())

    def test_module_has_no_package_manager_network_provider_browser_git_env_or_runtime_surface(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        scan = scan_module(RUNTIME_FILE)

        forbidden_imports = (
            "os",
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
            "pip",
            "venv",
            "runtime.providers.gateway",
            "runtime.provider_live_adapter",
            "runtime.execution",
            "runtime.control_write",
        )
        forbidden_calls = (
            "open",
            "print",
            "eval",
            "exec",
            "write",
            "write_text",
            "write_bytes",
            "dispatch",
            "authorize",
        )

        for forbidden in forbidden_imports:
            self.assertNotIn(forbidden, scan.imports)
        for forbidden in forbidden_calls:
            self.assertNotIn(forbidden, scan.calls)
        for forbidden_text in ("shell=true", "os.environ", "getenv", "api_key"):
            self.assertNotIn(forbidden_text, source)

    def request(self, **overrides) -> PackageInstallProposalRequest:
        values = {
            "ecosystem": "pip",
            "package_name": "requests",
            "version": "2.32.3",
            "reason": "Needed for a later reviewed dependency change proposal.",
            "requested_by": "local-human-operator",
            "created_at_tick": 10,
            "expires_at_tick": 20,
            "toctou_evidence": {
                "workspace_state_hash": "a" * 64,
                "dependency_file_hashes": {
                    "runtime/requirements.txt": "b" * 64,
                    "pyproject.toml": "c" * 64,
                },
                "observed_at_tick": 10,
            },
            "proposal_id": "pkg-install-001",
            "source_id": "manual-review",
            "source_hash": "d" * 64,
            "metadata": {"ticket": "step-42"},
        }
        values.update(overrides)
        return PackageInstallProposalRequest(**values)

    def request_dict(self, **overrides) -> dict:
        payload = self.request(**overrides).__dict__.copy()
        payload["schema_version"] = PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION
        return payload

    def assert_metadata_only(self, data: dict) -> None:
        self.assertTrue(data["human_review_required"])
        for field_name in (
            "install_performed",
            "package_manager_called",
            "network_called",
            "process_started",
            "shell_called",
            "provider_called",
            "browser_opened",
            "git_action_performed",
            "dependency_file_modified",
            "package_metadata_fetched",
            "approval_created",
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_install",
            "can_execute",
            "can_write",
            "can_push",
            "can_call_provider",
            "can_change_gate",
        ):
            self.assertFalse(data[field_name])


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
            for alias in node.names:
                full_name = f"{node.module}.{alias.name}"
                imports.add(full_name)
                aliases[alias.asname or alias.name] = full_name
        elif isinstance(node, ast.Call):
            name = call_name(node.func, aliases)
            if name:
                calls.add(name)
    return type("Scan", (), {"imports": imports, "calls": calls})


def call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parts = attribute_parts(node)
        if not parts:
            return ""
        return ".".join((aliases.get(parts[0], parts[0]), *parts[1:]))
    return ""


def attribute_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*attribute_parts(node.value), node.attr)
    return ()


if __name__ == "__main__":
    unittest.main()
