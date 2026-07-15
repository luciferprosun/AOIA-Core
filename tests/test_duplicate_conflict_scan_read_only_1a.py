import builtins
import hashlib
import importlib.util
import os
import pathlib
import stat
import subprocess
import sys
import unittest
from unittest import mock


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN_SCRIPT = (
    PROJECT_ROOT
    / "knowledge"
    / "languages"
    / "python"
    / "audits"
    / "duplicate_conflict_scan"
    / "scan_python_knowledge_duplicates.py"
)
TRACKED_REPORTS = (
    SCAN_SCRIPT.parent / "H21_DUPLICATE_CONFLICT_SCAN_RESULTS.json",
    SCAN_SCRIPT.parent / "H21_DUPLICATE_CONFLICT_SCAN_SUMMARY.md",
)


def load_scan_module():
    module_name = "aoia_duplicate_conflict_scan_read_only_boundary"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, SCAN_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load scan module: {SCAN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def tracked_report_metadata():
    return {
        path.relative_to(PROJECT_ROOT).as_posix(): {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
        for path in TRACKED_REPORTS
    }


def repository_file_state():
    records = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(PROJECT_ROOT)
        if ".git" in relative.parts or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        metadata = path.stat()
        records.append(
            (
                relative.as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest(),
                metadata.st_size,
                metadata.st_mtime_ns,
                stat.S_IMODE(metadata.st_mode),
            )
        )
    return tuple(sorted(records))


class DuplicateConflictScanReadOnlyBoundaryTests(unittest.TestCase):
    def test_import_performs_no_repository_write(self):
        before = tracked_report_metadata()
        before_repository = repository_file_state()
        code = (
            "import importlib.util, pathlib, sys; "
            f"path=pathlib.Path({str(SCAN_SCRIPT)!r}); "
            "spec=importlib.util.spec_from_file_location('aoia_duplicate_import_probe', path); "
            "module=importlib.util.module_from_spec(spec); "
            "sys.modules[spec.name]=module; "
            "spec.loader.exec_module(module)"
        )
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        subprocess.run(
            [sys.executable, "-c", code],
            cwd=PROJECT_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env=environment,
            check=True,
        )
        self.assertEqual(before, tracked_report_metadata())
        self.assertEqual(before_repository, repository_file_state())

    def test_functional_test_discovery_performs_no_repository_write(self):
        before = tracked_report_metadata()
        before_repository = repository_file_state()
        environment = os.environ.copy()
        environment.update(
            {
                "CI": "1",
                "PYTHONUNBUFFERED": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": "runtime:.",
            }
        )
        subprocess.run(
            [sys.executable, "-m", "unittest", "tests.test_python_duplicate_conflict_scan", "-q"],
            cwd=PROJECT_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env=environment,
            check=True,
        )
        self.assertEqual(before, tracked_report_metadata())
        self.assertEqual(before_repository, repository_file_state())

    def test_repository_snapshot_is_git_independent(self):
        forbidden = mock.Mock(side_effect=AssertionError("repository snapshot invoked a process"))
        with mock.patch("subprocess.run", forbidden):
            state = repository_file_state()
        self.assertTrue(state)
        self.assertIn("README.md", {record[0] for record in state})

    def test_scan_verify_and_serialization_are_write_inert(self):
        module = load_scan_module()
        real_open = builtins.open

        def read_only_open(file, mode="r", *args, **kwargs):
            if any(marker in mode for marker in "wax+"):
                raise AssertionError(f"unexpected write-mode open: {file}")
            return real_open(file, mode, *args, **kwargs)

        forbidden = mock.Mock(side_effect=AssertionError("read-only scan attempted mutation"))
        with (
            mock.patch.object(pathlib.Path, "write_text", forbidden),
            mock.patch.object(pathlib.Path, "write_bytes", forbidden),
            mock.patch.object(pathlib.Path, "mkdir", forbidden),
            mock.patch("os.replace", forbidden),
            mock.patch("os.rename", forbidden),
            mock.patch.object(builtins, "open", read_only_open),
        ):
            report = module.scan_duplicate_conflicts()
            self.assertTrue(module.verify_duplicate_conflict_report(report))
            self.assertTrue(module.serialize_duplicate_conflict_report(report))
            self.assertTrue(module.serialize_duplicate_conflict_summary(report))

    def test_tracked_reports_remain_unchanged_across_read_only_operations(self):
        module = load_scan_module()
        before = tracked_report_metadata()
        report = module.scan_duplicate_conflicts()
        module.verify_duplicate_conflict_report(report)
        module.serialize_duplicate_conflict_report(report)
        module.serialize_duplicate_conflict_summary(report)
        self.assertEqual(before, tracked_report_metadata())


if __name__ == "__main__":
    unittest.main()
