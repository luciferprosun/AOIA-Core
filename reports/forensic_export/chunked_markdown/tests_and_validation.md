# Tests And Validation

Unit tests, validator implementation, and validation documents.

Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

Files in this chunk: 12

## `docs/TEST_CONSTITUTION.md`

- size: 1105 bytes
- sha256: `0b87d1a0440e4b9d9e774e3f6f6ae3f8a4eea6169b6a2846bea1c3c7c2236191`
- category: docs

```markdown
# Test Constitution

## Principle

AOIA tests must prove deterministic behavior before any runtime integration.

## Required Properties

- Same input returns same output.
- Boundary values are explicit.
- Invalid input fails fast.
- Configuration loads deterministically.
- Configuration is readonly after loading.
- Tests must not call external networks.
- Tests must not require provider keys.
- Tests must not depend on current time unless time is explicitly injected.

## Fail-Fast Rule

Invalid configuration or invalid pressure input should raise immediately. Silent
fallbacks are not allowed in AOIA core contracts.

## Test Layers

Unit tests:
- pure functions
- config loading
- validation behavior

Integration tests:
- allowed only after runtime integration is approved

External tests:
- forbidden in early AOIA steps

## Current AOIA Test File

- `tests/test_aoia_determinism.py`

## Current Validation Focus

- `select_depth()` determinism
- pressure threshold stability
- invalid pressure rejection
- `load_config()` deterministic loading
- readonly config behavior
- correlation id shape
```

## `docs/reports/PHASE_1A_GIT_VALIDATION.md`

- size: 7710 bytes
- sha256: `3fc2dc9975e7275b80be8a13a7ebc662721849719675d5002ad093874133568c`
- category: docs

```markdown
# Phase 1A Git Validation

Status: validation report
Date: 2026-05-23
Repository: `/home/l/Desktop/AOIA-Core`
Remote: `https://github.com/luciferprosun/AOIA-Core.git`

## Summary

Phase 1A architecture documents are present in the canonical repository, but the repository is not fully clean under the requested checkpoint rules.

No runtime source files are modified. No files larger than 50 MB were found. No archives or nested git repositories were found inside the repository. The validation found untracked runtime/audit risk files and accidental duplicate architecture documents outside the repository.

Because the repository is not clean under the requested criteria, no new checkpoint commit should be created by this validation step.

## Repository Status

Current branch:
- `main`

Current HEAD:
- `5674fd4d25daaf8aa8c0bed1c658f9e0260678e5`

Current git status:

```text
## main...origin/main
?? docs/forensic-runtime-audit/
?? state/
```

Modified files:
- none

Staged files:
- none

Untracked files:
- `docs/forensic-runtime-audit/CANONICAL_REFACTOR_PREP.md`
- `docs/forensic-runtime-audit/CURRENT_RUNTIME_TOPOLOGY.md`
- `docs/forensic-runtime-audit/MEMORY_CONTAMINATION_MAP.md`
- `docs/forensic-runtime-audit/RUNTIME_BOUNDARY_VIOLATIONS.md`
- `state/model_config.json`
- `state/providers.json`

## Repository Size

Working tree size:
- `4.5M`

Git directory size:
- `2.1M`

Repository size is small and does not indicate large artifact contamination.

## Phase 1A Architecture Documents

Expected documents:
- `docs/architecture/AOIA_MEMORY_MODEL.md`
- `docs/architecture/FORBIDDEN_MEMORY_FLOWS.md`
- `docs/architecture/MEMORY_LAYER_ACCESS_MATRIX.md`

Validation result:
- all expected documents exist in the canonical repository
- no runtime files are required for these documents
- no provider or routing files are modified

Important note:
- These documents are already committed at HEAD `5674fd4d25daaf8aa8c0bed1c658f9e0260678e5`.
- They were previously pushed to `origin/main`.
- This validation report does not rewrite or amend that history.

## Large File Analysis

Files larger than 50 MB:
- none found

Recommendation:
- no Git LFS action is required for files currently present in the repository
- no large file deletion or movement is required

## Archives And Hidden Artifacts

Archives found in repository:
- none found for `.zip`, `.tar`, `.tar.gz`, `.tgz`, `.7z`, `.rar`, or `.gz`

Hidden files found outside `.git`:
- `.gitignore`

Temporary report-like files inside repository:
- `AOIA_CONTAMINATION_REPORT.md`
- `runtime/knowledge/validator/validation_report.md`

Assessment:
- both appear to be existing tracked project documents, not new temporary contamination from Phase 1A

## PDF And Binary Analysis

Tracked PDFs:
- `runtime/knowledge/source/RHCSA_Command_Library (1).pdf` - 153760 bytes

Duplicated PDFs:
- none detected

Tracked `.pyc` files:
- none

Ignored local `.pyc` files are present under runtime `__pycache__` directories. They are excluded by `.gitignore`:

```text
__pycache__/
*.pyc
.pytest_cache/
.venv/
```

Assessment:
- no tracked Python bytecode contamination detected
- ignored local bytecode files do not block the checkpoint

## Nested Git Repository Check

Nested `.git` directories inside the repository:
- none found

Assessment:
- no nested repository contamination detected

## Duplicate Detection Outside Repository

Accidental duplicate architecture documents were found outside the repository:

- `/home/l/docs/architecture/AOIA_MEMORY_MODEL.md`
- `/home/l/docs/architecture/FORBIDDEN_MEMORY_FLOWS.md`
- `/home/l/docs/architecture/MEMORY_LAYER_ACCESS_MATRIX.md`

Assessment:
- these are duplicates of the Phase 1A architecture documents
- they are outside `/home/l/Desktop/AOIA-Core`
- they should not be treated as canonical
- they should be removed or archived only after explicit operator approval

Related temporary report outside repository:
- `/home/l/Desktop/CODEX_RAPORT_1925.md`

Assessment:
- this is an operator-requested desktop report, not repository content
- it is outside the AOIA-Core git tree

