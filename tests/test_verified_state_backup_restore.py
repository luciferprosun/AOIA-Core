from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime.state_backup as backup_module
from runtime.startup_preflight import (
    ANCHOR_REGISTRY_ENV,
    ANCHOR_ROOT_ENV,
    ANCHOR_ROOT_FINGERPRINT_ENV,
    _derive_state_root,
)
from runtime.state_backup import (
    BackupStatus,
    ResourceClassification,
    RestoreResult,
    RestoreStatus,
    StateBackupDestinationError,
    create_state_backup,
    restore_state_backup,
    run_local_disaster_recovery_drill,
    verify_state_backup,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PROJECT = REPOSITORY_ROOT / "runtime"


class VerifiedStateBackupRestoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="aoia-p22-backup-")
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.home = self.root / "source-home"
        self.backups = self.root / "backups"
        self.home.mkdir(mode=0o700)
        self.backups.mkdir(mode=0o700)
        self.environment = {"AOIA_HOME": str(self.home)}
        self.state_root = _derive_state_root(RUNTIME_PROJECT.resolve(), self.environment)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def write_private(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600)

    @staticmethod
    def write_private_bytes(path: Path, value: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_bytes(value)
        path.chmod(0o600)

    def add_config(self) -> None:
        self.write_private(
            self.state_root / "state" / "model_config.json",
            {"model": "synthetic-local-model"},
        )
        self.write_private(
            self.state_root / "state" / "providers.json",
            {
                "providers": [
                    {"name": "local", "model": "synthetic", "enabled": False}
                ]
            },
        )

    def create(self):
        return create_state_backup(
            RUNTIME_PROJECT,
            self.backups,
            environ=self.environment,
            repository_root=REPOSITORY_ROOT,
        )

    def rewrite_manifest_for_payload(
        self,
        backup_path: Path,
        relative_path: str,
    ) -> Path:
        """Keep the outer backup envelope self-consistent after inner tampering."""

        payload_path = backup_path / "payload" / Path(relative_path)
        payload = payload_path.read_bytes()
        manifest_path = backup_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        row = next(
            item for item in manifest["resources"]
            if item["relative_path"] == relative_path
        )
        row["size_bytes"] = len(payload)
        row["sha256"] = hashlib.sha256(payload).hexdigest()
        return self.rewrite_manifest_core(backup_path, manifest)

    def rewrite_manifest_core(
        self,
        backup_path: Path,
        manifest: dict[str, object],
    ) -> Path:
        manifest_path = backup_path / "manifest.json"
        core = {
            key: value
            for key, value in manifest.items()
            if key not in {"backup_id", "core_hash"}
        }
        digest = backup_module._core_hash(core)
        manifest["core_hash"] = digest
        manifest["backup_id"] = f"backup_{digest}"
        manifest_path.write_bytes(backup_module._canonical_json(manifest))
        renamed = backup_path.parent / manifest["backup_id"]
        backup_path.rename(renamed)
        return renamed

    def create_anchored_backup(self):
        from runtime.tools.provenance import AppendOnlyProvenanceStore
        from runtime.tools.provenance_anchor import (
            create_provenance_anchor,
            provision_external_signing_key,
            register_initial_verification_key,
        )

        project = self.root / "anchor-project"
        prompt = project / "prompts" / "system_prompt.txt"
        prompt.parent.mkdir(parents=True)
        prompt.write_text("anchor prompt\n")
        home = self.root / "anchor-home"
        home.mkdir(mode=0o700)
        environment = {"AOIA_HOME": str(home)}
        runtime_root = _derive_state_root(project.resolve(), environment)
        store = AppendOnlyProvenanceStore(runtime_root / "state")
        key_dir = self.root / "keys-private"
        registry = self.root / "key-registry"
        anchors = self.root / "anchor-records"
        anchor_backups = self.root / "anchor-backups"
        for path in (key_dir, registry, anchors, anchor_backups):
            path.mkdir(mode=0o700)
        key = key_dir / "key.pem"
        fingerprint = provision_external_signing_key(
            key,
            repository_root=project,
            project_dir=project,
            ledger_path=store.runtime_log_path,
            anchor_root=anchors,
            public_key_registry=registry,
        )
        register_initial_verification_key(
            registry,
            private_key_path=key,
            repository_root=project,
            project_dir=project,
        )
        create_provenance_anchor(
            store.runtime_log_path,
            anchors,
            registry,
            private_key_path=key,
            expected_root_fingerprint=fingerprint,
            repository_root=project,
            project_dir=project,
        )
        environment.update(
            {
                ANCHOR_ROOT_ENV: str(anchors),
                ANCHOR_REGISTRY_ENV: str(registry),
                ANCHOR_ROOT_FINGERPRINT_ENV: fingerprint,
            }
        )
        created = create_state_backup(
            project,
            anchor_backups,
            environ=environment,
            repository_root=project,
        )
        return project, fingerprint, created

    def add_runtime_provenance(self) -> None:
        import datetime as dt

        from runtime.tools.provenance import (
            AppendOnlyProvenanceStore,
            RuntimeProvenanceEventType,
            new_runtime_provenance_event,
        )
        from runtime.trace_context import TraceContext

        store = AppendOnlyProvenanceStore(self.state_root / "state")
        store.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.REQUEST_STARTED,
                trace_context=TraceContext(
                    request_id="request_" + "1" * 32,
                    trace_id="trace_" + "2" * 32,
                    task_id="task_" + "3" * 32,
                ),
                ingress="RUNTIME",
                request_length=5,
                slash_command=False,
                clock=lambda: dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
            )
        )

    def test_valid_backup_is_deterministic_and_idempotent(self) -> None:
        self.add_config()
        self.add_runtime_provenance()

        first = self.create()
        second = self.create()

        self.assertEqual(BackupStatus.BACKUP_VALID, first.verification.status)
        self.assertEqual(1, first.verification.provenance_entry_count)
        self.assertEqual(first.backup_id, second.backup_id)
        self.assertTrue(second.reused_existing)
        self.assertEqual(
            BackupStatus.BACKUP_VALID,
            verify_state_backup(first.backup_path, project_dir=RUNTIME_PROJECT).status,
        )

    def test_manifest_and_file_tamper_are_corrupt(self) -> None:
        self.add_config()
        created = self.create()
        manifest_path = created.backup_path / "manifest.json"
        original = manifest_path.read_bytes()
        manifest = json.loads(original)
        manifest["source_commit"] = "0" * 40
        manifest_path.write_bytes(backup_module._canonical_json(manifest))
        self.assertEqual(
            BackupStatus.BACKUP_CORRUPT,
            verify_state_backup(created.backup_path, project_dir=RUNTIME_PROJECT).status,
        )
        manifest_path.write_bytes(original)
        payload = created.backup_path / "payload" / "runtime" / "state" / "model_config.json"
        payload.write_bytes(b"{}\n")
        self.assertEqual(
            BackupStatus.BACKUP_CORRUPT,
            verify_state_backup(created.backup_path, project_dir=RUNTIME_PROJECT).status,
        )

    def test_identity_tamper_is_corrupt_but_intact_foreign_backup_is_mismatch(self) -> None:
        created = self.create()
        foreign_project = self.root / "foreign-project"
        prompt = foreign_project / "prompts" / "system_prompt.txt"
        prompt.parent.mkdir(parents=True)
        prompt.write_text("foreign prompt\n", encoding="utf-8")
        self.assertEqual(
            BackupStatus.BACKUP_PROJECT_MISMATCH,
            verify_state_backup(
                created.backup_path,
                project_dir=foreign_project,
            ).status,
        )

        manifest_path = created.backup_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["project_identity"] = "0" * 64
        manifest_path.write_bytes(backup_module._canonical_json(manifest))

        self.assertEqual(
            BackupStatus.BACKUP_CORRUPT,
            verify_state_backup(
                created.backup_path,
                project_dir=RUNTIME_PROJECT,
            ).status,
        )

    def test_foreign_identity_never_masks_intrinsic_corruption_or_schema(self) -> None:
        self.add_config()
        foreign_project = self.root / "intrinsic-foreign-project"
        prompt = foreign_project / "prompts" / "system_prompt.txt"
        prompt.parent.mkdir(parents=True)
        prompt.write_text("intrinsic foreign prompt\n", encoding="utf-8")
        foreign_identity = backup_module._project_identity(foreign_project)

        corrupt_created = self.create()
        corrupt_manifest = json.loads(
            (corrupt_created.backup_path / "manifest.json").read_text(encoding="utf-8")
        )
        corrupt_manifest["project_identity"] = foreign_identity
        corrupt_manifest["resources"][0]["sha256"] = "0" * 64
        corrupt_path = self.rewrite_manifest_core(
            corrupt_created.backup_path,
            corrupt_manifest,
        )
        self.assertEqual(
            BackupStatus.BACKUP_CORRUPT,
            verify_state_backup(
                corrupt_path,
                project_dir=RUNTIME_PROJECT,
            ).status,
        )

        unsupported_created = self.create()
        unsupported_manifest = json.loads(
            (unsupported_created.backup_path / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        unsupported_manifest["project_identity"] = foreign_identity
        unsupported_manifest["nz_architecture_version"] = "NZ_UNSUPPORTED_TEST"
        unsupported_path = self.rewrite_manifest_core(
            unsupported_created.backup_path,
            unsupported_manifest,
        )
        self.assertEqual(
            BackupStatus.BACKUP_SCHEMA_UNSUPPORTED,
            verify_state_backup(
                unsupported_path,
                project_dir=RUNTIME_PROJECT,
            ).status,
        )

    def test_manifest_numeric_security_fields_require_exact_integer_types(self) -> None:
        for replacement in (False, 0.0):
            with self.subTest(field="resource_inventory.included_count", value=replacement):
                created = self.create()
                manifest = json.loads(
                    (created.backup_path / "manifest.json").read_text(encoding="utf-8")
                )
                zero_row = next(
                    row for row in manifest["resource_inventory"]
                    if row["included_count"] == 0
                )
                zero_row["included_count"] = replacement
                tampered = self.rewrite_manifest_core(created.backup_path, manifest)
                self.assertEqual(
                    BackupStatus.BACKUP_CORRUPT,
                    verify_state_backup(tampered, project_dir=RUNTIME_PROJECT).status,
                )

        for replacement in (False, 0.0):
            with self.subTest(field="provenance.entry_count", value=replacement):
                created = self.create()
                manifest = json.loads(
                    (created.backup_path / "manifest.json").read_text(encoding="utf-8")
                )
                manifest["provenance"]["entry_count"] = replacement
                tampered = self.rewrite_manifest_core(created.backup_path, manifest)
                self.assertEqual(
                    BackupStatus.BACKUP_CORRUPT,
                    verify_state_backup(tampered, project_dir=RUNTIME_PROJECT).status,
                )

    def test_missing_required_file_is_incomplete(self) -> None:
        self.add_runtime_provenance()
        created = self.create()
        ledger = (
            created.backup_path
            / "payload"
            / "runtime"
            / "state"
            / "provenance"
            / "runtime_provenance_log.jsonl"
        )
        ledger.unlink()

        result = verify_state_backup(created.backup_path, project_dir=RUNTIME_PROJECT)

        self.assertEqual(BackupStatus.BACKUP_INCOMPLETE, result.status)

    def test_path_traversal_and_symlink_escape_are_rejected(self) -> None:
        self.add_config()
        created = self.create()
        outside = self.root / "outside-canary"
        outside.write_text("untouched", encoding="utf-8")
        manifest_path = created.backup_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["resources"][0]["relative_path"] = "../outside-canary"
        manifest_path.write_bytes(backup_module._canonical_json(manifest))
        self.assertEqual(
            BackupStatus.BACKUP_CORRUPT,
            verify_state_backup(created.backup_path, project_dir=RUNTIME_PROJECT).status,
        )
        self.assertEqual("untouched", outside.read_text())

    def test_provenance_corruption_survives_outer_manifest_rehash(self) -> None:
        self.add_runtime_provenance()
        created = self.create()
        relative = "runtime/state/provenance/runtime_provenance_log.jsonl"
        ledger = created.backup_path / "payload" / Path(relative)
        ledger.write_bytes(ledger.read_bytes() + b"synthetic-invalid-ledger-row\n")
        tampered = self.rewrite_manifest_for_payload(created.backup_path, relative)

        result = verify_state_backup(tampered, project_dir=RUNTIME_PROJECT)

        self.assertEqual(BackupStatus.BACKUP_CORRUPT, result.status)

    def test_symlink_and_hardlink_payloads_are_corrupt(self) -> None:
        self.add_config()
        created = self.create()
        target = created.backup_path / "payload" / "runtime" / "state" / "model_config.json"
        original = target.read_bytes()
        target.unlink()
        outside = self.root / "outside.json"
        outside.write_bytes(original)
        target.symlink_to(outside)
        self.assertEqual(
            BackupStatus.BACKUP_CORRUPT,
            verify_state_backup(created.backup_path, project_dir=RUNTIME_PROJECT).status,
        )
        target.unlink()
        os.link(outside, target)
        self.assertEqual(
            BackupStatus.BACKUP_CORRUPT,
            verify_state_backup(created.backup_path, project_dir=RUNTIME_PROJECT).status,
        )

    def test_interrupted_and_no_replace_promotion_never_publish_false_valid(self) -> None:
        self.add_config()
        with patch.object(
            backup_module,
            "_promote_directory",
            side_effect=OSError("synthetic interrupted promotion"),
        ):
            with self.assertRaises(OSError):
                self.create()
        self.assertFalse(any(path.name.startswith("backup_") for path in self.backups.iterdir()))
        self.assertFalse(any(path.name.startswith(".aoia-backup-partial-") for path in self.backups.iterdir()))

        original_promote = backup_module._promote_directory

        def raced(staging: Path, destination: Path, root: Path) -> None:
            destination.mkdir(mode=0o700)
            (destination / "sentinel").write_text("preserve", encoding="utf-8")
            (destination / "sentinel").chmod(0o600)
            original_promote(staging, destination, root)

        with patch.object(backup_module, "_promote_directory", side_effect=raced):
            with self.assertRaises(StateBackupDestinationError):
                self.create()
        published = [path for path in self.backups.iterdir() if path.name.startswith("backup_")]
        self.assertEqual(1, len(published))
        self.assertEqual("preserve", (published[0] / "sentinel").read_text())

    def test_secret_bearing_memory_and_private_material_are_excluded(self) -> None:
        canary = "synthetic-private-secret-canary-p22"
        self.write_private(
            self.state_root / "state" / "agent_state.json",
            {
                "session_id": "session",
                "cwd": str(RUNTIME_PROJECT),
                "current_task": canary,
                "previous_commands": [],
                "recent_outputs": [],
                "open_tabs": [],
                "current_browser_page": "",
                "screenshots": [],
                "browser_active": False,
            },
        )
        self.write_private(
            self.state_root / "memory" / "hats" / "private.json",
            {
                "name": "private",
                "role": "test",
                "instructions": canary,
                "project_path": "",
                "persistent": True,
            },
        )
        self.write_private_bytes(self.state_root / "state" / "private-signing-key.pem", canary.encode())

        created = self.create()
        combined = b"".join(
            path.read_bytes()
            for path in created.backup_path.rglob("*")
            if path.is_file()
        )
        manifest = json.loads((created.backup_path / "manifest.json").read_text())

        self.assertNotIn(canary.encode(), combined)
        classifications = {
            row["resource"]: row["classification"]
            for row in manifest["resource_inventory"]
        }
        self.assertEqual(ResourceClassification.EXCLUDED_SECRET.value, classifications["agent_memory"])
        self.assertEqual(ResourceClassification.EXCLUDED_SECRET.value, classifications["memory_hats"])
        self.assertEqual(ResourceClassification.EXCLUDED_SECRET.value, classifications["private_signing_material"])

    def test_restore_to_live_and_cross_project_are_rejected_without_writes(self) -> None:
        self.add_config()
        created = self.create()
        live_result = restore_state_backup(
            created.backup_path,
            self.home,
            project_dir=RUNTIME_PROJECT,
            environ=self.environment,
            repository_root=REPOSITORY_ROOT,
        )
        self.assertEqual(RestoreStatus.RESTORE_REJECTED, live_result.status)

        other = self.root / "other-project"
        prompt = other / "prompts" / "system_prompt.txt"
        prompt.parent.mkdir(parents=True)
        prompt.write_text("synthetic prompt\n")
        destination = self.root / "cross-project-restore"
        cross = restore_state_backup(
            created.backup_path,
            destination,
            project_dir=other,
            environ=self.environment,
        )
        self.assertEqual(BackupStatus.BACKUP_PROJECT_MISMATCH, cross.backup_status)
        self.assertFalse(destination.exists())

    def test_valid_isolated_restore_runs_preflight_and_exact_set(self) -> None:
        self.add_config()
        self.add_runtime_provenance()
        created = self.create()
        destination = self.root / "isolated-restore"

        restored = restore_state_backup(
            created.backup_path,
            destination,
            project_dir=RUNTIME_PROJECT,
            environ=self.environment,
            repository_root=REPOSITORY_ROOT,
        )

        self.assertEqual(RestoreStatus.RESTORE_VALIDATED, restored.status)
        self.assertTrue(restored.success)
        self.assertEqual("READY_DEGRADED", restored.startup_status)

    def test_restore_detects_bundle_mutation_between_verify_and_copy(self) -> None:
        self.add_config()
        created = self.create()
        original_copy = backup_module._copy_bundle_to_restore

        def mutate_after_copy(*args, **kwargs):
            result = original_copy(*args, **kwargs)
            manifest_path = created.backup_path / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["source_commit"] = "0" * 40
            manifest_path.write_bytes(backup_module._canonical_json(manifest))
            return result

        with patch.object(backup_module, "_copy_bundle_to_restore", side_effect=mutate_after_copy):
            restored = restore_state_backup(
                created.backup_path,
                self.root / "mutated-restore",
                project_dir=RUNTIME_PROJECT,
                environ=self.environment,
                repository_root=REPOSITORY_ROOT,
            )
        self.assertEqual(RestoreStatus.RESTORE_REJECTED, restored.status)
        self.assertFalse(restored.success)

    def test_extra_restored_file_prevents_success(self) -> None:
        self.add_config()
        created = self.create()
        original_preflight = backup_module._restore_preflight

        def inject_extra(home, *args, **kwargs):
            report = original_preflight(home, *args, **kwargs)
            if not home.name.startswith(".aoia-restore-partial-"):
                extra = home / "unexpected"
                extra.write_text("unexpected", encoding="utf-8")
                extra.chmod(0o600)
            return report

        with patch.object(backup_module, "_restore_preflight", side_effect=inject_extra):
            restored = restore_state_backup(
                created.backup_path,
                self.root / "extra-restore",
                project_dir=RUNTIME_PROJECT,
                environ=self.environment,
                repository_root=REPOSITORY_ROOT,
            )
        self.assertEqual(RestoreStatus.RESTORE_REJECTED, restored.status)

    def test_forbidden_backup_root_has_no_precreation_side_effect(self) -> None:
        synthetic_project = self.root / "synthetic-project"
        prompt = synthetic_project / "prompts" / "system_prompt.txt"
        prompt.parent.mkdir(parents=True)
        prompt.write_text("synthetic prompt\n")
        synthetic_home = self.root / "synthetic-home"
        synthetic_home.mkdir(mode=0o700)
        forbidden = synthetic_project / "must-not-exist"

        with self.assertRaises(StateBackupDestinationError):
            create_state_backup(
                synthetic_project,
                forbidden,
                environ={"AOIA_HOME": str(synthetic_home)},
                repository_root=synthetic_project,
            )

        self.assertFalse(forbidden.exists())

    def test_manual_review_result_is_not_success(self) -> None:
        result = RestoreResult(
            RestoreStatus.RESTORE_MANUAL_REVIEW_REQUIRED,
            "backup_" + "a" * 64,
            BackupStatus.BACKUP_VALID,
            startup_status="MANUAL_REVIEW_REQUIRED",
        )
        self.assertFalse(result.success)

    def test_anchor_backup_requires_independent_external_pin(self) -> None:
        project, fingerprint, created = self.create_anchored_backup()

        missing = verify_state_backup(created.backup_path, project_dir=project)
        wrong = verify_state_backup(
            created.backup_path,
            project_dir=project,
            expected_root_fingerprint="f" * 64,
        )
        valid = verify_state_backup(
            created.backup_path,
            project_dir=project,
            expected_root_fingerprint=fingerprint,
        )

        self.assertEqual(BackupStatus.BACKUP_CORRUPT, missing.status)
        self.assertEqual(BackupStatus.BACKUP_CORRUPT, wrong.status)
        self.assertEqual(BackupStatus.BACKUP_VALID, valid.status)
        for relative in backup_module._REQUIRED_TRUST_DIRECTORIES:
            self.assertTrue((created.backup_path / "payload" / relative).is_dir())

    def test_anchor_tamper_survives_outer_manifest_rehash(self) -> None:
        project, fingerprint, created = self.create_anchored_backup()
        archive = next(
            (created.backup_path / "payload" / "trust" / "anchor" / "anchors").iterdir()
        )
        anchor = json.loads(archive.read_text(encoding="utf-8"))
        signature = anchor["signature_b64"]
        anchor["signature_b64"] = ("A" if signature[0] != "A" else "B") + signature[1:]
        archive.write_bytes(backup_module._canonical_json(anchor))
        relative = archive.relative_to(created.backup_path / "payload").as_posix()
        tampered = self.rewrite_manifest_for_payload(created.backup_path, relative)

        result = verify_state_backup(
            tampered,
            project_dir=project,
            expected_root_fingerprint=fingerprint,
        )

        self.assertEqual(BackupStatus.BACKUP_CORRUPT, result.status)

    def test_full_local_dr_drill_includes_provenance(self) -> None:
        drill_root = self.root / "drill"
        drill_root.mkdir(mode=0o700)

        result = run_local_disaster_recovery_drill(
            RUNTIME_PROJECT,
            drill_root,
            repository_root=REPOSITORY_ROOT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(1, result.provenance_entry_count)
        self.assertEqual(BackupStatus.BACKUP_VALID, result.backup_status)
        self.assertEqual(RestoreStatus.RESTORE_VALIDATED, result.restore_status)
        self.assertEqual([], list(drill_root.iterdir()))


if __name__ == "__main__":
    unittest.main()
