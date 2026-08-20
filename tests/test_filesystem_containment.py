from __future__ import annotations

import os
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.executor import ExecutionEngine
from tools.filesystem_tools import FilesystemContainmentError, resolve_path
from tools.memory import MemoryStore
from tools.validator import validate_action


class FilesystemContainmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temporary_directory.name)
        self.project_root = self.temp_root / "project"
        self.outside_root = self.temp_root / "outside"
        self.project_root.mkdir()
        self.outside_root.mkdir()
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

    def assert_containment_blocked(self, action: dict) -> FilesystemContainmentError:
        with self.assertRaises(FilesystemContainmentError) as raised:
            self.engine.execute(action, require_approval=False)
        error = raised.exception
        self.assertIn("Filesystem containment blocked", str(error))
        self.assertEqual(error.reason_code, "FILESYSTEM_CONTAINMENT_BLOCKED")
        self.assertNotIn(str(self.temp_root), str(error))
        self.assertNotIn(str(self.temp_root), "".join(traceback.format_exception(error)))
        return error

    def test_resolve_path_allows_relative_nested_absolute_inside_and_zero_name(self) -> None:
        nested = self.project_root / "subdir"
        nested.mkdir()

        self.assertEqual(
            resolve_path("./file.txt", self.project_root, self.project_root),
            self.project_root / "file.txt",
        )
        self.assertEqual(
            resolve_path("subdir/file.txt", self.project_root, self.project_root),
            nested / "file.txt",
        )
        self.assertEqual(
            resolve_path(nested / "absolute.txt", self.project_root, self.project_root),
            nested / "absolute.txt",
        )
        self.assertEqual(
            resolve_path("0", self.project_root, self.project_root),
            self.project_root / "0",
        )
        numeric_zero = validate_action({"action": "read_file", "path": 0})
        self.assertEqual(numeric_zero["path"], "0")

    def test_mkdir_write_read_move_and_delete_work_inside_project(self) -> None:
        mkdir_result = self.engine.execute(
            {"action": "create_folder", "path": "subdir"},
            require_approval=False,
        )
        write_result = self.engine.execute(
            {"action": "write_file", "path": "subdir/file.txt", "content": "inside\n"},
            require_approval=False,
        )
        read_result = self.engine.execute(
            {"action": "read_file", "path": "subdir/file.txt"},
            require_approval=False,
        )
        move_result = self.engine.execute(
            {"action": "move_file", "src": "subdir/file.txt", "dst": "subdir/moved.txt"},
            require_approval=False,
        )
        delete_result = self.engine.execute(
            {"action": "delete_file", "path": "subdir/moved.txt"},
            require_approval=False,
        )

        self.assertTrue(mkdir_result["success"])
        self.assertTrue(write_result["success"])
        self.assertEqual(read_result["content"], "inside\n")
        self.assertTrue(move_result["success"])
        self.assertTrue(delete_result["success"])
        self.assertFalse((self.project_root / "subdir" / "moved.txt").exists())

    def test_change_directory_inside_preserves_project_boundary(self) -> None:
        nested = self.project_root / "nested" / "deeper"
        nested.mkdir(parents=True)

        result = self.engine.execute(
            {"action": "change_directory", "path": "nested/deeper"},
            require_approval=False,
        )

        self.assertTrue(result["success"])
        self.assertEqual(self.engine.cwd, nested)
        self.assertEqual(self.engine.project_dir, self.project_root.resolve())
        self.assertEqual(
            resolve_path("file.txt", self.engine.cwd, self.engine.project_dir),
            nested / "file.txt",
        )

    def test_relative_traversal_escapes_are_blocked(self) -> None:
        for escaped_path in (
            "../outside.txt",
            "../../outside.txt",
            "nested/../../../outside.txt",
        ):
            with self.subTest(path=escaped_path):
                self.assert_containment_blocked(
                    {"action": "write_file", "path": escaped_path, "content": "blocked"}
                )

    def test_absolute_external_path_is_blocked(self) -> None:
        self.assert_containment_blocked(
            {
                "action": "write_file",
                "path": str(self.outside_root / "absolute.txt"),
                "content": "blocked",
            }
        )
        self.assertFalse((self.outside_root / "absolute.txt").exists())

    def test_external_read_write_delete_and_move_destination_are_blocked(self) -> None:
        outside_file = self.outside_root / "secret.txt"
        outside_file.write_text("secret\n", encoding="utf-8")
        inside_file = self.project_root / "inside.txt"
        inside_file.write_text("inside\n", encoding="utf-8")

        actions = (
            {"action": "read_file", "path": str(outside_file)},
            {"action": "write_file", "path": str(outside_file), "content": "changed"},
            {"action": "delete_file", "path": str(outside_file)},
            {
                "action": "move_file",
                "src": str(inside_file),
                "dst": str(self.outside_root / "moved.txt"),
            },
        )
        for action in actions:
            with self.subTest(action=action["action"]):
                self.assert_containment_blocked(action)

        self.assertEqual(outside_file.read_text(encoding="utf-8"), "secret\n")
        self.assertTrue(inside_file.exists())
        self.assertFalse((self.outside_root / "moved.txt").exists())

    def test_change_directory_outside_is_blocked_without_mutating_cwd(self) -> None:
        original_cwd = self.engine.cwd

        self.assert_containment_blocked(
            {"action": "change_directory", "path": str(self.outside_root)}
        )

        self.assertEqual(self.engine.cwd, original_cwd)
        self.assertEqual(Path(self.memory.memory.cwd), original_cwd)

    def test_external_cwd_cannot_redefine_security_boundary(self) -> None:
        with self.assertRaises(FilesystemContainmentError):
            resolve_path("file.txt", self.outside_root, self.project_root)

    def test_project_scan_inside_succeeds_and_external_scan_is_blocked(self) -> None:
        (self.project_root / "README.md").write_text("# Project\n", encoding="utf-8")
        inside = self.engine.execute(
            {"action": "scan_project", "path": "."},
            require_approval=False,
        )

        self.assertTrue(inside["success"])
        self.assertEqual(Path(inside["path"]), self.project_root)
        self.assertIn("README.md", inside["project_scan"]["sample_files"])
        self.assert_containment_blocked(
            {"action": "scan_project", "path": str(self.outside_root)}
        )

    def test_symlink_escape_is_blocked_for_tools_search_and_scanner(self) -> None:
        outside_file = self.outside_root / "secret.txt"
        outside_file.write_text("external secret\n", encoding="utf-8")
        (self.project_root / "link").symlink_to(self.outside_root, target_is_directory=True)

        actions = (
            {"action": "read_file", "path": "link/secret.txt"},
            {"action": "write_file", "path": "link/new.txt", "content": "blocked"},
            {"action": "delete_file", "path": "link/secret.txt"},
            {"action": "change_directory", "path": "link"},
            {"action": "scan_project", "path": "link"},
            {"action": "scan_project", "path": "."},
            {"action": "search_in_project", "path": ".", "pattern": "secret"},
        )
        for action in actions:
            with self.subTest(action=action["action"], path=action["path"]):
                self.assert_containment_blocked(action)

        self.assertEqual(outside_file.read_text(encoding="utf-8"), "external secret\n")
        self.assertFalse((self.outside_root / "new.txt").exists())

    def test_browser_file_inputs_use_the_same_containment_boundary(self) -> None:
        self.assert_containment_blocked(
            {"action": "browser_open", "url": (self.outside_root / "secret.html").as_uri()}
        )
        self.assert_containment_blocked(
            {"action": "browser_screenshot", "path": str(self.outside_root / "shot.png")}
        )

    def test_missing_project_root_fails_closed(self) -> None:
        with self.assertRaisesRegex(FilesystemContainmentError, "configured project root"):
            resolve_path("file.txt", self.project_root)


if __name__ == "__main__":
    unittest.main()
