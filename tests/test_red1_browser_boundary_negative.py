"""
RED-1-E browser/web-reader boundary negative tests.
These tests do not launch browsers.
They do not fetch URLs.
They verify that current import-safe proposal/router paths do not import or invoke
browser/web-reader surfaces.
This file targets RED-1 BLOCKER-04 only.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import socket
import subprocess
import sys
import unittest
import urllib.request
import webbrowser
from contextlib import ExitStack
from unittest.mock import patch

from runtime.model_catalog import get_static_model_catalog_payload
from runtime.model_router import create_model_selection_proposal, evaluate_model_selection_policy
from runtime.schemas.chat4_agentic_proposals import Chat4HatTarget, HatUpdateProposal
from runtime.schemas.model_router import RoutingDecisionStatus, TaskSensitivity


BROWSER_MODULES = {
    "runtime.tools.browser_tools",
    "runtime.tools.web_reader",
    "playwright",
    "selenium",
}


def helper_bot_proposal() -> dict[str, object]:
    return {
        "source": "helper_bot",
        "execution_permitted": False,
        "human_review_required": True,
        "canonical": False,
        "canonical_status": "NOT_CANONICAL",
        "provider_output_trusted": False,
        "requested_action": "browser_read_visible_text",
        "target": "https://example.invalid/review-only",
    }


def helper_hat_update_proposal() -> HatUpdateProposal:
    return HatUpdateProposal(
        update_id="red1e-update-1",
        target_hat=Chat4HatTarget.HAT_004_BROWSER_FILE_GOVERNANCE,
        target_record_id="record-1",
        proposed_diff_text="+ browser-boundary draft only; not executable",
        rationale="Diagnostic proposal construction only.",
        risk_class="review_required",
        source_ids=("source-1",),
    )


def browser_modules_loaded() -> set[str]:
    return BROWSER_MODULES.intersection(sys.modules)


def assert_no_new_browser_imports(test_case: unittest.TestCase, before: set[str]) -> None:
    after = browser_modules_loaded()
    new_imports = after - before
    test_case.assertFalse(new_imports, f"browser/web-reader modules imported by tested path: {sorted(new_imports)}")


def patched_dangerous_primitives():
    stack = ExitStack()
    mocks = {
        "urlopen": stack.enter_context(
            patch.object(urllib.request, "urlopen", side_effect=AssertionError("urllib.request.urlopen called"))
        ),
        "socket": stack.enter_context(
            patch.object(socket, "create_connection", side_effect=AssertionError("socket.create_connection called"))
        ),
        "webbrowser": stack.enter_context(
            patch.object(webbrowser, "open", side_effect=AssertionError("webbrowser.open called"))
        ),
        "popen": stack.enter_context(
            patch.object(subprocess, "Popen", side_effect=AssertionError("subprocess.Popen called"))
        ),
        "run": stack.enter_context(
            patch.object(subprocess, "run", side_effect=AssertionError("subprocess.run called"))
        ),
        "system": stack.enter_context(
            patch.object(os, "system", side_effect=AssertionError("os.system called"))
        ),
    }
    if importlib.util.find_spec("requests") is not None:
        requests = importlib.import_module("requests")
        mocks["requests_get"] = stack.enter_context(
            patch.object(requests, "get", side_effect=AssertionError("requests.get called"))
        )
        mocks["requests_post"] = stack.enter_context(
            patch.object(requests, "post", side_effect=AssertionError("requests.post called"))
        )
    return stack, mocks


class Red1BrowserBoundaryNegativeTests(unittest.TestCase):
    def test_helper_proposal_schema_construction_does_not_import_browser_modules(self) -> None:
        before = browser_modules_loaded()
        stack, mocks = patched_dangerous_primitives()

        with stack:
            proposal = helper_bot_proposal()
            schema_object = helper_hat_update_proposal()

        self.assertEqual("helper_bot", proposal["source"])
        self.assertFalse(proposal["execution_permitted"])
        self.assertFalse(schema_object.execution_permitted)
        assert_no_new_browser_imports(self, before)
        for mock in mocks.values():
            mock.assert_not_called()

    def test_model_catalog_and_router_proposal_paths_do_not_import_browser_modules(self) -> None:
        before = browser_modules_loaded()
        stack, mocks = patched_dangerous_primitives()

        with stack:
            catalog = get_static_model_catalog_payload()
            proposal = create_model_selection_proposal(
                provider_id="gemini",
                model_id="gemini/gemini-2.5-flash",
                task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
                user_prompt="public browser-boundary diagnostic prompt",
            )
            decision = evaluate_model_selection_policy(proposal=proposal)

        self.assertFalse(catalog["provider_call_permitted"])
        self.assertFalse(proposal["provider_call_permitted"])
        self.assertEqual(RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL.value, decision["status"])
        assert_no_new_browser_imports(self, before)
        for mock in mocks.values():
            mock.assert_not_called()

    def test_browser_web_reader_specs_are_visible_audit_surfaces_not_imported_by_spec_check(self) -> None:
        before = browser_modules_loaded()

        browser_spec = importlib.util.find_spec("runtime.tools.browser_tools")
        web_reader_spec = importlib.util.find_spec("runtime.tools.web_reader")

        assert_no_new_browser_imports(self, before)
        self.assertIsNotNone(
            browser_spec or web_reader_spec,
            "expected browser/web-reader modules to remain visible audit surfaces",
        )

    def test_no_web_fetch_happens_through_import_safe_paths(self) -> None:
        before = browser_modules_loaded()
        stack, mocks = patched_dangerous_primitives()

        with stack:
            proposal = helper_bot_proposal()
            catalog = get_static_model_catalog_payload()

        self.assertEqual("browser_read_visible_text", proposal["requested_action"])
        self.assertFalse(catalog["provider_call_permitted"])
        assert_no_new_browser_imports(self, before)
        mocks["urlopen"].assert_not_called()
        mocks["socket"].assert_not_called()
        if "requests_get" in mocks:
            mocks["requests_get"].assert_not_called()
            mocks["requests_post"].assert_not_called()

    def test_no_browser_launch_primitive_is_invoked_by_import_safe_paths(self) -> None:
        before = browser_modules_loaded()
        stack, mocks = patched_dangerous_primitives()

        with stack:
            proposal = create_model_selection_proposal(
                provider_id="local",
                model_id="local/manual-model",
                task_sensitivity=TaskSensitivity.PUBLIC_DEV.value,
                user_prompt="public browser-boundary diagnostic prompt",
            )
            decision = evaluate_model_selection_policy(proposal=proposal)

        self.assertFalse(proposal["provider_call_permitted"])
        self.assertEqual(RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL.value, decision["status"])
        assert_no_new_browser_imports(self, before)
        mocks["webbrowser"].assert_not_called()
        mocks["popen"].assert_not_called()
        mocks["run"].assert_not_called()
        mocks["system"].assert_not_called()

    def test_hat004_browser_action_schema_construction_is_inert_and_does_not_import_browser_modules(self) -> None:
        before = browser_modules_loaded()
        stack, mocks = patched_dangerous_primitives()

        with stack:
            from runtime.schemas.hat004_action_proposals import Hat004ActionDomain, Hat004ActionProposal

            proposal = Hat004ActionProposal(
                action_type="browser_read_visible_text",
                target="https://example.invalid/review-only",
                reason="schema construction only",
                source="unit_test",
                created_by="red1e",
            )

        self.assertEqual(Hat004ActionDomain.BROWSER, proposal.domain)
        self.assertTrue(proposal.proposal_only)
        self.assertFalse(proposal.execution_permitted)
        assert_no_new_browser_imports(self, before)
        for mock in mocks.values():
            mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
