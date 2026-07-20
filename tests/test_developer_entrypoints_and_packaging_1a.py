from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
import zipfile

from runtime.developer_entrypoints import (
    DeveloperEntrypointError,
    _explicit_new_output_root,
    offline_prototype_main,
    run_developer_smoke_test,
    verify_artifacts_main,
    verify_current_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DeveloperEntrypointsAndPackagingTests(unittest.TestCase):
    def test_packaging_declares_canonical_and_compatibility_imports(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            config["build-system"],
            {
                "requires": [],
                "build-backend": "aoia_build_backend",
                "backend-path": ["build_support"],
            },
        )
        project = config["project"]
        self.assertEqual(project["requires-python"], ">=3.12")
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(
            project["scripts"],
            {
                "aoia-knowledge-chat": "runtime.developer_entrypoints:knowledge_chat_main",
                "aoia-knowledge-hub": "runtime.developer_entrypoints:knowledge_hub_main",
                "aoia-knowledge-query": "runtime.developer_entrypoints:knowledge_query_main",
                "aoia-offline-prototype": "runtime.developer_entrypoints:offline_prototype_main",
                "aoia-smoke-test": "runtime.developer_entrypoints:smoke_test_main",
                "aoia-verify-artifacts": "runtime.developer_entrypoints:verify_artifacts_main",
            },
        )
        packages = set(config["tool"]["setuptools"]["packages"])
        for package in (
            "runtime",
            "runtime.retrieval.linux",
            "runtime.memory_hats",
            "runtime.knowledge",
            "runtime.knowledge_modules",
            "retrieval.linux",
            "memory_hats",
            "knowledge",
            "knowledge_modules",
        ):
            self.assertIn(package, packages)

    def test_local_editable_backend_is_dependency_free_and_deterministic(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "build_support"))
        try:
            import aoia_build_backend as backend
        finally:
            sys.path.pop(0)
        self.assertEqual(backend.get_requires_for_build_editable(), [])
        with tempfile.TemporaryDirectory(prefix="aoia-wheel-one-") as first:
            with tempfile.TemporaryDirectory(prefix="aoia-wheel-two-") as second:
                first_name = backend.build_editable(first)
                second_name = backend.build_editable(second)
                first_bytes = (Path(first) / first_name).read_bytes()
                second_bytes = (Path(second) / second_name).read_bytes()
                self.assertEqual(first_bytes, second_bytes)
                with zipfile.ZipFile(Path(first) / first_name) as archive:
                    names = set(archive.namelist())
                    self.assertIn("aoia_core_editable.pth", names)
                    self.assertIn("aoia_core-0.1.0.dist-info/entry_points.txt", names)
                    entry_points = archive.read(
                        "aoia_core-0.1.0.dist-info/entry_points.txt"
                    ).decode("utf-8")
                    self.assertIn(
                        "aoia-knowledge-chat = runtime.developer_entrypoints:knowledge_chat_main",
                        entry_points,
                    )
                    self.assertIn(
                        "aoia-knowledge-hub = runtime.developer_entrypoints:knowledge_hub_main",
                        entry_points,
                    )
                    self.assertIn(
                        "aoia-knowledge-query = runtime.developer_entrypoints:knowledge_query_main",
                        entry_points,
                    )
                    editable_paths = archive.read("aoia_core_editable.pth").decode("utf-8").splitlines()
                    self.assertEqual(editable_paths, [str(ROOT), str(ROOT / "runtime")])

    def test_compatibility_requirements_has_no_second_dependency_set(self) -> None:
        lines = (ROOT / "runtime/requirements.txt").read_text(encoding="utf-8").splitlines()
        self.assertFalse([line for line in lines if line.strip() and not line.lstrip().startswith("#")])

    def test_smoke_imports_all_hat_surfaces_and_is_inert(self) -> None:
        result = run_developer_smoke_test(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["authority_status"], "NON_AUTHORITATIVE")
        self.assertFalse(result["can_approve"])
        self.assertFalse(result["can_dispatch"])
        self.assertFalse(result["can_execute"])
        self.assertFalse(result["can_write"])
        self.assertEqual(
            result["entrypoints"],
            [
                "aoia-knowledge-chat",
                "aoia-knowledge-hub",
                "aoia-knowledge-query",
                "aoia-offline-prototype",
                "aoia-smoke-test",
                "aoia-verify-artifacts",
            ],
        )
        self.assertIn("runtime.retrieval.linux", result["imported_modules"])
        self.assertIn("runtime.safety.bash_parser", result["imported_modules"])
        self.assertIn("runtime.knowledge", result["imported_modules"])
        self.assertIn("runtime.knowledge_modules", result["imported_modules"])
        self.assertIn("runtime.memory_hats.unix_hat", result["imported_modules"])

    def test_artifact_verifier_is_read_only_and_complete(self) -> None:
        protected = (
            ROOT / "data/architect_handoff_manifest_1a.json",
            ROOT / "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json",
            ROOT / "data/unix_retrieval_adapter_1a/index/index_manifest.json",
            ROOT / "data/unix_hat_routing_1a/unix_hat_descriptor.json",
            ROOT / "data/visible_unix_prototype_1a/demo_manifest.json",
            ROOT / "data/unix_full_validation_freeze_1a_r1/freeze_manifest.json",
        )
        before = tuple((_sha256(path), path.stat().st_mtime_ns) for path in protected)
        result = verify_current_artifacts(ROOT)
        after = tuple((_sha256(path), path.stat().st_mtime_ns) for path in protected)
        self.assertEqual(before, after)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["freeze_id"], "aoia-unix-unit-1a-r1")
        self.assertFalse(result["can_write"])

    def test_offline_prototype_writes_only_to_explicit_new_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aoia-entrypoint-test-") as temporary:
            output = Path(temporary) / "offline-review"
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                status = offline_prototype_main(
                    ("--repository-root", str(ROOT), "--output-root", str(output))
                )
            self.assertEqual(status, 0)
            payload = json.loads(stream.getvalue())
            self.assertEqual(payload["status"], "VALID")
            self.assertFalse(payload["can_execute"])
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "demo_manifest.json").is_file())

    def test_output_root_rejects_relative_traversal_and_existing_path(self) -> None:
        with self.assertRaises(DeveloperEntrypointError):
            _explicit_new_output_root("relative/output")
        with self.assertRaises(DeveloperEntrypointError):
            _explicit_new_output_root("/tmp/aoia/../escape")
        with tempfile.TemporaryDirectory(prefix="aoia-entrypoint-existing-") as temporary:
            with self.assertRaises(DeveloperEntrypointError):
                _explicit_new_output_root(temporary)

    def test_output_root_rejects_symlink_components(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aoia-entrypoint-link-") as temporary:
            real = Path(temporary) / "real"
            real.mkdir()
            link = Path(temporary) / "link"
            os.symlink(real, link)
            with self.assertRaises(DeveloperEntrypointError):
                _explicit_new_output_root(link / "output")

    def test_missing_repository_data_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aoia-entrypoint-missing-") as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text("[project]\nname='missing'\n", encoding="utf-8")
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                status = verify_artifacts_main(("--repository-root", str(root)))
            self.assertEqual(status, 2)
            payload = json.loads(stream.getvalue())
            self.assertEqual(payload["status"], "FAILED_CLOSED")
            self.assertFalse(payload["can_approve"])

    def test_entrypoint_module_adds_no_dangerous_capability_import(self) -> None:
        source = (ROOT / "runtime/developer_entrypoints.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(
            imported.isdisjoint(
                {
                    "aiohttp",
                    "git",
                    "httpx",
                    "requests",
                    "socket",
                    "subprocess",
                    "urllib",
                    "webbrowser",
                }
            )
        )

    def test_readme_contains_exact_real_commands(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        commands = (
            "PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 python -m pip install --no-deps --no-build-isolation -e .",
            "aoia-smoke-test --repository-root .",
            "CI=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test*.py' -q < /dev/null",
            "aoia-offline-prototype --repository-root . --output-root /tmp/aoia-offline-prototype-1a",
            "aoia-verify-artifacts --repository-root .",
        )
        for command in commands:
            self.assertIn(command, readme)


if __name__ == "__main__":
    unittest.main()