## Untracked Runtime Risk Files

Untracked audit documents:

- `docs/forensic-runtime-audit/CANONICAL_REFACTOR_PREP.md`
- `docs/forensic-runtime-audit/CURRENT_RUNTIME_TOPOLOGY.md`
- `docs/forensic-runtime-audit/MEMORY_CONTAMINATION_MAP.md`
- `docs/forensic-runtime-audit/RUNTIME_BOUNDARY_VIOLATIONS.md`

Untracked runtime state files:

- `state/model_config.json`
- `state/providers.json`

Risk assessment:
- `docs/forensic-runtime-audit/` may be legitimate architecture audit material, but it is untracked and outside the requested Phase 1A commit set
- `state/` contains mutable runtime configuration/state and should not be committed without a dedicated policy
- these files prevent a fully clean checkpoint under the requested validation rules

Recommendation:
- decide explicitly whether `docs/forensic-runtime-audit/` should be committed as architecture audit evidence or moved to a report/archive policy
- add runtime state paths to ignore policy or move them out of source authority boundaries in a later implementation phase
- do not include `state/` in a Phase 1A architectural checkpoint

## Runtime Change Verification

Runtime files modified:
- none

Provider files modified:
- none

Routing files modified:
- none

Memory runtime files modified:
- none

Assessment:
- no runtime behavior was changed by this validation step

## Staging Verification

Current staged files:
- none

Expected Phase 1A staging set, if a clean checkpoint were performed:
- `docs/architecture/AOIA_MEMORY_MODEL.md`
- `docs/architecture/FORBIDDEN_MEMORY_FLOWS.md`
- `docs/architecture/MEMORY_LAYER_ACCESS_MATRIX.md`
- `docs/reports/PHASE_1A_GIT_VALIDATION.md`

Actual result:
- no files staged
- validation report is newly created and untracked until explicitly staged

Assessment:
- the repository is not in the requested clean checkpoint state because unrelated untracked files exist

## Safe-To-Commit Confirmation

Safe to create the requested clean checkpoint commit:
- no

Reason:
- unrelated untracked files remain in `docs/forensic-runtime-audit/` and `state/`
- accidental duplicate architecture files exist outside the canonical repository
- Phase 1A architecture documents are already committed at HEAD and already pushed

Safe to proceed with a later documentation-only commit after cleanup decision:
- yes, if untracked files are resolved or explicitly accepted as non-blocking

## Rollback Readiness Assessment

Current rollback readiness:
- partial

Positive signals:
- runtime files are unchanged
- no provider or routing changes are present
- no large artifacts were introduced
- no nested git repository was introduced
- Phase 1A architecture documents are isolated under `docs/architecture/`

Risks:
- previous Phase 1A commit was already pushed before this validation report was created
- duplicate documents outside the repository can confuse future operators
- untracked runtime state remains inside the repository working tree
- untracked forensic audit documents may be omitted accidentally from future architecture history

Recommended rollback approach if needed:
- do not rewrite history unless explicitly approved
- create a follow-up corrective commit rather than amending pushed history
- clean or archive outside-repo duplicates only with explicit approval
- decide the canonical handling for `docs/forensic-runtime-audit/` and `state/` before Phase 1B

## Final Validation Result

Repository clean:
- no

Safe to create requested clean checkpoint commit now:
- no

Safe to proceed to Phase 1B:
- no, not until the untracked runtime/audit files and outside-repo duplicates are explicitly resolved or accepted
```

## `tests/test_aoia_determinism.py`

- size: 1992 bytes
- sha256: `28c9e9cd381cc0d0ba49ab31a8f3dd19dca858b0a1337aa052dd78ce7e20565e`
- category: tests

```python
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
```

## `tests/test_epistemic_kernel.py`

- size: 1712 bytes
- sha256: `191dcb48a51dac387a5bf274c49326f3a85e404716123ba9683b5998d783cc4a`
- category: tests

```python
import unittest
from pathlib import Path

from adaptive_routing.epistemic_kernel import AOIAEpistemicKernel


PROJECT_DIR = Path(__file__).resolve().parents[1]


class AOIAEpistemicKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = AOIAEpistemicKernel(PROJECT_DIR)

    def test_evaluate_is_deterministic_for_same_query(self) -> None:
        first = self.kernel.evaluate("systemctl status")
        second = self.kernel.evaluate("systemctl status")
        self.assertEqual(first.route, second.route)
        self.assertEqual(first.depth, second.depth)
        self.assertEqual(first.pressure, second.pressure)
        self.assertEqual(first.confidence, second.confidence)
        self.assertEqual(first.manual_review_reasons, second.manual_review_reasons)

    def test_provenance_is_attached_to_evidence(self) -> None:
        decision = self.kernel.evaluate("systemctl status")
        self.assertTrue(decision.evidence)
        provenance = decision.evidence[0].get("provenance", {})
        self.assertIn("metadata", provenance)
        self.assertIn("content_hash", provenance)

    def test_duplicate_command_triggers_manual_review(self) -> None:
        decision = self.kernel.evaluate("systemctl status")
        self.assertTrue(decision.should_respond_locally)
        self.assertTrue(decision.manual_review_required)
        self.assertIn("duplicate_or_conflicting_sources_detected", decision.manual_review_reasons)

    def test_non_linux_query_does_not_force_local_response(self) -> None:
        decision = self.kernel.evaluate("write a haiku about spring")
        self.assertFalse(decision.should_respond_locally)


if __name__ == "__main__":
    unittest.main()
```

## `tests/test_epistemic_registry.py`

- size: 3299 bytes
- sha256: `578834cddcdf5524e7874e4f1ef341fbe64f39b0be1d289e70cb8b607209a855`
- category: tests

```python
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools import epistemic_registry


