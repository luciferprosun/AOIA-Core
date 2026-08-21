from __future__ import annotations

import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from runtime.safety.atomic_persistence import AtomicWriteError
from runtime.tools.provenance import (
    AppendOnlyProvenanceStore,
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
    verify_provenance_chain,
)
from runtime.tools.provenance_anchor import (
    AnchorStatus,
    ProvenanceAnchorConfigurationError,
    ProvenanceAnchorCryptoUnavailable,
    create_provenance_anchor,
    provision_external_signing_key,
    register_initial_verification_key,
    rotate_verification_key,
    verify_latest_provenance_anchor,
    verify_provenance_anchor,
)
from runtime.trace_context import TraceContext


def _canonical_write(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


class TrustedProvenanceAnchorTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = "/dev/shm" if Path("/dev/shm").is_dir() else None
        self.temporary = tempfile.TemporaryDirectory(
            prefix="aoia-p13-anchor-", dir=temp_parent
        )
        self.root = Path(self.temporary.name)
        os.chmod(self.root, 0o700)
        self.project = self.root / "project"
        self.key_dir = self.root / "private-keys"
        self.registry = self.root / "public-registry"
        self.anchor_root = self.root / "anchors"
        self.state = self.root / "state"
        for path in (
            self.project,
            self.key_dir,
            self.registry,
            self.anchor_root,
            self.state,
        ):
            path.mkdir(mode=0o700)
        self.store = AppendOnlyProvenanceStore(self.state)
        self.ledger = self.store.runtime_log_path
        self.root_key = self.key_dir / "root.pem"
        self.root_fingerprint = provision_external_signing_key(
            self.root_key,
            repository_root=self.project,
            project_dir=self.project,
            ledger_path=self.ledger,
            anchor_root=self.anchor_root,
            public_key_registry=self.registry,
        )
        registered = register_initial_verification_key(
            self.registry,
            private_key_path=self.root_key,
            repository_root=self.project,
            project_dir=self.project,
        )
        self.assertEqual(self.root_fingerprint, registered)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def append_event(self, length: int = 1) -> None:
        self.store.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.REQUEST_STARTED,
                trace_context=TraceContext.new_request(),
                ingress="RUNTIME",
                request_length=length,
                slash_command=False,
            )
        )

    def create(self, *, key: Path | None = None):
        return create_provenance_anchor(
            self.ledger,
            self.anchor_root,
            self.registry,
            private_key_path=key or self.root_key,
            expected_root_fingerprint=self.root_fingerprint,
            repository_root=self.project,
            project_dir=self.project,
        )

    def verify(self, anchor_path: Path):
        return verify_provenance_anchor(
            self.ledger,
            anchor_path,
            self.registry,
            expected_root_fingerprint=self.root_fingerprint,
            project_dir=self.project,
        )

    def verify_latest(self):
        return verify_latest_provenance_anchor(
            self.ledger,
            self.anchor_root,
            self.registry,
            expected_root_fingerprint=self.root_fingerprint,
            project_dir=self.project,
        )

    def test_empty_and_nonempty_ledgers_create_valid_current_anchors(self) -> None:
        empty = self.create()
        self.assertEqual(0, empty.entry_count)
        self.assertEqual(AnchorStatus.ANCHOR_VALID, self.verify(empty.anchor_path).status)
        self.append_event()
        nonempty = self.create()
        result = self.verify_latest()
        self.assertEqual(AnchorStatus.ANCHOR_VALID, result.status)
        self.assertTrue(result.is_current)
        self.assertEqual(2, nonempty.anchor_sequence)

    def test_appended_ledger_keeps_old_anchor_valid_but_historical(self) -> None:
        self.append_event()
        old = self.create()
        self.append_event(2)
        result = self.verify(old.anchor_path)
        self.assertEqual(AnchorStatus.ANCHOR_VALID, result.status)
        self.assertFalse(result.is_current)

    def test_modified_and_truncated_ledgers_fail_with_mismatch(self) -> None:
        self.append_event()
        self.append_event(2)
        anchor = self.create()
        original = self.ledger.read_bytes()
        records = [json.loads(line) for line in original.decode().splitlines()]
        records[0]["request_length"] = 999
        self.ledger.write_text(
            "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records),
            encoding="utf-8",
        )
        self.assertEqual(AnchorStatus.ANCHOR_LEDGER_MISMATCH, self.verify(anchor.anchor_path).status)
        self.ledger.write_bytes(original.splitlines(keepends=True)[0])
        self.assertEqual(AnchorStatus.ANCHOR_LEDGER_MISMATCH, self.verify(anchor.anchor_path).status)

    def test_valid_base64_signature_tamper_is_signature_invalid(self) -> None:
        anchor = self.create()
        record = json.loads(anchor.anchor_path.read_text(encoding="utf-8"))
        signature = bytearray(base64.b64decode(record["signature_b64"], validate=True))
        signature[0] ^= 1
        record["signature_b64"] = base64.b64encode(signature).decode("ascii")
        _canonical_write(anchor.anchor_path, record)
        self.assertEqual(
            AnchorStatus.ANCHOR_SIGNATURE_INVALID,
            self.verify(anchor.anchor_path).status,
        )
        self.assertEqual(
            AnchorStatus.ANCHOR_SIGNATURE_INVALID,
            self.verify_latest().status,
        )

    def test_unsupported_and_duplicate_anchor_schema_fail_closed(self) -> None:
        anchor = self.create()
        record = json.loads(anchor.anchor_path.read_text(encoding="utf-8"))
        record["schema_version"] = "AOIA_PROVENANCE_ANCHOR_2"
        _canonical_write(anchor.anchor_path, record)
        self.assertEqual(
            AnchorStatus.ANCHOR_SCHEMA_UNSUPPORTED,
            self.verify(anchor.anchor_path).status,
        )
        duplicate = json.dumps(record, sort_keys=True)[:-1] + ',"anchor_id":"x"}\n'
        anchor.anchor_path.write_text(duplicate, encoding="utf-8")
        self.assertEqual(
            AnchorStatus.ANCHOR_SCHEMA_UNSUPPORTED,
            self.verify(anchor.anchor_path).status,
        )

    def test_wrong_external_root_pin_is_unknown_key(self) -> None:
        anchor = self.create()
        result = verify_provenance_anchor(
            self.ledger,
            anchor.anchor_path,
            self.registry,
            expected_root_fingerprint="f" * 64,
            project_dir=self.project,
        )
        self.assertEqual(AnchorStatus.ANCHOR_UNKNOWN_KEY, result.status)
        latest = verify_latest_provenance_anchor(
            self.ledger,
            self.anchor_root,
            self.registry,
            expected_root_fingerprint="f" * 64,
            project_dir=self.project,
        )
        self.assertEqual(AnchorStatus.ANCHOR_UNKNOWN_KEY, latest.status)

    def test_rotation_preserves_old_anchor_and_activates_new_key(self) -> None:
        self.append_event()
        old_anchor = self.create()
        new_key = self.key_dir / "second.pem"
        new_fingerprint = provision_external_signing_key(
            new_key,
            repository_root=self.project,
            project_dir=self.project,
            ledger_path=self.ledger,
            anchor_root=self.anchor_root,
            public_key_registry=self.registry,
        )
        rotated = rotate_verification_key(
            self.registry,
            current_private_key_path=self.root_key,
            new_private_key_path=new_key,
            repository_root=self.project,
            project_dir=self.project,
            expected_root_fingerprint=self.root_fingerprint,
        )
        self.assertEqual(new_fingerprint, rotated)
        self.append_event(2)
        new_anchor = self.create(key=new_key)
        old_result = self.verify(old_anchor.anchor_path)
        self.assertEqual(AnchorStatus.ANCHOR_VALID, old_result.status)
        self.assertFalse(old_result.is_current)
        self.assertEqual(AnchorStatus.ANCHOR_VALID, self.verify(new_anchor.anchor_path).status)

    def test_retired_key_cannot_authorize_a_new_latest_anchor(self) -> None:
        first = self.create()
        new_key = self.key_dir / "active.pem"
        provision_external_signing_key(
            new_key,
            repository_root=self.project,
            project_dir=self.project,
            ledger_path=self.ledger,
            anchor_root=self.anchor_root,
            public_key_registry=self.registry,
        )
        rotate_verification_key(
            self.registry,
            current_private_key_path=self.root_key,
            new_private_key_path=new_key,
            repository_root=self.project,
            project_dir=self.project,
            expected_root_fingerprint=self.root_fingerprint,
        )
        self.append_event()
        from runtime.tools import provenance_anchor as module

        root_private, _bytes, _fingerprint = module._load_private_key(
            self.root_key,
            repository_root=self.project,
            project_dir=self.project,
            ledger_path=self.ledger,
            anchor_root=self.anchor_root,
            public_key_registry=self.registry,
        )
        first_record = json.loads(first.anchor_path.read_text())
        ledger_result = verify_provenance_chain(self.ledger)
        anchor_id = f"anchor_{'b' * 32}"
        unsigned = {
            "schema_version": module.ANCHOR_SCHEMA_VERSION,
            "anchor_id": anchor_id,
            "anchor_sequence": 2,
            "previous_anchor_hash": module._anchor_hash(first_record),
            "timestamp_utc": module._timestamp(),
            "project_identity": module._project_identity(self.project),
            "ledger_identity": module._ledger_identity(
                self.ledger, module._project_identity(self.project)
            ),
            "latest_entry_hash": ledger_result.terminal_hash,
            "entry_count": ledger_result.entry_count,
            "provenance_schema_generation": module.RUNTIME_PROVENANCE_SCHEMA_VERSION,
            "signature_algorithm": module.SIGNATURE_ALGORITHM,
            "public_key_fingerprint": self.root_fingerprint,
        }
        forged = {
            **unsigned,
            "signature_b64": module._b64encode(
                root_private.sign(
                    module.SIGNATURE_DOMAIN + module._canonical_json(unsigned)
                )
            ),
        }
        forged_path = self.anchor_root / "anchors" / f"{anchor_id}.json"
        _canonical_write(forged_path, forged)
        _canonical_write(
            self.anchor_root / "latest_anchor.json",
            {
                "schema_version": module.LATEST_ANCHOR_SCHEMA_VERSION,
                "project_identity": unsigned["project_identity"],
                "ledger_identity": unsigned["ledger_identity"],
                "anchor_id": anchor_id,
                "anchor_sequence": 2,
                "anchor_hash": module._anchor_hash(forged),
                "anchor_filename": forged_path.name,
                "entry_count": ledger_result.entry_count,
                "latest_entry_hash": ledger_result.terminal_hash,
            },
        )
        historical = self.verify(forged_path)
        self.assertEqual(AnchorStatus.ANCHOR_VALID, historical.status)
        self.assertFalse(historical.is_current)
        self.assertEqual(AnchorStatus.ANCHOR_UNKNOWN_KEY, self.verify_latest().status)

    def test_rotation_pointer_failure_is_recoverable_and_old_anchor_stays_valid(self) -> None:
        old_anchor = self.create()
        new_key = self.key_dir / "pending.pem"
        new_fingerprint = provision_external_signing_key(
            new_key,
            repository_root=self.project,
            project_dir=self.project,
            ledger_path=self.ledger,
            anchor_root=self.anchor_root,
            public_key_registry=self.registry,
        )
        from runtime.tools import provenance_anchor as module

        original = module._write_pointer_record

        def fail_latest_key(path, *args, **kwargs):
            if Path(path).name == "latest_key.json":
                raise AtomicWriteError("injected", target_path=Path(path))
            return original(path, *args, **kwargs)

        with patch.object(module, "_write_pointer_record", side_effect=fail_latest_key):
            with self.assertRaises(AtomicWriteError):
                rotate_verification_key(
                    self.registry,
                    current_private_key_path=self.root_key,
                    new_private_key_path=new_key,
                    repository_root=self.project,
                    project_dir=self.project,
                    expected_root_fingerprint=self.root_fingerprint,
                )
        self.assertEqual(
            AnchorStatus.ANCHOR_VALID,
            self.verify(old_anchor.anchor_path).status,
        )
        recovered = rotate_verification_key(
            self.registry,
            current_private_key_path=self.root_key,
            new_private_key_path=new_key,
            repository_root=self.project,
            project_dir=self.project,
            expected_root_fingerprint=self.root_fingerprint,
        )
        self.assertEqual(new_fingerprint, recovered)

    def test_latest_pointer_rollback_is_not_accepted(self) -> None:
        first = self.create()
        self.create()
        pointer = json.loads((self.anchor_root / "latest_anchor.json").read_text())
        first_record = json.loads(first.anchor_path.read_text())
        from runtime.tools import provenance_anchor as module

        pointer.update(
            anchor_id=first.anchor_id,
            anchor_sequence=first.anchor_sequence,
            anchor_hash=module._anchor_hash(first_record),
            anchor_filename=first.anchor_path.name,
            entry_count=first.entry_count,
            latest_entry_hash=first.latest_entry_hash,
        )
        _canonical_write(self.anchor_root / "latest_anchor.json", pointer)
        self.assertEqual(
            AnchorStatus.ANCHOR_LEDGER_MISMATCH,
            self.verify_latest().status,
        )

    def test_self_consistent_replacement_plus_append_cannot_be_reanchored(self) -> None:
        self.append_event()
        self.create()
        other_state = self.root / "other-state"
        other = AppendOnlyProvenanceStore(other_state)
        for length in (10, 11):
            other.append_runtime_event(
                new_runtime_provenance_event(
                    RuntimeProvenanceEventType.REQUEST_STARTED,
                    trace_context=TraceContext.new_request(),
                    ingress="RUNTIME",
                    request_length=length,
                    slash_command=False,
                )
            )
        self.ledger.write_bytes(other.runtime_log_path.read_bytes())
        self.assertTrue(verify_provenance_chain(self.ledger).ok)
        with self.assertRaises(ProvenanceAnchorConfigurationError):
            self.create()

    def test_private_key_path_and_permissions_fail_closed(self) -> None:
        inside = self.project / "new" / "key.pem"
        with self.assertRaises(ProvenanceAnchorConfigurationError):
            provision_external_signing_key(
                inside,
                repository_root=self.project,
                project_dir=self.project,
            )
        self.assertFalse(inside.parent.exists())
        os.chmod(self.root_key, 0o640)
        with self.assertRaises(ProvenanceAnchorConfigurationError):
            self.create()

    def test_symlinked_parent_into_project_has_no_rejected_provision_side_effect(self) -> None:
        link = self.root / "external-link"
        link.symlink_to(self.project, target_is_directory=True)
        target = link / "must-not-exist" / "key.pem"
        with self.assertRaises(ProvenanceAnchorConfigurationError):
            provision_external_signing_key(
                target,
                repository_root=self.project,
                project_dir=self.project,
            )
        self.assertFalse((self.project / "must-not-exist").exists())

    def test_decoy_repository_root_cannot_authorize_project_key(self) -> None:
        decoy = self.root / "decoy"
        decoy.mkdir(mode=0o700)
        with self.assertRaises(ProvenanceAnchorConfigurationError):
            provision_external_signing_key(
                self.project / "inside.pem",
                repository_root=decoy,
                project_dir=self.project,
            )

    def test_public_registry_substitution_is_not_self_authenticating(self) -> None:
        anchor = self.create()
        root = json.loads((self.registry / "trust_root.json").read_text())
        root["root_public_key_fingerprint"] = "e" * 64
        _canonical_write(self.registry / "trust_root.json", root)
        self.assertEqual(AnchorStatus.ANCHOR_UNKNOWN_KEY, self.verify(anchor.anchor_path).status)

    def test_symlink_and_hardlink_private_keys_are_rejected(self) -> None:
        symlink = self.key_dir / "link.pem"
        symlink.symlink_to(self.root_key)
        with self.assertRaises(ProvenanceAnchorConfigurationError):
            self.create(key=symlink)
        hardlink = self.key_dir / "hard.pem"
        os.link(self.root_key, hardlink)
        with self.assertRaises(ProvenanceAnchorConfigurationError):
            self.create()

    def test_verifier_does_not_create_missing_record_directories(self) -> None:
        missing_registry = self.root / "missing-registry"
        missing_anchor = (
            self.root / "missing-anchors" / f"anchor_{'0' * 32}.json"
        )
        result = verify_provenance_anchor(
            self.ledger,
            Path(str(missing_anchor)),
            missing_registry,
            expected_root_fingerprint=self.root_fingerprint,
            project_dir=self.project,
        )
        self.assertEqual(AnchorStatus.ANCHOR_SCHEMA_UNSUPPORTED, result.status)
        self.assertFalse(missing_registry.exists())

    def test_crypto_unavailable_is_explicit(self) -> None:
        anchor = self.create()
        with patch(
            "runtime.tools.provenance_anchor._crypto",
            side_effect=ProvenanceAnchorCryptoUnavailable("unavailable"),
        ):
            result = self.verify(anchor.anchor_path)
            latest = self.verify_latest()
        self.assertEqual(AnchorStatus.ANCHOR_CRYPTO_UNAVAILABLE, result.status)
        self.assertEqual(AnchorStatus.ANCHOR_CRYPTO_UNAVAILABLE, latest.status)

    def test_anchor_pointer_write_failure_preserves_old_archive_and_pointer(self) -> None:
        first = self.create()
        before = (self.anchor_root / "latest_anchor.json").read_bytes()
        self.append_event()
        from runtime.tools import provenance_anchor as module

        original = module._write_pointer_record

        def fail_latest(path, *args, **kwargs):
            if Path(path).name == "latest_anchor.json":
                raise AtomicWriteError("injected", target_path=Path(path))
            return original(path, *args, **kwargs)

        with patch.object(module, "_write_pointer_record", side_effect=fail_latest):
            with self.assertRaises(AtomicWriteError):
                self.create()
        self.assertEqual(before, (self.anchor_root / "latest_anchor.json").read_bytes())
        self.assertEqual(AnchorStatus.ANCHOR_VALID, self.verify(first.anchor_path).status)

    def test_archive_collision_never_overwrites_existing_anchor(self) -> None:
        fixed = SimpleNamespace(hex="a" * 32)
        from runtime.tools import provenance_anchor as module

        with patch.object(module.uuid, "uuid4", return_value=fixed):
            first = self.create()
            before = first.anchor_path.read_bytes()
            with self.assertRaises(ProvenanceAnchorConfigurationError):
                self.create()
        self.assertEqual(before, first.anchor_path.read_bytes())

    def test_archive_atomic_failure_leaves_previous_latest_unchanged(self) -> None:
        first = self.create()
        pointer_before = (self.anchor_root / "latest_anchor.json").read_bytes()
        self.append_event()
        from runtime.tools import provenance_anchor as module

        original = module._write_immutable_record

        def fail_archive(path, *args, **kwargs):
            if Path(path).parent.name == "anchors":
                raise AtomicWriteError("injected", target_path=Path(path))
            return original(path, *args, **kwargs)

        with patch.object(module, "_write_immutable_record", side_effect=fail_archive):
            with self.assertRaises(AtomicWriteError):
                self.create()
        self.assertEqual(
            pointer_before,
            (self.anchor_root / "latest_anchor.json").read_bytes(),
        )
        self.assertEqual(AnchorStatus.ANCHOR_VALID, self.verify(first.anchor_path).status)

    def test_anchor_root_path_swap_cannot_redirect_archive_or_lock(self) -> None:
        detached = self.root / "detached-anchors"
        outside = self.root / "outside"
        outside.mkdir(mode=0o700)
        (outside / "anchors").mkdir(mode=0o700)
        (outside / ".locks").mkdir(mode=0o700)
        from runtime.tools import provenance_anchor as module

        original = module._write_immutable_record
        swapped = False

        def swap_then_write(path, *args, **kwargs):
            nonlocal swapped
            if not swapped and Path(path).parent.name == "anchors":
                self.anchor_root.rename(detached)
                self.anchor_root.symlink_to(outside, target_is_directory=True)
                swapped = True
            return original(path, *args, **kwargs)

        try:
            with patch.object(
                module, "_write_immutable_record", side_effect=swap_then_write
            ):
                with self.assertRaises(Exception):
                    self.create()
            outside_files = [path for path in outside.rglob("*") if path.is_file()]
            self.assertEqual([], outside_files)
        finally:
            if self.anchor_root.is_symlink():
                self.anchor_root.unlink()
            if detached.exists():
                detached.rename(self.anchor_root)

    def test_registry_path_swap_cannot_redirect_rotation_or_lock(self) -> None:
        new_key = self.key_dir / "swap-new.pem"
        provision_external_signing_key(
            new_key,
            repository_root=self.project,
            project_dir=self.project,
            public_key_registry=self.registry,
        )
        detached = self.root / "detached-registry"
        outside = self.root / "outside-registry"
        outside.mkdir(mode=0o700)
        for name in ("keys", "rotations", ".locks"):
            (outside / name).mkdir(mode=0o700)
        from runtime.tools import provenance_anchor as module

        original = module._write_immutable_record
        swapped = False

        def swap_then_write(path, *args, **kwargs):
            nonlocal swapped
            if not swapped and Path(path).parent.name == "keys":
                self.registry.rename(detached)
                self.registry.symlink_to(outside, target_is_directory=True)
                swapped = True
            return original(path, *args, **kwargs)

        try:
            with patch.object(
                module, "_write_immutable_record", side_effect=swap_then_write
            ):
                with self.assertRaises(Exception):
                    rotate_verification_key(
                        self.registry,
                        current_private_key_path=self.root_key,
                        new_private_key_path=new_key,
                        repository_root=self.project,
                        project_dir=self.project,
                        expected_root_fingerprint=self.root_fingerprint,
                    )
            self.assertEqual(
                [], [path for path in outside.rglob("*") if path.is_file()]
            )
        finally:
            if self.registry.is_symlink():
                self.registry.unlink()
            if detached.exists():
                detached.rename(self.registry)

    def test_private_key_bytes_never_enter_public_records_or_ledger(self) -> None:
        self.append_event()
        self.create()
        private = self.root_key.read_bytes()
        for root in (self.registry, self.anchor_root, self.state):
            for path in root.rglob("*"):
                if path.is_file():
                    self.assertNotIn(private, path.read_bytes())


if __name__ == "__main__":
    unittest.main()
