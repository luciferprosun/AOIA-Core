from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORENSIC_TEST_DIRECTORY = "archive/forensic_exports/reports_forensic_export/source_export/tests"
FORENSIC_TEST_PATH = REPO_ROOT / FORENSIC_TEST_DIRECTORY
EXPECTED_ARCHIVED_TESTS = (
    "test_aoia_determinism.py",
    "test_epistemic_kernel.py",
    "test_epistemic_registry.py",
    "test_epistemic_safeguards.py",
    "test_executor_containment.py",
    "test_knowledge_validator.py",
    "test_linux_retrieval.py",
    "test_main.py",
    "test_rhcsa_retrieval.py",
    "test_routing_boundary.py",
)


class PytestCollectionBoundary1ATests(unittest.TestCase):
    def test_canonical_pytest_config_excludes_only_the_verified_forensic_test_directory(self) -> None:
        config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        addopts = tuple(config["tool"]["pytest"]["ini_options"]["addopts"])

        self.assertEqual(
            (f"--ignore={FORENSIC_TEST_DIRECTORY}",),
            addopts,
        )
        self.assertNotIn("--ignore=tests", addopts)
        self.assertNotIn("--ignore=tests/adversarial", addopts)

    def test_forensic_test_copies_remain_preserved(self) -> None:
        archived = tuple(sorted(path.name for path in FORENSIC_TEST_PATH.glob("test_*.py")))

        self.assertTrue(FORENSIC_TEST_PATH.is_dir())
        self.assertEqual(EXPECTED_ARCHIVED_TESTS, archived)

    def test_active_same_basename_tests_and_adversarial_tests_remain_in_inventory(self) -> None:
        active = self.active_test_inventory()

        for basename in EXPECTED_ARCHIVED_TESTS:
            self.assertIn(f"tests/{basename}", active)
        self.assertIn("tests/adversarial/test_state_bypass.py", active)
        self.assertIn("tests/adversarial/test_artifact_path_safety.py", active)
        self.assertFalse(any(path.startswith(FORENSIC_TEST_DIRECTORY + "/") for path in active))

    def test_active_test_inventory_is_stable_across_two_runs(self) -> None:
        first = self.active_test_inventory()
        second = self.active_test_inventory()

        self.assertTrue(first)
        self.assertEqual(first, second)

    @staticmethod
    def active_test_inventory() -> tuple[str, ...]:
        return tuple(
            sorted(
                path.relative_to(REPO_ROOT).as_posix()
                for path in REPO_ROOT.rglob("test_*.py")
                if FORENSIC_TEST_PATH not in path.parents
            )
        )


if __name__ == "__main__":
    unittest.main()