class EpistemicRegistryTests(unittest.TestCase):
    def test_detect_self_references_flags_self_edge(self) -> None:
        graph = {"knowledge/a.md": ["knowledge/a.md"]}
        findings = epistemic_registry.detect_self_references(graph)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "self_reference")

    def test_detect_circular_references_finds_simple_cycle(self) -> None:
        graph = {
            "knowledge/a.md": ["knowledge/b.md"],
            "knowledge/b.md": ["knowledge/a.md"],
        }
        findings = epistemic_registry.detect_circular_references(graph)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "circular_reference")

    def test_duplicate_command_detection_finds_multiple_sources(self) -> None:
        artifacts = (
            epistemic_registry.KnowledgeArtifact(
                path=Path("/repo/knowledge/a.md"),
                artifact_type="markdown",
                metadata={},
                references=(),
                commands=("ls",),
                content_hash="hash-a",
            ),
            epistemic_registry.KnowledgeArtifact(
                path=Path("/repo/knowledge/b.md"),
                artifact_type="markdown",
                metadata={},
                references=(),
                commands=("ls",),
                content_hash="hash-b",
            ),
        )
        findings = epistemic_registry.detect_duplicate_commands(artifacts)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["command"], "ls")

    def test_duplicate_artifact_detection_uses_hash(self) -> None:
        artifacts = (
            epistemic_registry.KnowledgeArtifact(
                path=Path("/repo/knowledge/a.md"),
                artifact_type="markdown",
                metadata={},
                references=(),
                commands=(),
                content_hash="same-hash",
            ),
            epistemic_registry.KnowledgeArtifact(
                path=Path("/repo/knowledge/b.md"),
                artifact_type="markdown",
                metadata={},
                references=(),
                commands=(),
                content_hash="same-hash",
            ),
        )
        findings = epistemic_registry.detect_duplicate_artifacts(artifacts)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "duplicate_content")

    def test_write_registries_writes_json_files(self) -> None:
        with TemporaryDirectory() as tmp:
            provenance_path = Path(tmp) / "provenance_registry.json"
            contradiction_path = Path(tmp) / "contradiction_registry.json"
            provenance, contradictions = epistemic_registry.write_registries(
                provenance_path=provenance_path,
                contradiction_path=contradiction_path,
            )
            self.assertTrue(provenance_path.exists())
            self.assertTrue(contradiction_path.exists())
            self.assertIn("artifact_count", provenance)
            self.assertIn("summary", contradictions)


if __name__ == "__main__":
    unittest.main()
```

## `tests/test_epistemic_safeguards.py`

- size: 3012 bytes
- sha256: `4e21324e2625bba3a3d36fccab6e5aaa97a5d187977eb018545a6c93def72542`
- category: tests

```python
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from tools.executor import ExecutionEngine
from tools.memory import MemoryStore
from tools.validator import validate_action


class EpistemicSafeguardsTests(unittest.TestCase):
    def test_validate_action_normalizes_confidence_label(self) -> None:
        action = validate_action(
            {
                "action": "respond",
                "message": "I DO NOT KNOW",
                "reason": "No evidence.",
                "confidence": "LOW",
            }
        )
        self.assertEqual(action["confidence_label"], "low")

    def test_validate_action_defaults_unknown_confidence(self) -> None:
        action = validate_action(
            {
                "action": "respond",
                "message": "I DO NOT KNOW",
                "reason": "No evidence.",
                "confidence": "unsupported",
            }
        )
        self.assertEqual(action["confidence_label"], "unknown")

    def test_load_epistemic_safeguards_from_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "EPISTEMIC_KILL_SWITCH": "1",
                "EPISTEMIC_DISABLE_MODEL": "1",
                "EPISTEMIC_DISABLE_KNOWLEDGE_ROUTE": "1",
                "EPISTEMIC_DISABLE_MEMORY_HATS": "1",
                "EPISTEMIC_DISABLE_REASONING_TRACE": "1",
            },
            clear=False,
        ):
            safeguards = main.load_epistemic_safeguards()
        self.assertTrue(safeguards.kill_switch)
        self.assertTrue(safeguards.disable_model)
        self.assertTrue(safeguards.disable_knowledge)
        self.assertTrue(safeguards.disable_memory_hats)
        self.assertFalse(safeguards.reasoning_trace_enabled)
        self.assertTrue(safeguards.prefer_unknown)

    def test_memory_store_creates_evidence_and_reasoning_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            memory = MemoryStore(project_dir, project_dir)
            self.assertTrue(memory.vault_paths.evidence_dir.is_dir())
            self.assertTrue(memory.vault_paths.reasoning_dir.is_dir())

    def test_executor_respond_propagates_confidence_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            memory = MemoryStore(project_dir, project_dir)
            engine = ExecutionEngine(project_dir, memory)
            result = engine.execute(
                {
                    "action": "respond",
                    "message": "I DO NOT KNOW",
                    "reason": "No evidence.",
                    "confidence_label": "unknown",
                },
                require_approval=False,
            )
            self.assertEqual(result["confidence_label"], "unknown")


if __name__ == "__main__":
    unittest.main()
```

## `tests/test_executor_containment.py`

- size: 1863 bytes
- sha256: `0aa30796c7f80550d976c9c694e1cf54a5398761a4b32c3cfcaa5c5dca703fcc`
- category: tests

```python
import json
import tempfile
import unittest
from pathlib import Path

from tools.executor import ExecutionEngine
from tools.memory import MemoryStore


