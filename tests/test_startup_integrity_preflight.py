from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.startup_preflight import (
    ANCHOR_REGISTRY_ENV,
    ANCHOR_ROOT_ENV,
    ANCHOR_ROOT_FINGERPRINT_ENV,
    AnchorConfigurationStatus,
    ConfigClassification,
    StartupMode,
    StartupStatus,
    _contains_sensitive_key,
    _derive_state_root,
    run_startup_preflight,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PROJECT = REPOSITORY_ROOT / "runtime"


class _FakeStartupReport:
    """Minimal fixed report used to prove activation-gate ordering."""

    def __init__(self, *, activation: bool, web_listener: bool = False, port: int = 4311):
        self.state_changing_execution_enabled = activation
        self._web_listener = activation and web_listener
        self._port = port

    def capability_enabled(self, name: str) -> bool:
        return name == "web_listener" and self._web_listener

    def bounded_setting_value(self, name: str) -> int | None:
        return self._port if name == "web_port" else None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "AOIA_STARTUP_PREFLIGHT_1A",
            "status": "READY_DEGRADED" if self.state_changing_execution_enabled else "BLOCKED_STATE",
            "reason_codes": ["STARTUP_SYNTHETIC_GATE"],
        }


class StartupIntegrityPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.project = self.root / "project" / "runtime"
        prompt = self.project / "prompts" / "system_prompt.txt"
        prompt.parent.mkdir(parents=True)
        prompt.write_text("bounded synthetic prompt\n", encoding="utf-8")
        self.aoia_home = self.root / "aoia-state"
        self.aoia_home.mkdir(mode=0o700)
        self.environ: dict[str, str] = {"AOIA_HOME": str(self.aoia_home)}
        self.state_root = _derive_state_root(self.project.resolve(), self.environ)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def report(self, **kwargs):
        return run_startup_preflight(
            self.project.resolve(),
            environ=dict(self.environ),
            **kwargs,
        )

    @staticmethod
    def write_private(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600)

    @staticmethod
    def write_private_text(path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        path.chmod(0o600)

    @staticmethod
    def snapshot(root: Path) -> tuple[tuple[str, str, object], ...]:
        if not root.exists() and not root.is_symlink():
            return ()
        values: list[tuple[str, str, object]] = []
        for path in sorted((root, *root.rglob("*")), key=lambda item: str(item)):
            relative = "." if path == root else path.relative_to(root).as_posix()
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                values.append((relative, "symlink", os.readlink(path)))
            elif stat.S_ISREG(metadata.st_mode):
                values.append((relative, "file", path.read_bytes()))
            elif stat.S_ISDIR(metadata.st_mode):
                values.append((relative, "directory", stat.S_IMODE(metadata.st_mode)))
            else:
                values.append((relative, "other", metadata.st_mode))
        return tuple(values)

    def test_valid_cli_config_is_explicitly_degraded_only_for_optional_anchor_and_commit(self) -> None:
        report = self.report()

        self.assertEqual(StartupStatus.READY_DEGRADED, report.status)
        self.assertEqual(AnchorConfigurationStatus.ANCHOR_NOT_CONFIGURED, report.anchor_status)
        self.assertTrue(report.state_changing_execution_enabled)
        self.assertFalse(self.state_root.exists())
        self.assertIn("STARTUP_ANCHOR_NOT_CONFIGURED", report.reason_codes)
        self.assertIn("STARTUP_SOURCE_COMMIT_UNAVAILABLE", report.reason_codes)

    def test_valid_web_config_requires_and_accepts_operator_secret_reference(self) -> None:
        self.environ["AOIA_WEB_OPERATOR_TOKEN"] = "synthetic-operator-token-0001"
        report = self.report(mode=StartupMode.WEB)

        self.assertEqual(StartupStatus.READY_DEGRADED, report.status)
        self.assertTrue(report.capability_enabled("web_listener"))

    def test_web_mode_missing_token_blocks_before_listener(self) -> None:
        report = self.report(mode=StartupMode.WEB)

        self.assertEqual(StartupStatus.BLOCKED_CONFIGURATION, report.status)
        self.assertFalse(report.capability_enabled("web_listener"))
        self.assertFalse(self.state_root.exists())

    def test_unsafe_web_bound_is_blocked_even_when_web_is_not_requested(self) -> None:
        self.environ["AOIA_WEB_MAX_CONCURRENT_REQUESTS"] = "0"
        report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_CONFIGURATION, report.status)
        self.assertIn("STARTUP_WEB_LIMIT_INVALID", report.reason_codes)

    def test_provider_max_tokens_is_strictly_bounded_and_reported(self) -> None:
        self.environ["OPENAI_COMPATIBLE_MAX_TOKENS"] = "4096"
        report = self.report()

        self.assertEqual(4096, report.bounded_setting_value("provider_max_tokens"))
        observation = next(
            item for item in report.configuration
            if item.name == "OPENAI_COMPATIBLE_MAX_TOKENS"
        )
        self.assertEqual(ConfigClassification.BOUNDED_TUNABLE, observation.classification)
        self.assertTrue(observation.configured)

        for invalid in ("0", "4097", "+1", "1.0", " unlimited "):
            with self.subTest(invalid=invalid):
                self.environ["OPENAI_COMPATIBLE_MAX_TOKENS"] = invalid
                invalid_report = self.report()
                self.assertEqual(StartupStatus.BLOCKED_CONFIGURATION, invalid_report.status)
                self.assertIn("STARTUP_PROVIDER_SETTING_INVALID", invalid_report.reason_codes)

    def test_provider_urls_and_model_identifier_are_validated_without_echo(self) -> None:
        cases = (
            ("OLLAMA_BASE_URL", "file:///etc/passwd"),
            ("GEMMA_OPENAI_BASE_URL", "https://user:canary@example.invalid/v1"),
            ("DEEPSEEK_BASE_URL", "https://example.invalid/v1?token=canary"),
            ("XAI_BASE_URL", "https://example.invalid/#canary"),
            ("GEMMA_HF_MODEL", "../canary-model"),
        )
        for name, invalid in cases:
            with self.subTest(name=name):
                environment = dict(self.environ)
                environment[name] = invalid
                report = run_startup_preflight(self.project.resolve(), environ=environment)
                encoded = json.dumps(report.to_dict(), sort_keys=True)
                self.assertEqual(StartupStatus.BLOCKED_CONFIGURATION, report.status)
                self.assertIn("STARTUP_PROVIDER_SETTING_INVALID", report.reason_codes)
                self.assertNotIn("canary", encoded)

    def test_agent_debug_uses_exact_boolean_parsing(self) -> None:
        self.environ["AGENT_DEBUG"] = "sometimes"
        report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_CONFIGURATION, report.status)
        self.assertIn("STARTUP_BOOLEAN_SETTING_INVALID", report.reason_codes)

    def test_invalid_boolean_setting_is_not_silently_coerced(self) -> None:
        self.environ["EPISTEMIC_KILL_SWITCH"] = "sometimes"
        report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_CONFIGURATION, report.status)
        self.assertIn("STARTUP_BOOLEAN_SETTING_INVALID", report.reason_codes)

    def test_security_weakening_flag_is_blocked(self) -> None:
        self.environ["EPISTEMIC_DISABLE_UNKNOWN_FALLBACK"] = "true"
        report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_SECURITY_INVARIANT, report.status)
        self.assertFalse(report.state_changing_execution_enabled)

    def test_provider_activation_requires_manual_review_and_is_reported_truthfully(self) -> None:
        self.environ["AOIA_PROVIDER_CALLS_ENABLED"] = "1"
        report = self.report()

        self.assertEqual(StartupStatus.MANUAL_REVIEW_REQUIRED, report.status)
        self.assertIn("STARTUP_PROVIDER_ACTIVATION_REVIEW_REQUIRED", report.reason_codes)
        self.assertFalse(report.capability_enabled("provider_calls"))
        self.assertFalse(report.state_changing_execution_enabled)

    def test_missing_required_prompt_blocks(self) -> None:
        (self.project / "prompts" / "system_prompt.txt").unlink()
        report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_CONFIGURATION, report.status)
        self.assertFalse(self.state_root.exists())

    def test_missing_project_is_blocked_without_creating_it(self) -> None:
        missing = self.root / "missing-project" / "runtime"

        report = run_startup_preflight(missing, environ=dict(self.environ))

        self.assertEqual(StartupStatus.BLOCKED_CONFIGURATION, report.status)
        self.assertFalse(missing.exists())
        self.assertFalse(self.state_root.exists())

    def test_corrupt_agent_state_is_read_only_and_blocks_runtime(self) -> None:
        corrupt = self.state_root / "state" / "agent_state.json"
        self.write_private_text(corrupt, "{not-json")
        before = self.snapshot(self.state_root)

        with patch("runtime.startup_preflight.atomic_write_json") as atomic_write:
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_STATE, report.status)
        self.assertIn("STARTUP_AGENT_MEMORY_INVALID", report.reason_codes)
        self.assertEqual(before, self.snapshot(self.state_root))
        atomic_write.assert_not_called()

    def test_corrupt_checkpoint_is_read_only_and_blocks_runtime(self) -> None:
        checkpoint = (
            self.state_root
            / "state"
            / "tasks"
            / ("a" * 64)
            / "checkpoint.json"
        )
        self.write_private_text(checkpoint, "{not-json")
        before = self.snapshot(self.state_root)

        with patch("runtime.startup_preflight.atomic_write_json") as atomic_write:
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_STATE, report.status)
        self.assertIn("STARTUP_TASK_CHECKPOINT_INVALID", report.reason_codes)
        self.assertEqual(before, self.snapshot(self.state_root))
        atomic_write.assert_not_called()

    def test_corrupt_idempotency_record_is_read_only_and_blocks_runtime(self) -> None:
        record = self.state_root / "state" / "idempotency" / (("b" * 64) + ".json")
        self.write_private_text(record, "{not-json")
        before = self.snapshot(self.state_root)

        with patch("runtime.startup_preflight.atomic_write_json") as atomic_write:
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_STATE, report.status)
        self.assertIn("STARTUP_IDEMPOTENCY_INVALID", report.reason_codes)
        self.assertEqual(before, self.snapshot(self.state_root))
        atomic_write.assert_not_called()

    def test_corrupt_provenance_is_read_only_and_blocks_runtime(self) -> None:
        ledger = self.state_root / "state" / "provenance" / "runtime_provenance_log.jsonl"
        self.write_private_text(ledger, "partial-record")
        before = self.snapshot(self.state_root)

        with patch("runtime.startup_preflight.atomic_write_json") as atomic_write:
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_PROVENANCE, report.status)
        self.assertIn("STARTUP_PROVENANCE_INVALID", report.reason_codes)
        self.assertEqual(before, self.snapshot(self.state_root))
        atomic_write.assert_not_called()

    def test_valid_terminal_outbox_is_degraded_recovery_pending_and_unchanged(self) -> None:
        from runtime.tools.provenance import (
            RuntimeProvenanceEventType,
            new_runtime_provenance_event,
        )
        from runtime.trace_context import TraceContext

        event = new_runtime_provenance_event(
            RuntimeProvenanceEventType.REQUEST_COMPLETED,
            trace_context=TraceContext.new_request(),
            ingress="RUNTIME",
            success=True,
        )
        pending = (
            self.state_root
            / "state"
            / "provenance"
            / "outbox"
            / f"{event.event_id}.json"
        )
        self.write_private(pending, event.outbox_document())
        before = self.snapshot(self.state_root)

        report = self.report()

        self.assertEqual(StartupStatus.READY_DEGRADED, report.status)
        self.assertIn("STARTUP_PROVENANCE_RECOVERY_REQUIRED", report.reason_codes)
        self.assertTrue(report.state_changing_execution_enabled)
        self.assertEqual(before, self.snapshot(self.state_root))

    def test_malformed_terminal_outbox_blocks_without_mutation(self) -> None:
        pending = (
            self.state_root
            / "state"
            / "provenance"
            / "outbox"
            / ("provenance_event_" + "a" * 32 + ".json")
        )
        self.write_private_text(pending, "{malformed")
        before = self.snapshot(self.state_root)

        with patch("runtime.startup_preflight.atomic_write_json") as atomic_write:
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_PROVENANCE, report.status)
        self.assertEqual(before, self.snapshot(self.state_root))
        atomic_write.assert_not_called()

    def test_durable_idempotency_without_runtime_ledger_blocks_provenance(self) -> None:
        import datetime as dt
        import uuid

        from runtime.tools.idempotency import (
            IDEMPOTENCY_RESERVED_REASON_CODE,
            IDEMPOTENCY_SCHEMA_VERSION,
            IdempotencyRecord,
            IdempotencyState,
            OperationContext,
        )

        operation = OperationContext.new_operation()
        now = dt.datetime(2026, 1, 1, tzinfo=dt.UTC).isoformat().replace("+00:00", "Z")
        runtime_id = lambda prefix: f"{prefix}_{uuid.uuid4().hex}"
        record = IdempotencyRecord(
            schema_version=IDEMPOTENCY_SCHEMA_VERSION,
            operation_key=operation.operation_key,
            project_scope=self.report().project_identity or "",
            task_id=runtime_id("task"),
            request_id=runtime_id("request"),
            trace_id=runtime_id("trace"),
            action_id=runtime_id("action"),
            model_call_id=None,
            action_fingerprint="b" * 64,
            capability_class="LOCAL_STATE_CHANGE",
            state=IdempotencyState.RESERVED,
            created_at=now,
            updated_at=now,
            reason_code=IDEMPOTENCY_RESERVED_REASON_CODE,
            terminal_receipt=None,
        )
        record.validate()
        digest = __import__("hashlib").sha256(operation.operation_key.encode("ascii")).hexdigest()
        self.write_private(
            self.state_root / "state" / "idempotency" / f"{digest}.json",
            record.to_payload(),
        )

        report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_PROVENANCE, report.status)
        self.assertIn("STARTUP_RUNTIME_PROVENANCE_REQUIRED", report.reason_codes)

    def test_atomic_probe_failure_blocks_and_removes_probe_directories(self) -> None:
        with patch(
            "runtime.startup_preflight.atomic_write_json",
            side_effect=OSError("synthetic probe failure"),
        ):
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_STATE, report.status)
        self.assertIn("STARTUP_PERSISTENCE_PROBE_FAILED", report.reason_codes)
        self.assertFalse(self.state_root.exists())

    def test_symlinked_empty_state_directory_is_not_false_clean(self) -> None:
        self.state_root.mkdir(parents=True)
        target = self.root / "attacker-state"
        target.mkdir()
        (self.state_root / "state").symlink_to(target, target_is_directory=True)
        before = self.snapshot(self.state_root)

        report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_SECURITY_INVARIANT, report.status)
        self.assertIn("STARTUP_STATE_LAYOUT_UNSAFE", report.reason_codes)
        self.assertEqual(before, self.snapshot(self.state_root))

    def test_state_lock_symlink_is_rejected_without_probe(self) -> None:
        state_dir = self.state_root / "state"
        state_dir.mkdir(parents=True)
        outside = self.root / "outside-locks"
        outside.mkdir()
        (state_dir / ".locks").symlink_to(outside, target_is_directory=True)
        before = self.snapshot(self.state_root)

        report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_STATE, report.status)
        self.assertIn("STARTUP_STATE_LOCK_INVALID", report.reason_codes)
        self.assertEqual(before, self.snapshot(self.state_root))

    def test_private_ancestor_allows_lower_group_readable_directories(self) -> None:
        self.state_root.mkdir(parents=True)
        self.state_root.chmod(0o775)
        (self.state_root / "state").mkdir(mode=0o775)

        report = self.report()

        self.assertEqual(StartupStatus.READY_DEGRADED, report.status)

    def test_exposed_state_home_is_rejected(self) -> None:
        exposed = Path(tempfile.mkdtemp(prefix="aoia-p21-public-", dir="/tmp"))
        try:
            exposed.chmod(0o777)
            self.environ["AOIA_HOME"] = str(exposed)
            report = self.report()
            self.assertEqual(StartupStatus.BLOCKED_SECURITY_INVARIANT, report.status)
            self.assertIn("STARTUP_STATE_LAYOUT_UNSAFE", report.reason_codes)
        finally:
            exposed.rmdir()

    def test_state_owner_mismatch_is_rejected(self) -> None:
        self.state_root.mkdir(parents=True)
        with patch("runtime.startup_preflight.os.getuid", return_value=os.getuid() + 1):
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_SECURITY_INVARIANT, report.status)

    def test_partial_anchor_configuration_is_not_reported_valid(self) -> None:
        self.environ[ANCHOR_ROOT_ENV] = str(self.root / "anchors")
        report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_CONFIGURATION, report.status)
        self.assertEqual(
            AnchorConfigurationStatus.ANCHOR_CONFIGURATION_INCOMPLETE,
            report.anchor_status,
        )

    def _configured_anchor_directories(self) -> None:
        anchor_root = self.root / "anchors"
        registry = self.root / "registry"
        anchor_root.mkdir(mode=0o700)
        registry.mkdir(mode=0o700)
        self.environ.update(
            {
                ANCHOR_ROOT_ENV: str(anchor_root),
                ANCHOR_REGISTRY_ENV: str(registry),
                ANCHOR_ROOT_FINGERPRINT_ENV: "a" * 64,
            }
        )

    def test_anchor_pointer_or_archive_mismatch_remains_blocked(self) -> None:
        self._configured_anchor_directories()
        from runtime.tools.provenance_anchor import AnchorStatus, AnchorVerificationResult

        result = AnchorVerificationResult(
            status=AnchorStatus.ANCHOR_LEDGER_MISMATCH,
            message_safe="synthetic mismatch",
        )
        with patch(
            "runtime.tools.provenance_anchor.verify_latest_provenance_anchor",
            return_value=result,
        ):
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_PROVENANCE, report.status)
        self.assertEqual(AnchorConfigurationStatus.ANCHOR_LEDGER_MISMATCH, report.anchor_status)

    def test_exact_current_valid_anchor_produces_ready(self) -> None:
        self._configured_anchor_directories()
        from runtime.tools.provenance_anchor import AnchorStatus, AnchorVerificationResult

        result = AnchorVerificationResult(
            status=AnchorStatus.ANCHOR_VALID,
            anchor_id="anchor_" + "d" * 32,
            anchored_entry_count=0,
            actual_entry_count=0,
            is_current=True,
            public_key_fingerprint="e" * 64,
            message_safe="synthetic current anchor",
        )
        with (
            patch("runtime.startup_preflight._read_source_commit", return_value="f" * 40),
            patch(
                "runtime.tools.provenance_anchor.verify_latest_provenance_anchor",
                return_value=result,
            ),
        ):
            report = self.report()

        self.assertEqual(StartupStatus.READY, report.status)
        self.assertEqual(AnchorConfigurationStatus.ANCHOR_VALID, report.anchor_status)
        self.assertTrue(report.state_changing_execution_enabled)

    def test_invalid_signature_and_unknown_anchor_key_block_provenance(self) -> None:
        self._configured_anchor_directories()
        from runtime.tools.provenance_anchor import AnchorStatus, AnchorVerificationResult

        cases = (
            (
                AnchorStatus.ANCHOR_SIGNATURE_INVALID,
                AnchorConfigurationStatus.ANCHOR_SIGNATURE_INVALID,
            ),
            (
                AnchorStatus.ANCHOR_UNKNOWN_KEY,
                AnchorConfigurationStatus.ANCHOR_UNKNOWN_KEY,
            ),
        )
        for verifier_status, expected_status in cases:
            with self.subTest(verifier_status=verifier_status.value):
                result = AnchorVerificationResult(
                    status=verifier_status,
                    message_safe="synthetic invalid anchor",
                )
                with patch(
                    "runtime.tools.provenance_anchor.verify_latest_provenance_anchor",
                    return_value=result,
                ):
                    report = self.report()

                self.assertEqual(StartupStatus.BLOCKED_PROVENANCE, report.status)
                self.assertEqual(expected_status, report.anchor_status)
                self.assertFalse(report.state_changing_execution_enabled)

    def test_verified_historical_anchor_shape_is_explicitly_stale(self) -> None:
        self._configured_anchor_directories()
        from runtime.tools.provenance_anchor import AnchorStatus, AnchorVerificationResult

        result = AnchorVerificationResult(
            status=AnchorStatus.ANCHOR_LEDGER_MISMATCH,
            anchor_id="anchor_" + "b" * 32,
            anchored_entry_count=2,
            actual_entry_count=3,
            public_key_fingerprint="c" * 64,
            message_safe="synthetic verified historical checkpoint",
        )
        with patch(
            "runtime.tools.provenance_anchor.verify_latest_provenance_anchor",
            return_value=result,
        ):
            report = self.report()

        self.assertEqual(StartupStatus.READY_DEGRADED, report.status)
        self.assertEqual(AnchorConfigurationStatus.ANCHOR_STALE, report.anchor_status)
        self.assertTrue(report.state_changing_execution_enabled)

    def test_secret_values_never_enter_report(self) -> None:
        canaries = (
            "synthetic-operator-secret-canary-001",
            "synthetic-provider-secret-canary-002",
            "synthetic-private-key-canary-003",
        )
        self.environ.update(
            {
                "AOIA_WEB_OPERATOR_TOKEN": canaries[0],
                "OPENROUTER_API_KEY": canaries[1],
                "AOIA_PROVENANCE_PRIVATE_KEY": canaries[2],
            }
        )

        encoded = json.dumps(self.report().to_dict(), sort_keys=True)

        for canary in canaries:
            self.assertNotIn(canary, encoded)
        self.assertNotIn(str(self.project), encoded)
        self.assertNotIn(str(self.aoia_home), encoded)

    def test_expected_commit_cannot_override_independently_read_head(self) -> None:
        report = run_startup_preflight(
            RUNTIME_PROJECT,
            environ={"AOIA_HOME": str(self.aoia_home)},
            repository_root=REPOSITORY_ROOT,
            expected_source_commit="0" * 40,
        )

        self.assertEqual(StartupStatus.BLOCKED_SECURITY_INVARIANT, report.status)
        self.assertNotEqual("0" * 40, report.source_commit)

    def test_max_tokens_is_not_misclassified_as_a_secret_field(self) -> None:
        self.assertFalse(_contains_sensitive_key({"default_max_tokens": 256}))
        self.assertTrue(_contains_sensitive_key({"api_key": "canary"}))

    def test_non_string_environment_value_fails_without_echoing_value(self) -> None:
        invalid: dict[str, object] = dict(self.environ)
        invalid["AOIA_HOME"] = 12345
        report = run_startup_preflight(self.project.resolve(), environ=invalid)  # type: ignore[arg-type]

        self.assertIn(
            report.status,
            {StartupStatus.BLOCKED_CONFIGURATION, StartupStatus.BLOCKED_SECURITY_INVARIANT},
        )
        self.assertNotIn("12345", json.dumps(report.to_dict(), sort_keys=True))

    def test_unrecognized_client_and_model_fields_cannot_override_security_truth(self) -> None:
        self.environ.update(
            {
                "CLIENT_AOIA_HOME": str(self.root / "attacker-state-root"),
                "MODEL_STARTUP_STATUS": "READY",
                "MODEL_STATE_CHANGING_EXECUTION_ENABLED": "1",
                "CLIENT_PROCESS_RESOURCE_PROFILE_COUNT": "0",
            }
        )
        self.write_private(
            self.state_root / "state" / "model_config.json",
            {
                "model": "synthetic-model",
                "startup_status": "READY",
                "state_root": str(self.root / "attacker-state-root"),
                "process_resource_profiles": {},
                "capabilities": {"state_changing_execution": True},
            },
        )
        self.write_private_text(self.state_root / "state" / "agent_state.json", "{not-json")
        before = self.snapshot(self.state_root)

        with patch("runtime.startup_preflight.atomic_write_json") as atomic_write:
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_STATE, report.status)
        self.assertFalse(report.state_changing_execution_enabled)
        self.assertFalse(report.capability_enabled("provider_calls"))
        self.assertEqual(
            len(__import__("runtime.safety.bounded_subprocess", fromlist=["SUBPROCESS_RESOURCE_PROFILES"]).SUBPROCESS_RESOURCE_PROFILES),
            report.bounded_setting_value("subprocess_resource_profile_count"),
        )
        expected_identity = __import__("hashlib").sha256(
            ("AOIA_STARTUP_STATE_ROOT_IDENTITY_1A\x00" + str(self.state_root)).encode("utf-8")
        ).hexdigest()
        self.assertEqual(expected_identity, report.state_root_identity)
        self.assertNotIn("attacker-state-root", json.dumps(report.to_dict(), sort_keys=True))
        self.assertEqual(before, self.snapshot(self.state_root))
        atomic_write.assert_not_called()

    def test_process_profile_above_reviewed_ceiling_blocks_startup(self) -> None:
        import runtime.startup_preflight as startup_preflight

        profiles = dict(startup_preflight.SUBPROCESS_RESOURCE_PROFILES)
        name = next(iter(profiles))
        profiles[name] = replace(profiles[name], cpu_seconds=601)

        with patch.object(startup_preflight, "SUBPROCESS_RESOURCE_PROFILES", profiles):
            report = self.report()

        self.assertEqual(StartupStatus.BLOCKED_SECURITY_INVARIANT, report.status)
        self.assertIn("STARTUP_RUNTIME_BOUND_INVALID", report.reason_codes)
        self.assertFalse(report.state_changing_execution_enabled)

    def test_configuration_contract_contains_every_class_and_unique_names(self) -> None:
        report = self.report()
        names = [item.name for item in report.configuration]

        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(ConfigClassification), {item.classification for item in report.configuration})

    def test_cli_blocked_preflight_constructs_no_runtime_objects(self) -> None:
        import main as runtime_main

        report = _FakeStartupReport(activation=False)
        with (
            patch("runtime.startup_preflight.run_startup_preflight", return_value=report),
            patch.object(runtime_main, "ProviderManager") as provider_manager,
            patch.object(runtime_main, "AgentRuntime") as agent_runtime,
            patch.object(runtime_main, "load_prompt_template") as prompt_loader,
        ):
            with self.assertRaisesRegex(SystemExit, "2"):
                runtime_main.main()

        provider_manager.assert_not_called()
        agent_runtime.assert_not_called()
        prompt_loader.assert_not_called()

    def test_cli_ready_degraded_preflight_allows_runtime_construction(self) -> None:
        import main as runtime_main

        report = _FakeStartupReport(activation=True)
        provider = object()
        runtime = object()
        with (
            patch(
                "runtime.startup_preflight.run_startup_preflight",
                return_value=report,
            ) as preflight,
            patch.object(runtime_main, "ProviderManager", return_value=provider) as provider_manager,
            patch.object(runtime_main, "AgentRuntime", return_value=runtime) as agent_runtime,
            patch.object(runtime_main, "load_prompt_template", return_value="prompt") as prompt_loader,
            patch.object(runtime_main, "print_banner") as banner,
            patch("builtins.input", return_value="quit"),
        ):
            runtime_main.main()

        provider_manager.assert_called_once_with(runtime_main.PROJECT_DIR)
        prompt_loader.assert_called_once_with(runtime_main.PROMPT_FILE)
        agent_runtime.assert_called_once()
        banner.assert_called_once_with(runtime)
        self.assertIsInstance(preflight.call_args.kwargs["environ"], dict)

    def test_web_blocked_preflight_constructs_no_service_or_listener(self) -> None:
        from runtime import webapp

        report = _FakeStartupReport(activation=False)
        with (
            patch("runtime.startup_preflight.run_startup_preflight", return_value=report),
            patch.object(webapp, "load_web_boundary_config") as boundary_loader,
            patch.object(webapp, "WebRuntimeService") as runtime_service,
            patch.object(webapp, "AOIAWebServer") as web_server,
        ):
            with self.assertRaisesRegex(SystemExit, "2"):
                webapp.main()

        boundary_loader.assert_not_called()
        runtime_service.assert_not_called()
        web_server.assert_not_called()

    def test_web_ready_degraded_uses_validated_port_before_listener(self) -> None:
        from runtime import webapp

        report = _FakeStartupReport(activation=True, web_listener=True, port=54321)
        server = MagicMock()
        with (
            patch(
                "runtime.startup_preflight.run_startup_preflight",
                return_value=report,
            ) as preflight,
            patch.object(webapp, "load_web_boundary_config", return_value=object()) as boundary_loader,
            patch.object(webapp, "AOIAWebServer", return_value=server) as web_server,
            patch.dict(os.environ, {"APP2_WEB_HOST": "127.0.0.1"}, clear=False),
        ):
            webapp.main()

        boundary_loader.assert_called_once()
        self.assertEqual("127.0.0.1", boundary_loader.call_args.kwargs["host"])
        self.assertEqual(54321, boundary_loader.call_args.kwargs["port"])
        self.assertIsInstance(boundary_loader.call_args.kwargs["environ"], dict)
        self.assertIs(
            preflight.call_args.kwargs["environ"],
            boundary_loader.call_args.kwargs["environ"],
        )
        web_server.assert_called_once()
        self.assertEqual(("127.0.0.1", 54321), web_server.call_args.args[0])
        server.serve_forever.assert_called_once_with()
        server.server_close.assert_called_once_with()

    def test_web_module_import_does_not_parse_untrusted_port(self) -> None:
        import importlib
        from runtime import webapp

        with patch.dict(os.environ, {"APP2_WEB_PORT": "not-an-integer"}, clear=False):
            reloaded = importlib.reload(webapp)

        self.assertEqual(4311, reloaded.PORT)


if __name__ == "__main__":
    unittest.main()
