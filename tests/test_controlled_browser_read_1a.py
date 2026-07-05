from __future__ import annotations

import ast
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.browser_ops.controlled_browser_read import (
    BROWSER_READ_CONTEXT_SCHEMA_VERSION,
    BROWSER_READ_HUMAN_BARRIER_SCHEMA_VERSION,
    BROWSER_READ_REQUEST_SCHEMA_VERSION,
    CONTROLLED_BROWSER_READ_BLOCKED,
    CONTROLLED_BROWSER_READ_BLOCKED_AUTHORITY_CLAIM,
    CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_HASH_MISMATCH,
    CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_SCOPE_MISMATCH,
    CONTROLLED_BROWSER_READ_BLOCKED_HASH_MISMATCH,
    CONTROLLED_BROWSER_READ_BLOCKED_MALFORMED_EVIDENCE,
    CONTROLLED_BROWSER_READ_BLOCKED_NON_OFFLINE_CONTEXT,
    CONTROLLED_BROWSER_READ_BLOCKED_STALE_EVIDENCE,
    CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_HTML,
    CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_SOURCE,
    CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_EXTRACTOR,
    CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_SOURCE,
    CONTROLLED_BROWSER_READ_REASON_SNAPSHOT_CREATED,
    CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED,
    BrowserReadHumanBarrier,
    ControlledBrowserReadContext,
    ControlledBrowserReadRequest,
    compute_browser_read_barrier_hash,
    compute_browser_read_context_hash,
    compute_browser_read_request_hash,
    compute_browser_read_source_hash,
    compute_browser_read_text_hash,
    create_browser_read_human_barrier,
    create_controlled_browser_read_context,
    create_controlled_browser_read_request,
    execute_controlled_browser_read,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "browser_ops" / "controlled_browser_read.py"


class ControlledBrowserRead1ATests(unittest.TestCase):
    def test_inline_html_snapshot_extracts_inert_metadata_only(self):
        with self.evidence() as evidence:
            result = execute_controlled_browser_read(
                request=evidence.request,
                context=evidence.context,
                human_barrier=evidence.barrier,
            )

            self.assertEqual(CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED, result.status)
            self.assertEqual((CONTROLLED_BROWSER_READ_REASON_SNAPSHOT_CREATED,), result.reason_codes)
            self.assertEqual("Example Title", result.title)
            self.assertEqual(compute_browser_read_text_hash("Example Title Hello world Read"), result.text_hash)
            self.assertEqual(("https://example.invalid/read",), result.links)
            self.assertTrue(result.inline_html_read)
            self.assertFalse(result.local_file_read)
            self.assert_metadata_only(result.to_dict(), snapshot=True, inline=True)

    def test_sandbox_file_snapshot_reads_only_local_html_inside_sandbox(self):
        with self.evidence(source_kind="sandbox_file") as evidence:
            result = execute_controlled_browser_read(
                request=evidence.request,
                context=evidence.context,
                human_barrier=evidence.barrier,
            )

            self.assertEqual(CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED, result.status)
            self.assertEqual("Example Title", result.title)
            self.assertTrue(result.local_file_read)
            self.assertFalse(result.inline_html_read)
            self.assert_metadata_only(result.to_dict(), snapshot=True, local=True)

    def test_missing_malformed_stale_and_unsupported_evidence_fails_closed(self):
        with self.evidence() as evidence:
            unsupported_source = self.request(evidence, source_kind="remote_url", source_locator="https://example.invalid")
            unsupported_extractor = self.request(evidence, allowed_extractors=("title", "screenshot"))
            stale_request = self.request(evidence, requested_at=1, expires_at=5)
            non_offline_context = replace(evidence.context, network_disabled=False)

            cases = (
                (None, evidence.context, evidence.barrier, CONTROLLED_BROWSER_READ_BLOCKED_MALFORMED_EVIDENCE),
                (unsupported_source, evidence.context, self.barrier(evidence, request=unsupported_source), CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_SOURCE),
                (unsupported_extractor, evidence.context, self.barrier(evidence, request=unsupported_extractor, approved_extractors=("title", "screenshot")), CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_EXTRACTOR),
                (stale_request, evidence.context, self.barrier(evidence, request=stale_request), CONTROLLED_BROWSER_READ_BLOCKED_STALE_EVIDENCE),
                (evidence.request, non_offline_context, evidence.barrier, CONTROLLED_BROWSER_READ_BLOCKED_NON_OFFLINE_CONTEXT),
            )
            for request, context, barrier, reason in cases:
                with self.subTest(reason=reason):
                    result = execute_controlled_browser_read(
                        request=request,
                        context=context,
                        human_barrier=barrier,
                    )

                    self.assertEqual(CONTROLLED_BROWSER_READ_BLOCKED, result.status)
                    self.assertIn(reason, result.reason_codes)
                    self.assert_metadata_only(result.to_dict())

    def test_hash_and_barrier_scope_mismatch_fails_closed(self):
        with self.evidence() as evidence:
            changed_source = self.html.replace("Hello", "Changed")
            wrong_request_hash = {**evidence.request.to_dict(), "request_hash": "0" * 64}
            wrong_barrier_hash = {**evidence.barrier.to_dict(), "barrier_hash": "1" * 64}
            wrong_scope_barrier = self.barrier(evidence, source_hash=compute_browser_read_source_hash(changed_source))

            cases = (
                (wrong_request_hash, evidence.barrier, CONTROLLED_BROWSER_READ_BLOCKED_HASH_MISMATCH),
                (evidence.request, wrong_barrier_hash, CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_HASH_MISMATCH),
                (evidence.request, wrong_scope_barrier, CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_SCOPE_MISMATCH),
            )
            for request, barrier, reason in cases:
                with self.subTest(reason=reason):
                    result = execute_controlled_browser_read(
                        request=request,
                        context=evidence.context,
                        human_barrier=barrier,
                    )

                    self.assertEqual(CONTROLLED_BROWSER_READ_BLOCKED, result.status)
                    self.assertIn(reason, result.reason_codes)

    def test_sandbox_file_outside_sandbox_remote_or_hash_mismatch_fails_closed(self):
        with self.evidence(source_kind="sandbox_file") as evidence:
            outside = evidence.root / "outside.html"
            outside.write_text(self.html, encoding="utf-8")
            outside_request = self.request(evidence, source_kind="sandbox_file", source_locator=str(outside))
            remote_request = self.request(evidence, source_kind="sandbox_file", source_locator="https://example.invalid/page.html")
            wrong_hash = self.request(evidence, expected_source_hash="f" * 64)

            cases = (
                (outside_request, CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_SOURCE),
                (remote_request, CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_SOURCE),
                (wrong_hash, CONTROLLED_BROWSER_READ_BLOCKED_HASH_MISMATCH),
            )
            for request, reason in cases:
                with self.subTest(reason=reason):
                    result = execute_controlled_browser_read(
                        request=request,
                        context=evidence.context,
                        human_barrier=self.barrier(evidence, request=request),
                    )

                    self.assertEqual(CONTROLLED_BROWSER_READ_BLOCKED, result.status)
                    self.assertIn(reason, result.reason_codes)
                    self.assert_metadata_only(result.to_dict())

    def test_scripts_forms_remote_resources_and_mutable_html_fail_closed(self):
        unsafe_html = (
            "<html><script>alert(1)</script></html>",
            '<html><body onload="x()">x</body></html>',
            '<form action="/submit"><input name="q"></form>',
            '<img src="https://example.invalid/pixel.png">',
            '<a href="javascript:alert(1)">bad</a>',
        )
        with self.evidence() as evidence:
            for html in unsafe_html:
                with self.subTest(html=html):
                    request = self.request(evidence, source_locator=html, expected_source_hash=compute_browser_read_source_hash(html))
                    result = execute_controlled_browser_read(
                        request=request,
                        context=evidence.context,
                        human_barrier=self.barrier(evidence, request=request, source_hash=compute_browser_read_source_hash(html)),
                    )

                    self.assertEqual(CONTROLLED_BROWSER_READ_BLOCKED, result.status)
                    self.assertIn(CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_HTML, result.reason_codes)
                    self.assert_metadata_only(result.to_dict())

    def test_authority_claims_cannot_substitute_for_barrier_or_enable_result_authority(self):
        with self.evidence() as evidence:
            forged_barrier = {"approved": True, "safe": True, "can_browse": True, "authority": True}
            forced_request = replace(evidence.request, can_browse=True, can_click=True, gate_satisfied=True)
            forced_barrier = replace(evidence.barrier, can_browse=True, can_click=True, gate_satisfied=True)

            malformed = execute_controlled_browser_read(
                request=evidence.request,
                context=evidence.context,
                human_barrier=forged_barrier,
            )
            self.assertEqual(CONTROLLED_BROWSER_READ_BLOCKED, malformed.status)
            self.assertIn(CONTROLLED_BROWSER_READ_BLOCKED_MALFORMED_EVIDENCE, malformed.reason_codes)

            result = execute_controlled_browser_read(
                request=forced_request,
                context=evidence.context,
                human_barrier=forced_barrier,
            )
            self.assertEqual(CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED, result.status)
            self.assertFalse(forced_request.can_browse)
            self.assertFalse(forced_barrier.can_click)
            self.assert_metadata_only(result.to_dict(), snapshot=True, inline=True)

            authority_barrier = {**evidence.barrier.to_dict(), "can_browse": True}
            blocked = execute_controlled_browser_read(
                request=evidence.request,
                context=evidence.context,
                human_barrier=authority_barrier,
            )
            self.assertEqual(CONTROLLED_BROWSER_READ_BLOCKED, blocked.status)
            self.assertIn(CONTROLLED_BROWSER_READ_BLOCKED_AUTHORITY_CLAIM, blocked.reason_codes)

    def test_result_hash_is_deterministic_and_changes_with_snapshot_material(self):
        with self.evidence() as evidence:
            first = execute_controlled_browser_read(request=evidence.request, context=evidence.context, human_barrier=evidence.barrier)
            second = execute_controlled_browser_read(request=evidence.request, context=evidence.context, human_barrier=evidence.barrier)
            html = self.html.replace("world", "reader")
            changed_request = self.request(evidence, source_locator=html, expected_source_hash=compute_browser_read_source_hash(html))
            changed = execute_controlled_browser_read(
                request=changed_request,
                context=evidence.context,
                human_barrier=self.barrier(evidence, request=changed_request, source_hash=compute_browser_read_source_hash(html)),
            )

            self.assertEqual(first.result_hash, second.result_hash)
            self.assertNotEqual(first.result_hash, changed.result_hash)

    def test_module_static_surface_is_local_parser_only(self):
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
            "runtime.package_ops.controlled_package_install",
            "runtime.git_ops",
        ):
            self.assertNotIn(forbidden_import, scan.imports)
        for forbidden_call in (
            "subprocess.run",
            "subprocess.Popen",
            "eval",
            "exec",
            "__import__",
        ):
            self.assertNotIn(forbidden_call, scan.calls)
        for forbidden_text in (
            "shell=true",
            "os.environ",
            "getenv",
            "api_key",
            "webdriver",
            "playwright",
            "selenium",
            "webbrowser",
            ".write_text(",
            ".write_bytes(",
        ):
            self.assertNotIn(forbidden_text, source)

    def evidence(self, **overrides):
        return EvidenceContext(self, **overrides)

    def request(self, evidence, **overrides) -> ControlledBrowserReadRequest:
        source_kind = overrides.pop("source_kind", evidence.source_kind)
        source_locator = overrides.pop("source_locator", str(evidence.html_file) if source_kind == "sandbox_file" else self.html)
        expected_source_hash = overrides.pop("expected_source_hash", compute_browser_read_source_hash(self.html))
        values = {
            "source_kind": source_kind,
            "source_locator": source_locator,
            "expected_source_hash": expected_source_hash,
            "reason": "Review local read-only HTML snapshot.",
            "requested_by": "local-human-operator",
            "requested_at": 10,
            "expires_at": 20,
            "allowed_extractors": ("title", "text_hash", "links"),
        }
        values.update(overrides)
        return create_controlled_browser_read_request(**values)

    def barrier(self, evidence, **overrides) -> BrowserReadHumanBarrier:
        request = overrides.pop("request", evidence.request)
        source_hash = overrides.pop("source_hash", request.expected_source_hash)
        values = {
            "request_hash": request.request_hash,
            "context_hash": evidence.context.context_hash,
            "source_hash": source_hash,
            "source_kind": request.source_kind,
            "approved_extractors": request.allowed_extractors,
            "approved_by": "local-human-operator",
            "approval_reason": "Approve local read-only HTML snapshot only.",
            "approved_at": 10,
            "expires_at": 20,
        }
        values.update(overrides)
        return create_browser_read_human_barrier(**values)

    @property
    def html(self) -> str:
        return '<html><head><title>Example Title</title></head><body><p>Hello world</p><a href="https://example.invalid/read">Read</a></body></html>'

    def assert_metadata_only(self, data: dict, *, snapshot: bool = False, inline: bool = False, local: bool = False) -> None:
        self.assertEqual(snapshot, data["snapshot_created"])
        self.assertEqual(inline, data["inline_html_read"])
        self.assertEqual(local, data["local_file_read"])
        for field_name in (
            "browser_opened",
            "browser_action_performed",
            "network_called",
            "remote_resource_loaded",
            "javascript_executed",
            "link_followed",
            "form_submitted",
            "download_performed",
            "cookie_mutated",
            "storage_mutated",
            "file_written",
            "provider_called",
            "git_action_performed",
            "package_installed",
            "approval_created",
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_browse",
            "can_click",
            "can_download",
            "can_execute",
            "can_write",
            "can_call_provider",
            "can_change_gate",
            "future_browser_action_authorized",
        ):
            self.assertFalse(data[field_name])


class EvidenceContext:
    def __init__(self, testcase: ControlledBrowserRead1ATests, *, source_kind: str = "inline_html") -> None:
        self.testcase = testcase
        self.source_kind = source_kind

    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sandbox = self.root / "sandbox"
        self.sandbox.mkdir()
        self.html_file = self.sandbox / "fixture.html"
        self.html_file.write_text(self.testcase.html, encoding="utf-8")
        self.context = create_controlled_browser_read_context(
            current_tick=15,
            sandbox_root=str(self.sandbox),
        )
        self.request = self.testcase.request(self)
        self.barrier = self.testcase.barrier(self)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.temp.cleanup()
        return False


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
