from __future__ import annotations

import ast
import hashlib
import json
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.providers.critic_adversarial_corpus import (
    CRITIC_ADVERSARIAL_CORPUS_SCHEMA_VERSION,
    CriticAdversarialCase,
    compute_critic_adversarial_case_hash,
    default_critic_adversarial_cases,
)
from runtime.providers.critic_taxonomy import (
    CRITIC_TAXONOMY_CLASSIFIED,
    CRITIC_TAXONOMY_CLASSIFIED_METADATA_ONLY,
    CRITIC_TAXONOMY_INVALID,
    CRITIC_TAXONOMY_SCHEMA_VERSION,
    CriticTaxonomyCategory,
    CriticTaxonomyEntry,
    classify_critic_findings,
    compute_critic_taxonomy_hash,
    default_critic_taxonomy_entries,
)


RUNTIME_FILE = Path(__file__).resolve().parents[1] / "runtime" / "providers" / "critic_adversarial_corpus.py"
AUTHORITY_FIELDS = (
    "approved",
    "authorized",
    "authority",
    "gate_satisfied",
    "can_approve",
    "can_execute",
    "can_write",
    "can_push",
    "can_call_provider",
    "can_change_gate",
)


class CriticAdversarialCorpus1ATests(unittest.TestCase):
    def test_corpus_is_static_deterministic_and_schema_versioned(self):
        first = default_critic_adversarial_cases()
        second = default_critic_adversarial_cases()

        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 10)
        self.assertTrue(all(case.schema_version == CRITIC_ADVERSARIAL_CORPUS_SCHEMA_VERSION for case in first))
        self.assertEqual(len({case.case_id for case in first}), len(first))
        self.assertEqual(
            tuple(case.case_hash for case in first),
            tuple(compute_critic_adversarial_case_hash(case) for case in second),
        )

    def test_every_case_has_required_metadata_and_no_top_level_authority(self):
        for case in default_critic_adversarial_cases():
            with self.subTest(case_id=case.case_id):
                data = case.to_dict()

                self.assertEqual(
                    {
                        "schema_version",
                        "case_id",
                        "title",
                        "taxonomy_code",
                        "subject",
                        "adversarial_evidence",
                        "expected_category",
                        "expected_severity",
                        "expected_fail_closed",
                        "expected_errors",
                        "case_hash",
                    },
                    set(data),
                )
                self.assertTrue(case.case_id.startswith("critic_adv_1a_"))
                self.assertTrue(case.taxonomy_code.startswith("CRITIC_"))
                self.assertIsInstance(case.adversarial_evidence, dict)
                for field in AUTHORITY_FIELDS:
                    self.assertNotIn(field, data)

    def test_corpus_covers_required_adversarial_subjects(self):
        subjects = {case.subject for case in default_critic_adversarial_cases()}

        self.assertTrue(
            {
                "authority_claim",
                "metadata_as_authority",
                "execution_boundary",
                "provider_boundary",
                "package_install_boundary",
                "malformed_critic_evidence",
                "stale_taxonomy_evidence",
                "duplicate_taxonomy_evidence",
                "ambiguous_taxonomy_evidence",
            }.issubset(subjects)
        )

    def test_all_corpus_cases_classify_or_fail_closed_as_expected(self):
        for case in default_critic_adversarial_cases():
            with self.subTest(case_id=case.case_id):
                result = self.classify_case(case)

                if case.expected_fail_closed:
                    self.assertEqual(CRITIC_TAXONOMY_INVALID, result.status)
                    self.assertEqual((), result.classifications)
                    for error in case.expected_errors:
                        self.assertIn(error, result.reason_codes)
                else:
                    self.assertEqual(CRITIC_TAXONOMY_CLASSIFIED, result.status)
                    self.assertEqual((CRITIC_TAXONOMY_CLASSIFIED_METADATA_ONLY,), result.reason_codes)
                    self.assertGreater(len(result.classifications), 0)
                    classification = result.classifications[0]
                    self.assertEqual(case.taxonomy_code, classification.taxonomy_code)
                    self.assertEqual(case.expected_category, classification.category)
                    self.assertEqual(case.expected_severity, classification.severity)

                self.assert_metadata_only(result.to_dict())
                for classification in result.classifications:
                    self.assert_metadata_only(classification.to_dict())

    def test_severity_never_satisfies_gate_or_human_barrier(self):
        critical_cases = [
            case
            for case in default_critic_adversarial_cases()
            if case.expected_severity == "CRITICAL" and not case.expected_fail_closed
        ]
        self.assertGreater(len(critical_cases), 0)

        for case in critical_cases:
            with self.subTest(case_id=case.case_id):
                result = self.classify_case(case)
                data = result.to_dict()

                self.assertEqual(CRITIC_TAXONOMY_CLASSIFIED, result.status)
                self.assertTrue(data["human_review_required"])
                self.assertFalse(data["gate_satisfied"])
                self.assertFalse(data["can_approve"])
                self.assertFalse(data["can_execute"])
                self.assertFalse(data["can_push"])

    def test_metadata_cannot_override_fail_closed_cases(self):
        for case in default_critic_adversarial_cases():
            if not case.expected_fail_closed:
                continue
            with self.subTest(case_id=case.case_id):
                result = self.classify_case(case)
                forced = replace(
                    result,
                    human_review_required=False,
                    can_approve=True,
                    can_execute=True,
                    can_write=True,
                    can_push=True,
                    can_call_provider=True,
                    can_change_gate=True,
                    gate_satisfied=True,
                )

                self.assertEqual(CRITIC_TAXONOMY_INVALID, forced.status)
                self.assertEqual((), forced.classifications)
                self.assert_metadata_only(forced.to_dict())

    def test_unknown_and_capability_smuggling_cases_remain_metadata_only(self):
        cases = {
            case.case_id: case
            for case in default_critic_adversarial_cases()
            if case.subject in {"execution_boundary", "provider_boundary", "package_install_boundary"}
        }
        self.assertEqual(
            {
                "critic_adv_1a_execution_git_browser_smuggling",
                "critic_adv_1a_provider_fallback_smuggling",
                "critic_adv_1a_package_install_unknown_signal",
            },
            set(cases),
        )

        for case in cases.values():
            with self.subTest(case_id=case.case_id):
                result = self.classify_case(case)

                self.assertEqual(CRITIC_TAXONOMY_CLASSIFIED, result.status)
                self.assert_metadata_only(result.to_dict())
                self.assertFalse(result.can_call_provider)
                self.assertFalse(result.can_execute)
                self.assertFalse(result.can_push)

    def test_case_hash_detects_stale_or_mutated_case_metadata(self):
        case = default_critic_adversarial_cases()[0]
        data = case.to_dict()
        data["title"] = "mutated after review"

        self.assertNotEqual(case.case_hash, compute_critic_adversarial_case_hash(data))

    def test_case_dataclass_rejects_stale_case_hash(self):
        case = default_critic_adversarial_cases()[0]

        with self.assertRaises(ValueError):
            CriticAdversarialCase(**{**case.to_dict(), "case_hash": "0" * 64})

    def test_module_has_no_execution_provider_network_browser_package_env_or_gate_surface(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        scan = scan_module(RUNTIME_FILE)

        forbidden_imports = (
            "os",
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "aiohttp",
            "webbrowser",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
            "runtime.providers.gateway",
            "runtime.provider_live_adapter",
            "runtime.execution",
            "runtime.control_write",
        )
        forbidden_calls = (
            "open",
            "print",
            "eval",
            "exec",
            "subprocess.run",
            "os.system",
            "write",
            "write_text",
            "write_bytes",
            "dispatch",
            "execute",
            "approve",
            "authorize",
        )

        for forbidden in forbidden_imports:
            self.assertNotIn(forbidden, scan.imports)
        for forbidden in forbidden_calls:
            self.assertNotIn(forbidden, scan.calls)
        for forbidden_text in ("shell=true", "os.environ", "getenv", "api_key"):
            self.assertNotIn(forbidden_text, source)

    def classify_case(self, case):
        evidence = dict(case.adversarial_evidence)
        report = evidence.get("critic_report", evidence)
        expected_taxonomy_hash = evidence.get("expected_taxonomy_hash")
        taxonomy_entries = self.taxonomy_entries_for_case(evidence)
        return classify_critic_findings(
            report,
            taxonomy_entries=taxonomy_entries,
            expected_taxonomy_hash=expected_taxonomy_hash,
        )

    def taxonomy_entries_for_case(self, evidence):
        attack = evidence.get("taxonomy_attack")
        entries = default_critic_taxonomy_entries()
        if attack == "duplicate_code":
            return (*entries, entries[0])
        if attack == "ambiguous_signal":
            ambiguous = self.valid_entry(
                code="CRITIC_ADVERSARIAL_AMBIGUOUS_SIGNAL",
                category=CriticTaxonomyCategory.PROVIDER_TRUST.value,
                match_flags=entries[0].match_flags,
            )
            return (*entries, ambiguous)
        return entries

    @staticmethod
    def valid_entry(*, code: str, category: str, match_flags: tuple[str, ...]) -> CriticTaxonomyEntry:
        material = {
            "schema_version": CRITIC_TAXONOMY_SCHEMA_VERSION,
            "code": code,
            "category": category,
            "severity": "HIGH",
            "title": "Adversarial taxonomy entry",
            "description": "Test entry that attempts to collide with taxonomy evidence.",
            "match_flags": match_flags,
            "match_check_ids": (),
        }
        return CriticTaxonomyEntry(entry_hash=hash_json(material), **material)

    def assert_metadata_only(self, data: dict) -> None:
        for field in AUTHORITY_FIELDS:
            self.assertFalse(data.get(field, False))


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    calls: list[str] = []
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Call):
            name = call_name(node.func, aliases)
            if name:
                calls.append(name)
    return type("Scan", (), {"imports": tuple(imports), "calls": tuple(calls)})()


def call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parts = attribute_parts(node)
        if parts:
            return ".".join((aliases.get(parts[0], parts[0]), *parts[1:]))
    return ""


def attribute_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*attribute_parts(node.value), node.attr)
    return ()


def hash_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    unittest.main()
