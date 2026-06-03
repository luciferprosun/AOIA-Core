from __future__ import annotations

import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path

from runtime.safety.bash_parser import parse_bash_command

CORPUS_PATH = Path(__file__).resolve().parent / "corpus" / "bash_safety_v0_3.jsonl"
ALLOWED_LABELS = {"safe", "dangerous", "ambiguous", "unknown"}
FIELD_ALIASES = {
    "id": "case_id",
    "expected_classification": "expected_label",
    "reason": "risk_reason",
}
REQUIRED_SEMANTIC_FIELDS = {
    "id",
    "command",
    "expected_classification",
    "category",
    "reason",
}
REQUIRED_COVERAGE_AREAS = {
    "direct binary path deletion": {"absolute_path_invocation"},
    "shell escape / alias bypass style": {"escaped_command_name"},
    "IFS substitution": {"ifs_substitution"},
    "env wrappers": {"env_wrapper"},
    "xargs wrappers": {"xargs_wrapper"},
    "alias/function definitions": {"alias_function_definition"},
    "heredocs": {"heredoc_indicator"},
    "base64 payload indicators": {"base64_payload_indicator"},
    "pipe-to-shell variants": {"pipe_to_shell_variant"},
    "sudo variants": {"sudo_privilege_variant"},
    "recursive chmod/chown": {"chmod_chown_recursive"},
    "false-positive output-only cases": {"false_positive_output_only"},
    "safe read-only admin commands": {"safe_admin_read_only"},
    "unknown/unbalanced quote cases": {"unknown_unbalanced_quote"},
    "Unicode/encoding tricks": {"unicode_or_encoding_trick"},
}
KNOWN_FALSE_NEGATIVE_SAFE: dict[str, str] = {}
KNOWN_CONSERVATIVE_FALSE_POSITIVES: dict[str, str] = {}


def load_corpus() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(CORPUS_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise AssertionError(f"invalid JSONL at line {line_number}: {error}") from error
    return rows


def semantic_value(row: dict[str, str], field: str) -> str:
    source_field = field if field in row else FIELD_ALIASES.get(field, field)
    value = row.get(source_field)
    if not isinstance(value, str) or not value.strip():
        raise AssertionError(f"missing non-empty semantic field {field!r}")
    return value


def build_coverage(rows: list[dict[str, str]]) -> dict[str, object]:
    by_category: Counter[str] = Counter()
    by_expected: Counter[str] = Counter()
    actual_by_category: dict[str, Counter[str]] = defaultdict(Counter)
    expected_vs_actual: Counter[tuple[str, str]] = Counter()
    actual_by_case: dict[str, str] = {}

    for row in rows:
        case_id = semantic_value(row, "id")
        category = semantic_value(row, "category")
        expected = semantic_value(row, "expected_classification")
        actual = parse_bash_command(row["command"], source="corpus_v0_3_coverage").classification
        by_category[category] += 1
        by_expected[expected] += 1
        actual_by_category[category][actual] += 1
        expected_vs_actual[(expected, actual)] += 1
        actual_by_case[case_id] = actual

    return {
        "total": len(rows),
        "by_category": by_category,
        "by_expected": by_expected,
        "actual_by_category": actual_by_category,
        "expected_vs_actual": expected_vs_actual,
        "actual_by_case": actual_by_case,
    }


class BashSafetyCorpusV03CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = load_corpus()
        cls.coverage = build_coverage(cls.rows)

    def test_corpus_has_at_least_thirty_cases(self) -> None:
        self.assertGreaterEqual(self.coverage["total"], 30)

    def test_required_semantic_fields_exist(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row.get("case_id", row.get("id"))):
                for field in REQUIRED_SEMANTIC_FIELDS:
                    self.assertTrue(semantic_value(row, field))

    def test_expected_labels_are_allowed(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=semantic_value(row, "id")):
                self.assertIn(semantic_value(row, "expected_classification"), ALLOWED_LABELS)

    def test_required_coverage_areas_are_represented(self) -> None:
        categories = {semantic_value(row, "category") for row in self.rows}
        for area, accepted_categories in REQUIRED_COVERAGE_AREAS.items():
            with self.subTest(area=area):
                self.assertTrue(categories.intersection(accepted_categories))

    def test_no_risky_expected_case_is_silently_safe(self) -> None:
        actual_by_case = self.coverage["actual_by_case"]
        for row in self.rows:
            case_id = semantic_value(row, "id")
            expected = semantic_value(row, "expected_classification")
            if expected == "safe":
                continue
            with self.subTest(case_id=case_id):
                if case_id in KNOWN_FALSE_NEGATIVE_SAFE:
                    self.assertEqual("safe", actual_by_case[case_id])
                else:
                    self.assertNotEqual("safe", actual_by_case[case_id])

    def test_safe_read_only_cases_are_not_dangerous(self) -> None:
        actual_by_case = self.coverage["actual_by_case"]
        for row in self.rows:
            case_id = semantic_value(row, "id")
            expected = semantic_value(row, "expected_classification")
            if expected != "safe":
                continue
            with self.subTest(case_id=case_id):
                if case_id in KNOWN_CONSERVATIVE_FALSE_POSITIVES:
                    self.assertEqual("dangerous", actual_by_case[case_id])
                else:
                    self.assertNotEqual("dangerous", actual_by_case[case_id])

    def test_expected_vs_actual_matrix_has_no_current_mismatch(self) -> None:
        matrix = self.coverage["expected_vs_actual"]
        mismatches = {
            f"{expected}->{actual}": count
            for (expected, actual), count in matrix.items()
            if expected != actual
        }
        self.assertEqual({}, mismatches)

    def test_coverage_stats_are_deterministic(self) -> None:
        self.assertEqual(18, len(self.coverage["by_category"]))
        self.assertEqual(
            {"ambiguous": 7, "dangerous": 18, "safe": 2, "unknown": 3},
            dict(self.coverage["by_expected"]),
        )

    def test_this_file_has_no_forbidden_execution_primitives(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        blocked = (
            "sub" + "process",
            "os." + "system",
            "shell" + "=True",
            "P" + "open",
            "ev" + "al(",
            "ex" + "ec(",
        )
        for pattern in blocked:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, source)


if __name__ == "__main__":
    unittest.main()