class ExecutorContainmentTests(unittest.TestCase):
    def test_action_results_are_replay_only_not_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            desktop_dir = Path(tmp) / "Desktop"
            project_dir.mkdir()
            desktop_dir.mkdir()

            memory = MemoryStore(project_dir, project_dir)
            engine = ExecutionEngine(project_dir, memory)
            result = engine.execute(
                {
                    "action": "create_folder",
                    "path": str(desktop_dir / "AI_TEST"),
                    "reason": "Create desktop folder.",
                },
                require_approval=False,
            )

            self.assertTrue(result["success"])
            self.assertTrue((desktop_dir / "AI_TEST").is_dir())
            self.assertTrue(memory.memory.recent_outputs)
            self.assertEqual(len(list(memory.paths.command_logs_dir.glob("*.json"))), 1)
            self.assertFalse(memory.evidence_file.exists())

            history_lines = memory.history_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(history_lines), 1)
            history_record = json.loads(history_lines[0])
            authority = history_record["payload"]["authority"]
            self.assertEqual(history_record["kind"], "action_result")
            self.assertEqual(authority["classification"], "operational_event")
            self.assertEqual(authority["retention"], "replay_only")
            self.assertTrue(authority["non_authoritative"])
            self.assertFalse(authority["canonical_evidence"])


if __name__ == "__main__":
    unittest.main()
```

## `tests/test_knowledge_validator.py`

- size: 3940 bytes
- sha256: `1699f29e0f2ad9bbfdc090f3c495732b4e5edfc8db971c88f9162011afc8eae2`
- category: tests

```python
import json
import tempfile
import unittest
from pathlib import Path

from knowledge.validator.validator import validate_path


VALID_ENTRY = {
    "id": "ls-command",
    "command": "ls",
    "description": "Lists directory contents.",
    "category": "filesystem",
    "tags": ["directory-listing", "read-only"],
    "risk": "low",
    "os": ["linux"],
    "shell": ["bash"],
    "examples": [
        {
            "input": "ls -la",
            "expected_effect": "Prints detailed directory contents.",
        }
    ],
}


class KnowledgeValidatorTests(unittest.TestCase):
    def test_valid_entry_passes(self) -> None:
        with knowledge_dir() as root:
            write_entry(root, "ls-command.json", VALID_ENTRY)
            report = validate_path(root)
            self.assertTrue(report.ok)
            self.assertEqual(report.checked_files, 1)

    def test_invalid_json_fails(self) -> None:
        with knowledge_dir() as root:
            (root / "examples" / "bad-json.json").write_text("{bad", encoding="utf-8")
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid JSON", report.message)

    def test_missing_required_field_fails(self) -> None:
        with knowledge_dir() as root:
            entry = dict(VALID_ENTRY)
            del entry["risk"]
            write_entry(root, "missing-risk.json", entry)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("missing required field: risk", report.message)

    def test_duplicate_command_fails(self) -> None:
        with knowledge_dir() as root:
            write_entry(root, "first-command.json", VALID_ENTRY)
            duplicate = dict(VALID_ENTRY)
            duplicate["id"] = "second-command"
            write_entry(root, "second-command.json", duplicate)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("duplicate command 'ls'", report.message)

    def test_invalid_tag_fails(self) -> None:
        with knowledge_dir() as root:
            entry = dict(VALID_ENTRY)
            entry["tags"] = ["Read Only"]
            write_entry(root, "invalid-tag.json", entry)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid tag", report.message)

    def test_invalid_risk_fails(self) -> None:
        with knowledge_dir() as root:
            entry = dict(VALID_ENTRY)
            entry["risk"] = "extreme"
            write_entry(root, "invalid-risk.json", entry)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid risk", report.message)

    def test_invalid_filename_fails(self) -> None:
        with knowledge_dir() as root:
            write_entry(root, "BadName.json", VALID_ENTRY)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid filename", report.message)

    def test_invalid_category_fails(self) -> None:
        with knowledge_dir() as root:
            entry = dict(VALID_ENTRY)
            entry["category"] = "misc"
            write_entry(root, "invalid-category.json", entry)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid category", report.message)


class knowledge_dir:
    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "knowledge"
        (self.root / "examples").mkdir(parents=True)
        return self.root

    def __exit__(self, exc_type, exc, tb) -> None:
        self._tmp.cleanup()


