from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import tools.executor as executor_module
from tools.capability_policy import (
    ACTION_POLICY_RULES,
    POLICY_ACTIONS,
    ActionPolicyDecision,
    CapabilityClass,
    evaluate_action_policy,
)
from tools.executor import ExecutionEngine, ToolSpec
from tools.memory import MemoryStore
from tools.validator import ALLOWED_ACTIONS


class CapabilityApprovalPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temporary_directory.name)
        self.project_root = self.temp_root / "project"
        self.project_root.mkdir()
        self.environment = patch.dict(
            os.environ,
            {
                "AOIA_HOME": str(self.temp_root / "aoia-state"),
                "AOIA_LEGACY_FILESYSTEM_ENABLED": "1",
            },
        )
        self.environment.start()
        self.memory = MemoryStore(self.project_root, self.project_root)
        self.engine = ExecutionEngine(self.project_root, self.memory)

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_filesystem_false_cannot_bypass_runtime_approval(self) -> None:
        events: list[str] = []
        action = {
            "action": "write_file",
            "path": "result.txt",
            "content": "approved",
            "requires_confirmation": False,
        }

        def approve(_action: dict, decision: ActionPolicyDecision) -> bool:
            events.append("approval")
            self.assertTrue(decision.runtime_requires_confirmation)
            self.assertFalse(decision.model_requests_confirmation)
            return True

        def dispatch(*_args, **_kwargs) -> dict:
            events.append("dispatch")
            return {"success": True}

        with (
            patch.object(self.engine, "_request_approval", side_effect=approve) as approval,
            patch.object(executor_module, "write_file", side_effect=dispatch) as write,
        ):
            result = self.engine.execute(action, require_approval=False)

        self.assertTrue(result["success"])
        self.assertEqual(events, ["approval", "dispatch"])
        approval.assert_called_once()
        write.assert_called_once()

    def test_filesystem_omission_cannot_bypass_runtime_approval(self) -> None:
        action = {
            "action": "create_file",
            "path": "result.txt",
            "content": "approved",
        }
        with (
            patch.object(self.engine, "_request_approval", return_value=True) as approval,
            patch.object(
                executor_module,
                "create_file",
                return_value={"success": True},
            ) as create,
        ):
            result = self.engine.execute(action)

        self.assertTrue(result["success"])
        decision = approval.call_args.args[1]
        self.assertTrue(decision.runtime_requires_confirmation)
        self.assertFalse(decision.model_requests_confirmation)
        approval.assert_called_once()
        create.assert_called_once()

    def test_declined_filesystem_action_has_zero_underlying_side_effects(self) -> None:
        target = self.project_root / "target.txt"
        target.write_text("original\n", encoding="utf-8")
        command_logs_before = tuple(self.memory.paths.command_logs_dir.iterdir())

        with (
            patch.object(self.engine, "_request_approval", return_value=False) as approval,
            patch.object(
                executor_module,
                "write_file",
                side_effect=AssertionError("filesystem handler dispatched"),
            ) as write,
        ):
            result = self.engine.execute(
                {
                    "action": "write_file",
                    "path": "target.txt",
                    "content": "changed\n",
                    "requires_confirmation": False,
                }
            )

        self.assertFalse(result["success"])
        self.assertFalse(result["allowed"])
        self.assertTrue(result["policy_allowed"])
        self.assertTrue(result["blocked"])
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["result_reason_code"], "HUMAN_APPROVAL_DECLINED")
        self.assertEqual(target.read_text(encoding="utf-8"), "original\n")
        self.assertEqual(tuple(self.memory.paths.command_logs_dir.iterdir()), command_logs_before)
        self.assertFalse(self.memory.memory.recent_outputs)
        approval.assert_called_once()
        write.assert_not_called()

    def test_model_can_escalate_a_genuinely_read_only_action(self) -> None:
        action = {
            "action": "read_file",
            "path": "readme.txt",
            "requires_confirmation": True,
        }
        with (
            patch.object(self.engine, "_request_approval", return_value=True) as approval,
            patch.object(
                executor_module,
                "read_file",
                return_value={"success": True, "content": "read only"},
            ) as read,
        ):
            result = self.engine.execute(action)

        self.assertTrue(result["success"])
        decision = approval.call_args.args[1]
        self.assertEqual(decision.capability_class, CapabilityClass.READ_ONLY)
        self.assertFalse(decision.runtime_requires_confirmation)
        self.assertTrue(decision.model_requests_confirmation)
        self.assertEqual(
            decision.reason_code,
            "MODEL_ESCALATION_REQUIRES_CONFIRMATION",
        )
        approval.assert_called_once()
        read.assert_called_once()

    def test_shell_classifier_confirmation_cannot_be_downgraded(self) -> None:
        handler = Mock(return_value={"success": True})
        self.engine.tools["shell_execute"] = ToolSpec(
            "shell_execute",
            handler,
            "test shell boundary",
        )
        action = {
            "action": "shell_execute",
            "command": "sudo apt install curl",
            "requires_confirmation": False,
        }

        with patch.object(
            self.engine,
            "_request_approval",
            return_value=True,
        ) as approval:
            result = self.engine.execute(action, require_approval=False)

        self.assertTrue(result["success"])
        decision = approval.call_args.args[1]
        self.assertEqual(decision.capability_class, CapabilityClass.CODE_EXECUTION)
        self.assertTrue(decision.runtime_requires_confirmation)
        self.assertFalse(decision.model_requests_confirmation)
        self.assertEqual(
            decision.reason_code,
            "SHELL_RUNTIME_CONFIRMATION_REQUIRED",
        )
        approval.assert_called_once()
        handler.assert_called_once_with(action)

    def test_runtime_blocked_shell_cannot_be_approved_or_dispatched(self) -> None:
        handler = Mock(side_effect=AssertionError("blocked shell handler dispatched"))
        self.engine.tools["shell_execute"] = ToolSpec(
            "shell_execute",
            handler,
            "test shell boundary",
        )
        flag_variants = ({}, {"requires_confirmation": False}, {"requires_confirmation": True})

        for flag_fields in flag_variants:
            with self.subTest(flag_fields=flag_fields):
                action = {
                    "action": "shell_execute",
                    "command": "rm -rf /",
                    **flag_fields,
                }
                with patch.object(
                    self.engine,
                    "_request_approval",
                    return_value=True,
                ) as approval:
                    result = self.engine.execute(action)

                self.assertFalse(result["success"])
                self.assertTrue(result["blocked"])
                self.assertFalse(result["allowed"])
                self.assertEqual(result["policy_reason_code"], "SHELL_COMMAND_BLOCKED")
                approval.assert_not_called()

        handler.assert_not_called()

    def test_browser_false_cannot_bypass_runtime_approval(self) -> None:
        with (
            patch.object(self.engine, "_request_approval", return_value=False) as approval,
            patch.object(
                executor_module,
                "browser_click",
                side_effect=AssertionError("browser handler dispatched"),
            ) as browser_click,
        ):
            result = self.engine.execute(
                {
                    "action": "browser_click",
                    "selector": "#submit",
                    "requires_confirmation": False,
                }
            )

        self.assertFalse(result["success"])
        self.assertFalse(result["allowed"])
        self.assertTrue(result["policy_allowed"])
        self.assertTrue(result["cancelled"])
        decision = approval.call_args.args[1]
        self.assertEqual(decision.capability_class, CapabilityClass.EXTERNAL_INTERACTION)
        self.assertTrue(decision.runtime_requires_confirmation)
        approval.assert_called_once()
        browser_click.assert_not_called()

    def test_unknown_action_fails_closed_even_if_a_handler_is_injected(self) -> None:
        handler = Mock(side_effect=AssertionError("unknown handler dispatched"))
        self.engine.tools["future_unclassified_action"] = ToolSpec(
            "future_unclassified_action",
            handler,
            "unclassified test action",
        )
        with patch.object(
            self.engine,
            "_request_approval",
            return_value=True,
        ) as approval:
            result = self.engine.execute(
                {
                    "action": "future_unclassified_action",
                    "requires_confirmation": True,
                }
            )

        self.assertFalse(result["success"])
        self.assertTrue(result["blocked"])
        self.assertFalse(result["allowed"])
        self.assertEqual(result["capability_class"], CapabilityClass.PRIVILEGED.value)
        self.assertEqual(result["policy_reason_code"], "ACTION_NOT_CLASSIFIED")
        approval.assert_not_called()
        handler.assert_not_called()

    def test_policy_registry_is_complete_and_classifications_are_explicit(self) -> None:
        self.assertEqual(set(ALLOWED_ACTIONS), set(POLICY_ACTIONS))
        self.assertEqual(set(ALLOWED_ACTIONS), set(self.engine.tools))

        expected_classes = {
            "respond": CapabilityClass.READ_ONLY,
            "shell_execute": CapabilityClass.CODE_EXECUTION,
            "write_file": CapabilityClass.FILESYSTEM_MUTATION,
            "append_file": CapabilityClass.FILESYSTEM_MUTATION,
            "read_file": CapabilityClass.READ_ONLY,
            "create_file": CapabilityClass.FILESYSTEM_MUTATION,
            "create_folder": CapabilityClass.FILESYSTEM_MUTATION,
            "move_file": CapabilityClass.FILESYSTEM_MUTATION,
            "delete_file": CapabilityClass.FILESYSTEM_MUTATION,
            "search_in_project": CapabilityClass.READ_ONLY,
            "change_directory": CapabilityClass.LOCAL_STATE_CHANGE,
            "browser_start": CapabilityClass.EXTERNAL_INTERACTION,
            "browser_open": CapabilityClass.EXTERNAL_INTERACTION,
            "browser_click": CapabilityClass.EXTERNAL_INTERACTION,
            "browser_type": CapabilityClass.EXTERNAL_INTERACTION,
            "browser_press": CapabilityClass.EXTERNAL_INTERACTION,
            "browser_read_html": CapabilityClass.EXTERNAL_INTERACTION,
            "browser_get_visible_text": CapabilityClass.EXTERNAL_INTERACTION,
            "browser_screenshot": CapabilityClass.FILESYSTEM_MUTATION,
            "browser_close": CapabilityClass.LOCAL_STATE_CHANGE,
            "browser_current_url": CapabilityClass.EXTERNAL_INTERACTION,
            "scan_project": CapabilityClass.FILESYSTEM_MUTATION,
        }
        self.assertEqual(
            {
                action_name: rule.capability_class
                for action_name, rule in ACTION_POLICY_RULES.items()
            },
            expected_classes,
        )

        for action_name in ALLOWED_ACTIONS:
            with self.subTest(action_name=action_name):
                rule = ACTION_POLICY_RULES[action_name]
                self.assertIsInstance(rule.capability_class, CapabilityClass)
                self.assertTrue(rule.reason_code)
                self.assertTrue(rule.reason)

        self.assertTrue(ACTION_POLICY_RULES["scan_project"].requires_confirmation)
        self.assertTrue(ACTION_POLICY_RULES["browser_screenshot"].requires_confirmation)
        self.assertFalse(ACTION_POLICY_RULES["read_file"].requires_confirmation)
        self.assertFalse(ACTION_POLICY_RULES["search_in_project"].requires_confirmation)

    def test_policy_decision_has_explicit_required_fields(self) -> None:
        decision = evaluate_action_policy({"action": "read_file", "path": "file.txt"})

        self.assertEqual(decision.action_name, "read_file")
        self.assertEqual(decision.capability_class, CapabilityClass.READ_ONLY)
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_confirmation)
        self.assertEqual(decision.reason_code, "READ_ONLY_ALLOWED")


if __name__ == "__main__":
    unittest.main()
