import unittest
from dataclasses import FrozenInstanceError

from adaptive_routing.config_loader import load_config
from adaptive_routing.deterministic_router import select_depth
from adaptive_routing.stdout_logger import new_correlation_id


class AOIADeterminismTests(unittest.TestCase):
    def test_select_depth_is_deterministic_for_same_input(self) -> None:
        for pressure in (0, 1, 33, 34, 50, 66, 67, 100):
            first = select_depth(pressure)
            second = select_depth(pressure)
            self.assertEqual(first, second)

    def test_select_depth_thresholds_are_stable(self) -> None:
        expected = {
            0: "shallow",
            33: "shallow",
            34: "mid",
            66: "mid",
            67: "deep",
            100: "deep",
        }
        for pressure, depth in expected.items():
            self.assertEqual(select_depth(pressure), depth)

    def test_select_depth_rejects_negative_pressure(self) -> None:
        with self.assertRaises(ValueError):
            select_depth(-1)

    def test_config_is_readonly_after_loading(self) -> None:
        config = load_config()
        with self.assertRaises(FrozenInstanceError):
            config.mid_max = 99
        with self.assertRaises(TypeError):
            config.runtime_policy["mutable_at_runtime"] = True

    def test_config_load_is_deterministic(self) -> None:
        first = load_config()
        second = load_config()
        self.assertEqual(first.version, second.version)
        self.assertEqual(first.depths, second.depths)
        self.assertEqual(first.shallow_max, second.shallow_max)
        self.assertEqual(first.mid_max, second.mid_max)
        self.assertEqual(dict(first.runtime_policy), dict(second.runtime_policy))

    def test_correlation_ids_are_not_routing_outputs(self) -> None:
        cid = new_correlation_id()
        self.assertIsInstance(cid, str)
        self.assertEqual(len(cid), 12)


if __name__ == "__main__":
    unittest.main()