def write_entry(root: Path, filename: str, entry: dict) -> None:
    (root / "examples" / filename).write_text(
        json.dumps(entry, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
```

## `tests/test_linux_retrieval.py`

- size: 2928 bytes
- sha256: `3f3c66fb5546758ccf7cf31125f014a5240d923d49215ee423732fe0f0780a61`
- category: tests

```python
from __future__ import annotations

import unittest

from retrieval.linux import LinuxRetrievalEngine


class LinuxRetrievalEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = LinuxRetrievalEngine(max_results=5)

    def test_exact_command_retrieval(self) -> None:
        response = self.engine.retrieve("ls")

        self.assertTrue(response.answered)
        self.assertEqual(response.match_type, "exact")
        self.assertEqual(response.confidence, "high")
        self.assertGreaterEqual(response.confidence_score, 90)
        self.assertTrue(any("ls" in item.get("related_commands", []) for item in response.results))

    def test_alias_retrieval(self) -> None:
        response = self.engine.retrieve("firewall")

        self.assertTrue(response.answered)
        self.assertEqual(response.match_type, "alias")
        self.assertGreaterEqual(response.confidence_score, 90)
        self.assertTrue(response.results)

    def test_subcommand_retrieval(self) -> None:
        response = self.engine.retrieve("systemctl status")

        self.assertTrue(response.answered)
        self.assertIn(response.match_type, {"exact", "subcommand"})
        self.assertGreaterEqual(response.confidence_score, 80)

    def test_invalid_command_refuses(self) -> None:
        response = self.engine.retrieve("zzzz-not-a-linux-command-xyz")

        self.assertFalse(response.answered)
        self.assertEqual(response.status, "refused")
        self.assertEqual(response.confidence, "none")
        self.assertFalse(response.results)
        self.assertIn("clarify", response.message.lower())

    def test_low_confidence_generic_query_refuses(self) -> None:
        response = self.engine.retrieve("linux command")

        self.assertFalse(response.answered)
        self.assertEqual(response.status, "refused")
        self.assertEqual(response.confidence_score, 0)

    def test_provenance_attachment(self) -> None:
        response = self.engine.retrieve("ls")

        self.assertTrue(response.results)
        provenance = response.results[0]["provenance"]
        self.assertIn("source_file", provenance)
        self.assertIn("source_page", provenance)
        self.assertIn("canonical_source", provenance)
        self.assertIn("confidence_score", provenance)
        self.assertEqual(provenance["confidence_score"], response.confidence_score)
        self.assertTrue(provenance["canonical_source"].endswith("linux_master_library_v1.pdf"))

    def test_duplicate_handling(self) -> None:
        response = self.engine.retrieve("ls")

        keys = [
            (
                item.get("file_location"),
                item.get("source_file"),
                item.get("topic"),
                item.get("summary"),
            )
            for item in response.results
        ]
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == "__main__":
    unittest.main()
```

## `tests/test_main.py`

- size: 19366 bytes
- sha256: `96b4f25afa459f28b514db009526bf5af335ee5c3aada99528bc9bde2a953542`
- category: tests

```python
import json
import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main
from tools.browser_tools import (
    browser_click,
    browser_close,
    browser_current_url,
    browser_get_visible_text,
    browser_open,
    browser_press,
    browser_screenshot,
    browser_start,
    browser_type,
    PLAYWRIGHT_AVAILABLE,
)
from tools.executor import ExecutionEngine
from tools.memory import MemoryStore
from tools.system_info import detect_desktop_dir
from tools.validator import classify_shell_command, validate_shell_command
from providers.config import DEFAULT_MODEL, ProviderManager
from providers.aureon_provider import AureonProvider
from commands.local_commands import cmd_scemda


class FakeProvider:
    def __init__(self, outputs: list[str | Exception]) -> None:
        self.outputs = outputs
        self.calls = 0
        self.model_name = "fake/test-model"

    def generate(self, prompt: str) -> str:
        _ = prompt
        output = self.outputs[self.calls]
        self.calls += 1
        if isinstance(output, Exception):
            raise output
        return output

    def describe(self) -> str:
        return self.model_name

    def switch_model(self, model_name: str) -> str:
        self.model_name = model_name
        return model_name


class RuntimeArchitectureTests(unittest.TestCase):
    def test_normalize_external_url_unwraps_facebook_redirect(self) -> None:
        raw = (
            "https://l.facebook.com/l.php?u=https%3A%2F%2Fzenodo.org%2Frecords%2F20038802"
            "%3Ffbclid%3Dabc123&h=XYZ"
        )
        normalized = main.normalize_external_url(raw)
        self.assertEqual(normalized, "https://zenodo.org/records/20038802?fbclid=abc123")

    def test_detect_desktop_dir_uses_xdg_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config_dir = home / ".config"
            config_dir.mkdir(parents=True)
            desktop_dir = home / "MojPulpit"
            desktop_dir.mkdir()
            (config_dir / "user-dirs.dirs").write_text(
                'XDG_DESKTOP_DIR="$HOME/MojPulpit"\n',
                encoding="utf-8",
            )
            detected = detect_desktop_dir(home)
            self.assertEqual(detected, desktop_dir)

    def test_validate_shell_command_allows_multi_step_redirection(self) -> None:
        allowed, reason = validate_shell_command('echo "hello" > file.txt && cat file.txt')
        self.assertTrue(allowed)
        self.assertEqual(reason, "OK")

    def test_classify_install_command_requires_confirmation(self) -> None:
        decision = classify_shell_command("sudo apt install curl")
        self.assertEqual(decision.mode, "advanced")
        self.assertTrue(decision.requires_confirmation)
        self.assertTrue(decision.interactive)

    def test_executor_creates_folder_on_desktop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            desktop_dir = Path(tmp) / "Desktop"
            project_dir.mkdir()
            desktop_dir.mkdir()
            memory = MemoryStore(project_dir, project_dir)
            engine = ExecutionEngine(project_dir, memory)
            result = engine.execute(
                {
                    "action": "create_folder",
                    "path": str(desktop_dir / "AI_TEST"),
                    "reason": "Create desktop folder.",
                }
            )
            self.assertTrue(result["success"])
            self.assertTrue((desktop_dir / "AI_TEST").is_dir())

    def test_executor_creates_and_writes_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            desktop_dir = Path(tmp) / "Desktop"
            project_dir.mkdir()
            desktop_dir.mkdir()
            target_file = desktop_dir / "AI_TEST" / "note.txt"
            memory = MemoryStore(project_dir, project_dir)
            engine = ExecutionEngine(project_dir, memory)
            engine.execute(
                {
                    "action": "create_folder",
                    "path": str(target_file.parent),
                    "reason": "Create folder.",
                }
            )
            result = engine.execute(
                {
                    "action": "write_file",
                    "path": str(target_file),
                    "content": "hello from agent\n",
                    "reason": "Write file.",
                }
            )
            self.assertTrue(result["success"])
            self.assertEqual(target_file.read_text(encoding="utf-8"), "hello from agent\n")

    def test_runtime_cancels_install_when_user_declines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            provider = FakeProvider(
                [
                    json_text(
                        {
                            "action": "shell_execute",
                            "command": "sudo apt install curl",
                            "reason": "Install curl.",
                            "requires_confirmation": True,
                        }
                    )
                ]
            )
            runtime = main.AgentRuntime(provider, PROMPT_TEMPLATE, project_dir)
            with patch("builtins.input", return_value="n"):
                runtime.handle_user_request("zainstaluj curl")
            self.assertEqual(provider.calls, 1)
            self.assertTrue(runtime.memory_store.memory.recent_outputs)
            self.assertFalse(runtime.memory_store.memory.recent_outputs[-1]["success"])

    def test_runtime_handles_model_503_after_successful_first_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            desktop_dir = Path(tmp) / "Desktop"
            project_dir.mkdir()
            desktop_dir.mkdir()
            provider = FakeProvider(
                [
                    json_text(
                        {
                            "action": "create_folder",
                            "path": str(desktop_dir / "xxxxxxxxxxxx"),
                            "reason": "Create requested desktop folder.",
                        }
                    ),
                    RuntimeError("503 UNAVAILABLE"),
                    RuntimeError("503 UNAVAILABLE"),
                    RuntimeError("503 UNAVAILABLE"),
                ]
            )
            runtime = main.AgentRuntime(provider, PROMPT_TEMPLATE, project_dir)
            with patch("sys.stdout", new_callable=StringIO) as fake_stdout:
                runtime.handle_user_request("zrob folder i plik")
            self.assertTrue((desktop_dir / "xxxxxxxxxxxx").is_dir())
            self.assertIn("Część operacji została już wykonana poprawnie", fake_stdout.getvalue())

    @unittest.skipUnless(PLAYWRIGHT_AVAILABLE, "Playwright is not installed")
    def test_bootstrap_local_context_opens_url_before_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_local_site(root)
            project_dir = root / "project"
            project_dir.mkdir()
            provider = FakeProvider([])
            runtime = main.AgentRuntime(provider, PROMPT_TEMPLATE, project_dir)
            local_url = (root / "index.html").as_uri()

            with patch("sys.stdout", new_callable=StringIO):
                trace = runtime.bootstrap_local_context(f"przeanalizuj te prace {local_url}")

            self.assertEqual(provider.calls, 0)
            self.assertGreaterEqual(len(trace), 2)
            self.assertEqual(trace[1]["action"]["action"], "browser_open")
            self.assertIn("index.html", trace[1]["result"]["current_url"])
            browser_close()

    def test_slash_status_uses_no_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            provider = FakeProvider([])
            runtime = main.AgentRuntime(provider, PROMPT_TEMPLATE, project_dir)
            result = runtime.command_registry.execute("/status", runtime)
            self.assertTrue(result.handled)
            self.assertIn("Local runtime status", result.message)
            self.assertEqual(provider.calls, 0)

    def test_local_desktop_folder_route_uses_no_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            desktop_dir = Path(tmp) / "Desktop"
            project_dir.mkdir()
            desktop_dir.mkdir()
            provider = FakeProvider([])
            runtime = main.AgentRuntime(provider, PROMPT_TEMPLATE, project_dir)
            runtime.desktop_dir = desktop_dir
            runtime.local_router.desktop_dir = desktop_dir
            with patch("sys.stdout", new_callable=StringIO):
                runtime.handle_user_request("stworz folder AI_TEST na pulpicie")
            self.assertTrue((desktop_dir / "AI_TEST").is_dir())
            self.assertEqual(provider.calls, 0)

    def test_plain_help_uses_no_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            provider = FakeProvider([])
            runtime = main.AgentRuntime(provider, PROMPT_TEMPLATE, project_dir)
            with patch("sys.stdout", new_callable=StringIO) as fake_stdout:
                runtime.handle_user_request("help")
            self.assertIn("/status", fake_stdout.getvalue())
            self.assertEqual(provider.calls, 0)

    def test_slash_vault_uses_no_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            provider = FakeProvider([])
            runtime = main.AgentRuntime(provider, PROMPT_TEMPLATE, project_dir)
            result = runtime.command_registry.execute("/vault", runtime)
            self.assertTrue(result.handled)
            self.assertIn("Obsidian vault", result.message)
            self.assertEqual(provider.calls, 0)

    def test_scemda_command_reports_when_zip_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runtime = main.AgentRuntime(FakeProvider([]), PROMPT_TEMPLATE, project_dir)
            with patch("commands.local_commands.SCEMDA_ZIP", Path(tmp) / "missing.zip"):
                result = cmd_scemda("", runtime)
            self.assertTrue(result.handled)
            self.assertIn("SCEMDA zip not found", result.message)

    def test_memory_store_initializes_obsidian_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            memory = MemoryStore(project_dir, project_dir)
            self.assertTrue(memory.vault_dir.exists())
            self.assertTrue((memory.vault_dir / "00_START_HERE.md").exists())
            self.assertTrue((memory.vault_dir / ".obsidian" / "app.json").exists())

    def test_provider_manager_defaults_to_aureon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            manager = ProviderManager(project_dir)
            self.assertEqual(manager.current_model, DEFAULT_MODEL)

    def test_provider_manager_normalizes_model_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            manager = ProviderManager(project_dir)
            self.assertEqual(manager.normalize_model_name("aureon"), "aureon/aureon-queen")
            self.assertEqual(manager.normalize_model_name("gemini"), "gemini/gemini-2.5-flash")
            self.assertEqual(manager.normalize_model_name("openrouter"), "openrouter/free")
            self.assertEqual(
                manager.normalize_model_name("openai:gpt-4o-mini"),
                "openai/gpt-4o-mini",
            )

    def test_model_command_lists_presets_and_current_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            manager = ProviderManager(project_dir)
            runtime = SimpleNamespace(provider_manager=manager)
            result = main.build_command_registry().execute("/model list", runtime)
            self.assertTrue(result.handled)
            self.assertIn("Current model:", result.message)
            self.assertIn("aureon", result.message)
            self.assertIn("gemini", result.message)

    def test_model_command_switches_alias_to_full_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            manager = ProviderManager(project_dir)
            runtime = SimpleNamespace(provider_manager=manager)
            result = main.build_command_registry().execute("/model aureon", runtime)
            self.assertTrue(result.handled)
            self.assertIn("Model switched to: aureon/aureon-queen", result.message)
            self.assertEqual(manager.current_model, "aureon/aureon-queen")
            self.assertEqual(
                json.loads((project_dir / "state" / "model_config.json").read_text(encoding="utf-8"))["model"],
                "aureon/aureon-queen",
            )

    def test_model_command_switches_gemini_without_instantiating_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            manager = ProviderManager(project_dir)
            runtime = SimpleNamespace(provider_manager=manager)
            result = main.build_command_registry().execute("/model gemini", runtime)
            self.assertTrue(result.handled)
            self.assertIn("Model switched to: gemini/gemini-2.5-flash", result.message)
            self.assertIn("google-genai", result.message)
            self.assertEqual(manager.current_model, "gemini/gemini-2.5-flash")

    def test_aureon_offline_provider_answers_greeting_normally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _ = tmp
            with patch.dict(os.environ, {}, clear=True):
                provider = AureonProvider("aureon-queen")
                reply = provider.generate('{"user_request":"hello are you ai ?"}')
            payload = json.loads(reply)
            self.assertEqual(payload["action"], "respond")
            self.assertIn("lokalnym Aureon", payload["message"])

    @unittest.skipUnless(PLAYWRIGHT_AVAILABLE, "Playwright is not installed")
    def test_browser_open_search_screenshot_visible_text_and_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_local_site(root)
            project_dir = root / "project"
            project_dir.mkdir()
            memory = MemoryStore(project_dir, project_dir)
            _ = ExecutionEngine(project_dir, memory)

            browser_start()
            browser_open((root / "index.html").as_uri())
            browser_type("#query", "OpenAI")
            browser_press("Enter")
            current = browser_current_url()
            self.assertIn("#search=OpenAI", current["current_url"])

            text_result = browser_get_visible_text()
            self.assertIn("Search Results for OpenAI", text_result["text"])

            shot = browser_screenshot("local_search.png")
            self.assertTrue(Path(shot["screenshot_path"]).exists())

            browser_open((root / "index.html").as_uri())
            browser_click("#next-link")
            current = browser_current_url()
            self.assertIn("#clicked", current["current_url"])
            text_result = browser_get_visible_text()
            self.assertIn("Click confirmed", text_result["text"])

            browser_open((root / "page2.html").as_uri())
            current = browser_current_url()
            self.assertIn("page2.html", current["current_url"])
            text_result = browser_get_visible_text()
            self.assertIn("Second Page", text_result["text"])
            browser_close()

    def test_shell_execute_runs_curl_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            memory = MemoryStore(project_dir, project_dir)
            engine = ExecutionEngine(project_dir, memory)
            result = engine.execute(
                {
                    "action": "shell_execute",
                    "command": "curl --version",
                    "reason": "Check curl version.",
                    "requires_confirmation": False,
                }
            )
            self.assertTrue(result["success"])
            self.assertIn("curl", result["stdout"].lower())

    @staticmethod
    def _write_local_site(root: Path) -> None:
        (root / "index.html").write_text(
            """
            <html>
              <body>
                <h1>Local Search</h1>
                <form id="search-form">
                  <input id="query" name="q" type="text" />
                  <button id="submit" type="submit">Search</button>
                </form>
                <div id="result"></div>
                <button id="next-link" type="button">Click Next</button>
                <div id="nav-status"></div>
                <script>
                  const form = document.getElementById("search-form");
                  form.addEventListener("submit", function(event) {
                    event.preventDefault();
                    const q = document.getElementById("query").value;
                    document.getElementById("result").textContent = "Search Results for " + q;
                    window.location.hash = "search=" + encodeURIComponent(q);
                  });
                  document.getElementById("next-link").addEventListener("click", function() {
                    document.getElementById("nav-status").textContent = "Click confirmed";
                    window.location.hash = "clicked";
                  });
                </script>
              </body>
            </html>
            """,
            encoding="utf-8",
        )
        (root / "page2.html").write_text(
            """
            <html>
              <body>
                <h1>Second Page</h1>
                <p>Browser navigation succeeded.</p>
              </body>
            </html>
            """,
            encoding="utf-8",
        )


PROMPT_TEMPLATE = """
You are an autonomous AI runtime agent.
Desktop: __DESKTOP_DIR__
Project: __CURRENT_PROJECT__
cwd: __CURRENT_CWD__
Return one JSON object only.
""".strip()


def json_text(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
```

## `tests/test_rhcsa_retrieval.py`

- size: 2446 bytes
- sha256: `314e6f949eecdfeadfe13682929680c9f8d9383895773087c2900945d39f7191`
- category: tests

```python
import unittest

from tools.rhcsa_search import (
    exact_command_lookup,
    filter_by_topic,
    grep_rhcsa,
    library_status,
    load_topic,
    retrieve_examples,
    search_by_tag,
    search_rhcsa,
    suggest_related_commands,
)


class RHCSARetrievalTests(unittest.TestCase):
    def test_library_status_uses_local_knowledge_root(self) -> None:
        status = library_status()
        self.assertTrue(status["exists"])
        self.assertTrue(status["path"].endswith("/knowledge"))
        self.assertGreater(status["indexed_topics"], 0)

    def test_keyword_search_returns_filesystem_module(self) -> None:
        results = search_rhcsa("nawigacja plikow", limit=5)
        self.assertTrue(results)
        self.assertEqual(results[0]["category"], "filesystem")

    def test_tag_search_matches_exact_tag(self) -> None:
        results = search_by_tag("service-status", limit=5)
        self.assertTrue(results)
        self.assertTrue(any("systemctl-status.json" in item["file_location"] for item in results))

    def test_exact_command_lookup_matches_only_exact_command(self) -> None:
        results = exact_command_lookup("systemctl status", limit=5)
        self.assertTrue(results)
        self.assertTrue(any("systemctl-status.json" in item["file_location"] for item in results))

    def test_grep_retrieval_finds_literal_pattern(self) -> None:
        results = grep_rhcsa("Troubleshooting hint", limit=5)
        self.assertTrue(results)
        self.assertTrue(all("preview" in item for item in results))

    def test_topic_filter_restricts_results(self) -> None:
        results = filter_by_topic("networking", "ssh", limit=10)
        self.assertTrue(results)
        self.assertTrue(all(item["category"] == "networking" for item in results))

    def test_load_topic_returns_topic_markdown(self) -> None:
        text = load_topic("filesystem", max_chars=4000)
        self.assertIn("# Filesystem", text)

    def test_examples_retrieval_reads_local_json_examples(self) -> None:
        results = retrieve_examples("systemctl", limit=5)
        self.assertTrue(results)
        self.assertEqual(results[0]["topic"], "systemctl-status")

    def test_command_suggestions_are_deterministic(self) -> None:
        first = suggest_related_commands("podman", limit=5)
        second = suggest_related_commands("podman", limit=5)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
```

## `tests/test_routing_boundary.py`

- size: 6708 bytes
- sha256: `34cde37358c6678048133b7d502dcf0e0a76efaef56cb5403f64613e7708dc52`
- category: tests

```python
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main


PROMPT_TEMPLATE = """
You are an autonomous AI runtime agent.
Desktop: __DESKTOP_DIR__
Project: __CURRENT_PROJECT__
cwd: __CURRENT_CWD__
Return one JSON object only.
""".strip()


class FakeProvider:
    model_name = "fake/test-model"

    def describe(self) -> str:
        return self.model_name

    def active_fallback_chain(self) -> list[str]:
        return []

    def provider_status(self) -> list[dict]:
        return []

    def generate(self, prompt: str) -> str:
        _ = prompt
        return '{"plan":[{"action":"respond","message":"normal runtime response","reason":"test"}]}'


class RaisingKernel:
    def evaluate(self, user_request: str):
        raise AssertionError(f"RHCSA kernel must not receive external request: {user_request}")


class RecordingKernel:
    def __init__(self) -> None:
        self.called = False

    def evaluate(self, user_request: str):
        self.called = True
        return SimpleNamespace(
            should_respond_locally=True,
            route="local_knowledge",
            depth="shallow",
            pressure=34,
            confidence="medium",
            response="Local RHCSA route preserved.",
            manual_review_required=False,
            manual_review_reasons=(),
            evidence=(),
            reasoning={"query": user_request, "route": "local_knowledge"},
        )


class RecordingExecutor:
    def __init__(self) -> None:
        self.actions: list[dict] = []

    def execute(self, action: dict, require_approval: bool = True):
        _ = require_approval
        self.actions.append(action)
        if action["action"] == "browser_open":
            return {
                "success": True,
                "message": f"Opened {action['url']}",
                "current_url": action["url"],
                "open_tabs": [action["url"]],
            }
        if action["action"] == "browser_get_visible_text":
            return {
                "success": True,
                "message": "Read visible page text.",
                "text": "GitHub page text",
            }
        raise AssertionError(f"Unexpected action: {action}")


class RoutingBoundaryTests(unittest.TestCase):
    def test_model_question_is_not_external_review(self) -> None:
        self.assertIsNone(main.classify_external_review_request("jakim jestes modelem"))

    def test_model_question_uses_normal_runtime_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runtime = main.AgentRuntime(FakeProvider(), PROMPT_TEMPLATE, project_dir)
            runtime.safeguards = main.EpistemicSafeguards(
                kill_switch=False,
                disable_model=False,
                disable_knowledge=True,
                disable_memory_hats=True,
                reasoning_trace_enabled=False,
                prefer_unknown=True,
            )

            with patch("sys.stdout", new_callable=StringIO) as fake_stdout:
                runtime.handle_user_request("jakim jestes modelem")

            self.assertIn("normal runtime response", fake_stdout.getvalue())

    def test_github_url_does_not_trigger_rhcsa_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runtime = main.AgentRuntime(FakeProvider(), PROMPT_TEMPLATE, project_dir)
            executor = RecordingExecutor()
            runtime.executor = executor
            runtime.aoia_kernel = RaisingKernel()

            with patch("sys.stdout", new_callable=StringIO) as fake_stdout:
                runtime.handle_user_request("https://github.com/luciferprosun/AOIA-Core")

            transcript = fake_stdout.getvalue()
            self.assertEqual([action["action"] for action in executor.actions], ["browser_open", "browser_get_visible_text"])
            self.assertIn("Opened https://github.com/luciferprosun/AOIA-Core", transcript)
            self.assertIn("Current URL: https://github.com/luciferprosun/AOIA-Core", transcript)
            self.assertIn("GitHub page text", transcript)
            self.assertNotIn("AOIA deterministic epistemic kernel hit", transcript)

    def test_repository_intent_does_not_trigger_rhcsa_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runtime = main.AgentRuntime(FakeProvider(), PROMPT_TEMPLATE, project_dir)
            runtime.aoia_kernel = RaisingKernel()

            with patch("sys.stdout", new_callable=StringIO) as fake_stdout:
                runtime.handle_user_request("can you check github repository")

            transcript = fake_stdout.getvalue()
            self.assertIn("External repository inspection path detected", transcript)
            self.assertIn("Browser inspection path available", transcript)
            self.assertNotIn("AOIA deterministic epistemic kernel hit", transcript)

    def test_repository_inspection_intent_does_not_trigger_rhcsa_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runtime = main.AgentRuntime(FakeProvider(), PROMPT_TEMPLATE, project_dir)
            runtime.aoia_kernel = RaisingKernel()

            with patch("sys.stdout", new_callable=StringIO) as fake_stdout:
                runtime.handle_user_request("can you inspect github repository")

            transcript = fake_stdout.getvalue()
            self.assertIn("External repository inspection path detected", transcript)
            self.assertIn("Browser inspection path available", transcript)
            self.assertNotIn("AOIA deterministic epistemic kernel hit", transcript)

    def test_linux_request_still_uses_rhcsa_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            runtime = main.AgentRuntime(FakeProvider(), PROMPT_TEMPLATE, project_dir)
            kernel = RecordingKernel()
            runtime.aoia_kernel = kernel

            with patch("sys.stdout", new_callable=StringIO) as fake_stdout:
                runtime.handle_user_request("how to create folder in linux")

            self.assertTrue(kernel.called)
            self.assertIn("Local RHCSA route preserved.", fake_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
```

