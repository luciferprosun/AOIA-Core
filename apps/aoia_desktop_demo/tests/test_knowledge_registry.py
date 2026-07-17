from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.aoia_desktop_demo.knowledge.registry import (
    NONE_PROFILE_ID,
    discover_profiles,
    find_profile,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


class KnowledgeRegistryTests(unittest.TestCase):
    def test_none_profile_always_present_first(self) -> None:
        profiles = discover_profiles(REPO_ROOT)
        self.assertEqual(profiles[0].id, NONE_PROFILE_ID)

    def test_does_not_invent_a_profile_when_index_missing(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            profiles = discover_profiles(Path(tmp_dir))
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0].id, NONE_PROFILE_ID)

    def test_discovers_real_linux_profile_from_actual_repository(self) -> None:
        profiles = discover_profiles(REPO_ROOT)
        ids = [profile.id for profile in profiles]
        self.assertIn("linux_unix", ids)
        linux_profile = next(p for p in profiles if p.id == "linux_unix")
        self.assertIsInstance(linux_profile.document_count, int)
        self.assertGreater(linux_profile.document_count, 0)
        self.assertFalse(linux_profile.authoritative, "knowledge profiles must never claim authority")

    def test_find_profile_falls_back_to_none(self) -> None:
        profiles = discover_profiles(REPO_ROOT)
        found = find_profile(profiles, "does-not-exist")
        self.assertEqual(found.id, NONE_PROFILE_ID)


if __name__ == "__main__":
    unittest.main()
