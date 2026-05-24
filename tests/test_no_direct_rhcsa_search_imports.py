from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COORDINATOR_MODULES = (
    "runtime/commands/local_commands.py",
    "runtime/adaptive_routing/epistemic_kernel.py",
    "runtime/orchestrator/knowledge_router.py",
    "runtime/main.py",
)


class NoDirectRHCSASearchImportsTests(unittest.TestCase):
    def test_coordinators_do_not_import_low_level_rhcsa_search(self) -> None:
        offenders: list[str] = []
        for relative_path in COORDINATOR_MODULES:
            source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
            if "from tools.rhcsa_search" in source or "import tools.rhcsa_search" in source:
                offenders.append(relative_path)

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
