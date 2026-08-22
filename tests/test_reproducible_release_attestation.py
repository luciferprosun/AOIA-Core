from __future__ import annotations

import copy
import datetime as dt
import hashlib
import inspect
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import runtime.release_attestation as release_module
from runtime.release_attestation import (
    DependencyClassification,
    RELEASE_MANIFEST_SCHEMA_VERSION,
    ReleaseBuildResult,
    ReleaseFileClassification,
    ReleaseSigningError,
    ReleaseSourceError,
    ReleaseStatus,
    ReleaseVerificationResult,
    TestEvidence,
    TestEvidenceDisposition,
    build_release_manifest,
    decode_release_manifest,
    encode_release_manifest,
    sign_release_manifest,
    verify_release_manifest,
)
from runtime.state_backup import BACKUP_SCHEMA_VERSION
from runtime.startup_preflight import STARTUP_PREFLIGHT_SCHEMA_VERSION
from runtime.task_checkpoints import TASK_CHECKPOINT_SCHEMA_VERSION
from runtime.tools.idempotency import IDEMPOTENCY_SCHEMA_VERSION
from runtime.tools.provenance import RUNTIME_PROVENANCE_SCHEMA_VERSION
from runtime.tools.provenance_anchor import (
    ANCHOR_SCHEMA_VERSION,
    provision_external_signing_key,
    register_initial_verification_key,
)


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class ReproducibleReleaseAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="aoia-p23-release-")
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.repository = self.root / "repository"
        self.repository.mkdir(mode=0o700)
        self._write(
            "pyproject.toml",
            """[project]
name = "synthetic-aoia"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = ["declared>=1", "pinned==2.0"]

[build-system]
requires = []
build-backend = "synthetic"
""",
        )
        self._write(
            "runtime/requirements.txt",
            "# Canonical dependencies are in pyproject.toml.\n",
        )
        self._write("runtime/main.py", "VALUE = 'release-source'\n")
        self._write("tests/test_runtime.py", "def test_runtime():\n    assert True\n")
        self._write("data/visible_unix_prototype_1a/demo.json", "{\"safe\":true}\n")
        self._write("knowledge/hats/example/manifest.json", "{\"hat\":\"safe\"}\n")
        self._write("apps/demo/state/session.py", "STATE_PACKAGE = True\n")
        self._write("docs/architecture/NZ_OPERATIONAL_HARDENING_V1.md", "# P1\n")
        self._write("README.md", "# Synthetic AOIA\n")
        self._write("LICENSE", "Synthetic test fixture only.\n")
        self._write("run_aoia_demo.sh", "#!/bin/sh\nexit 0\n", mode=0o755)
        self._write("run_final_recording_demo.sh", "#!/bin/sh\nexit 0\n", mode=0o755)
        self.git("init", "-q")
        self.git("add", "--all")
        self.git(
            "-c",
            "user.name=AOIA Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "-q",
            "-m",
            "synthetic release source",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write(self, relative: str, text: str, *, mode: int = 0o600) -> Path:
        path = self.repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        path.chmod(mode)
        return path

    def git(self, *arguments: str) -> str:
        completed = subprocess.run(
            ("git", *arguments),
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": str(self.root / "git-home"),
                "LANG": "C",
                "LC_ALL": "C",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            },
        )
        return completed.stdout.strip()

    @contextmanager
    def observed_dependencies(self):
        distributions = (
            SimpleNamespace(metadata={"Name": "Pinned"}, version="2.0"),
            SimpleNamespace(metadata={"Name": "Host-Only"}, version="9.1"),
        )
        with patch.object(
            release_module.importlib.metadata,
            "distributions",
            return_value=distributions,
        ):
            yield

    def evidence(self, *, passing: bool = False) -> TestEvidence:
        if passing:
            counts = (8, 8, 0, 0, 0)
        else:
            counts = (8, 5, 1, 1, 1)
        return TestEvidence(
            command_id="SYNTHETIC_FULL_UNITTEST",
            source_commit=self.git("rev-parse", "HEAD"),
            git_tree_identity=self.git("rev-parse", "HEAD^{tree}"),
            run_count=counts[0],
            pass_count=counts[1],
            failure_count=counts[2],
            error_count=counts[3],
            skip_count=counts[4],
            failure_names_sha256=_digest(b"known failure names\n"),
            error_names_sha256=_digest(b"known error names\n"),
            skip_names_sha256=_digest(b"known skip names\n"),
            output_log_sha256=_digest(b"synthetic local test output\n"),
        )

    def build(self, *, clock=None, passing: bool = False):
        with self.observed_dependencies():
            return build_release_manifest(
                self.repository,
                test_evidence=self.evidence(passing=passing),
                clock=clock,
            )

    def verify(self, manifest, **kwargs):
        with self.observed_dependencies():
            return verify_release_manifest(manifest, self.repository, **kwargs)

    def trust_fixture(self, name: str = "root") -> tuple[Path, Path, str]:
        key_directory = self.root / f"{name}-private"
        registry = self.root / f"{name}-registry"
        key_directory.mkdir(mode=0o700)
        registry.mkdir(mode=0o700)
        key_path = key_directory / "release.pem"
        fingerprint = provision_external_signing_key(
            key_path,
            repository_root=self.repository,
            project_dir=self.repository,
            public_key_registry=registry,
        )
        registered = register_initial_verification_key(
            registry,
            private_key_path=key_path,
            repository_root=self.repository,
            project_dir=self.repository,
        )
        self.assertEqual(fingerprint, registered)
        return key_path, registry, fingerprint

    def signed(self):
        unsigned = self.build()
        key, registry, fingerprint = self.trust_fixture()
        with self.observed_dependencies():
            signed = sign_release_manifest(
                unsigned.manifest,
                self.repository,
                private_key_path=key,
                public_key_registry=registry,
                expected_root_fingerprint=fingerprint,
            )
        return signed, registry, fingerprint

    def test_deterministic_core_is_timestamp_independent(self) -> None:
        first = self.build(clock=lambda: dt.datetime(2026, 1, 1, tzinfo=dt.UTC))
        second = self.build(clock=lambda: dt.datetime(2027, 2, 2, tzinfo=dt.UTC))
        self.assertEqual(first.core_hash, second.core_hash)
        self.assertEqual(first.release_id, second.release_id)
        self.assertEqual(first.manifest["core"], second.manifest["core"])
        self.assertNotEqual(
            first.manifest["metadata"]["created_at"],
            second.manifest["metadata"]["created_at"],
        )

    def test_manifest_records_exact_scope_dependencies_schemas_and_evidence(self) -> None:
        result = self.build()
        core = result.manifest["core"]
        paths = {row["path"] for row in core["critical_files"]}
        self.assertTrue(
            {
                "runtime/main.py",
                "tests/test_runtime.py",
                "data/visible_unix_prototype_1a/demo.json",
                "knowledge/hats/example/manifest.json",
                "apps/demo/state/session.py",
                "run_aoia_demo.sh",
            }.issubset(paths)
        )
        classifications = {
            row["classification"] for row in core["dependency_inventory"]
        }
        self.assertEqual(
            {
                DependencyClassification.DECLARED_DEPENDENCY.value,
                DependencyClassification.PINNED_DEPENDENCY.value,
                DependencyClassification.OBSERVED_INSTALLED_DEPENDENCY.value,
            },
            classifications,
        )
        self.assertEqual(
            {
                "configuration": STARTUP_PREFLIGHT_SCHEMA_VERSION,
                "checkpoint": TASK_CHECKPOINT_SCHEMA_VERSION,
                "idempotency": IDEMPOTENCY_SCHEMA_VERSION,
                "provenance": RUNTIME_PROVENANCE_SCHEMA_VERSION,
                "anchor": ANCHOR_SCHEMA_VERSION,
                "backup": BACKUP_SCHEMA_VERSION,
                "release": RELEASE_MANIFEST_SCHEMA_VERSION,
            },
            core["schemas"],
        )
        self.assertEqual(
            TestEvidenceDisposition.VERIFIED_WITH_KNOWN_BASELINE_FAILURES.value,
            core["test_evidence"]["disposition"],
        )
        self.assertEqual(self.git("rev-parse", "HEAD"), core["test_evidence"]["source_commit"])
        signature = inspect.signature(build_release_manifest)
        self.assertNotIn("observed_installed", signature.parameters)

    def test_served_web_sources_are_hashed_and_untracked_source_is_rejected(self) -> None:
        index_body = "<!doctype html>\n"
        app_body = "console.log('synthetic');\n"
        self._write("web/index.html", index_body)
        self._write("web/app.js", app_body)
        self.git("add", "web/index.html", "web/app.js")
        self.git(
            "-c",
            "user.name=AOIA Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "-q",
            "-m",
            "served web sources",
        )
        result = self.build()
        rows = {
            row["path"]: row
            for row in result.manifest["core"]["critical_files"]
        }
        for path, body in (
            ("web/index.html", index_body),
            ("web/app.js", app_body),
        ):
            self.assertEqual(
                ReleaseFileClassification.APPLICATION_SOURCE.value,
                rows[path]["classification"],
            )
            self.assertEqual(len(body.encode()), rows[path]["size_bytes"])
            self.assertEqual(_digest(body.encode()), rows[path]["sha256"])

        untracked = self._write(
            "web/untracked-served.js",
            "console.log('untracked');\n",
        )
        with self.assertRaises(ReleaseSourceError):
            self.build()
        untracked.unlink()

        self._write("web/app.js", "console.log('modified');\n")
        self.assertEqual(
            ReleaseStatus.RELEASE_FILE_MISMATCH,
            self.verify(result.manifest).status,
        )
        self._write("web/app.js", app_body)
        (self.repository / "web" / "index.html").unlink()
        self.assertEqual(
            ReleaseStatus.RELEASE_FILE_MISMATCH,
            self.verify(result.manifest).status,
        )

    def test_served_web_policy_exclusions_fail_closed_tracked_and_untracked(self) -> None:
        for path in ("web/.env", "web/cache/hidden.js"):
            with self.subTest(path=path, state="untracked"):
                target = self._write(path, "synthetic served exclusion canary\n")
                with self.assertRaises(ReleaseSourceError):
                    self.build()
            self.git("add", path)
            self.git(
                "-c",
                "user.name=AOIA Synthetic",
                "-c",
                "user.email=synthetic@example.invalid",
                "commit",
                "-q",
                "-m",
                f"tracked served exclusion {path}",
            )
            with self.subTest(path=path, state="tracked"):
                with self.assertRaises(ReleaseSourceError):
                    self.build()
            target.unlink()
            self.git("add", "--all")
            self.git(
                "-c",
                "user.name=AOIA Synthetic",
                "-c",
                "user.email=synthetic@example.invalid",
                "commit",
                "-q",
                "-m",
                f"remove served exclusion {path}",
            )

    def test_unsigned_release_is_truthfully_unsigned(self) -> None:
        result = self.build(passing=True)
        verification = self.verify(result.manifest)
        self.assertEqual(ReleaseStatus.RELEASE_UNSIGNED, verification.status)
        self.assertTrue(verification.content_valid)
        self.assertFalse(verification.valid)
        self.assertFalse(verification.signed)
        self.assertEqual(
            TestEvidenceDisposition.VERIFIED_PASS.value,
            verification.test_disposition,
        )

    def test_source_modification_and_missing_file_are_detected(self) -> None:
        result = self.build()
        target = self.repository / "runtime" / "main.py"
        target.write_text("VALUE = 'changed-source'\n", encoding="utf-8")
        self.assertEqual(
            ReleaseStatus.RELEASE_FILE_MISMATCH,
            self.verify(result.manifest).status,
        )
        self.git("restore", "runtime/main.py")
        target.unlink()
        self.assertEqual(
            ReleaseStatus.RELEASE_FILE_MISMATCH,
            self.verify(result.manifest).status,
        )

    def test_new_committed_source_is_source_mismatch(self) -> None:
        result = self.build()
        self._write("runtime/new_committed.py", "NEW = True\n")
        self.git("add", "runtime/new_committed.py")
        self.git(
            "-c",
            "user.name=AOIA Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "-q",
            "-m",
            "new source",
        )
        self.assertEqual(
            ReleaseStatus.RELEASE_SOURCE_MISMATCH,
            self.verify(result.manifest).status,
        )

    def test_dependency_modification_has_specific_precedence(self) -> None:
        result = self.build()
        pyproject = self.repository / "pyproject.toml"
        pyproject.write_text(
            pyproject.read_text(encoding="utf-8").replace(
                '"pinned==2.0"', '"pinned==3.0"'
            ),
            encoding="utf-8",
        )
        self.assertEqual(
            ReleaseStatus.RELEASE_DEPENDENCY_MISMATCH,
            self.verify(result.manifest).status,
        )
        pyproject.unlink()
        self.assertEqual(
            ReleaseStatus.RELEASE_DEPENDENCY_MISMATCH,
            self.verify(result.manifest).status,
        )

    def test_dynamic_dependencies_fail_closed(self) -> None:
        pyproject = self.repository / "pyproject.toml"
        value = pyproject.read_text(encoding="utf-8").replace(
            'dependencies = ["declared>=1", "pinned==2.0"]',
            'dynamic = ["dependencies"]',
        )
        pyproject.write_text(value, encoding="utf-8")
        self.git("add", "pyproject.toml")
        self.git(
            "-c",
            "user.name=AOIA Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "-q",
            "-m",
            "dynamic dependencies",
        )
        with self.assertRaises(ReleaseSourceError):
            self.build()

    def test_cache_temp_and_secret_canaries_are_excluded(self) -> None:
        excluded = {
            "runtime/cache/cache.tmp": "cache\n",
            "runtime/operator-token.json": "synthetic-token-canary\n",
            "data/private-key.txt": "synthetic-private-key-canary\n",
            "apps/demo/credentials-prod.json": "synthetic-credential-canary\n",
            "knowledge/access-token.yaml": "synthetic-access-token-canary\n",
            "tests/.DS_Store": "synthetic desktop metadata canary\n",
            "tests/Thumbs.db": "synthetic thumbnail metadata canary\n",
            "tests/test_results/result.json": "synthetic test result canary\n",
            "apps/demo/key.pkcs12": "synthetic key canary\n",
            "runtime/operator.token": "synthetic token canary\n",
            "runtime/operator.secret": "synthetic secret canary\n",
            "runtime/operator.credentials": "synthetic credential canary\n",
        }
        for path, value in excluded.items():
            self._write(path, value)
        result = self.build()
        encoded = encode_release_manifest(result.manifest)
        for path, canary in excluded.items():
            self.assertNotIn(path.encode(), encoded)
            self.assertNotIn(canary.strip().encode(), encoded)

    def test_tracked_credentials_caches_and_test_outputs_are_excluded(self) -> None:
        excluded = {
            "runtime/.npmrc": "//registry.invalid/:_authToken=canary\n",
            "runtime/.pypirc": "password=canary\n",
            "runtime/.netrc": "password canary\n",
            "apps/demo/.docker/config.json": "{\"auths\":{\"canary\":{}}}\n",
            "apps/demo/secrets.yaml": "secret: canary\n",
            "apps/demo/auth.json": "{\"token\":\"canary\"}\n",
            "tests/.mypy_cache/state.json": "{\"cache\":true}\n",
            "tests/.ruff_cache/state.json": "{\"cache\":true}\n",
            "tests/.hypothesis/state.json": "{\"cache\":true}\n",
            "tests/.coverage": "synthetic coverage output\n",
            "tests/.DS_Store": "synthetic desktop metadata canary\n",
            "tests/Thumbs.db": "synthetic thumbnail metadata canary\n",
            "tests/htmlcov/index.html": "synthetic coverage output\n",
            "tests/coverage/report.json": "synthetic coverage output\n",
            "apps/demo/node_modules/package.json": "{\"generated\":true}\n",
            "apps/demo/site-packages/local.py": "generated dependency output\n",
            "apps/demo/build/generated.js": "generated output\n",
            "apps/demo/dist/generated.js": "generated output\n",
            "tests/test_results/result.json": "synthetic test result canary\n",
            "apps/demo/key.pkcs12": "synthetic key canary\n",
            "runtime/operator.token": "synthetic token canary\n",
            "runtime/operator.secret": "synthetic secret canary\n",
            "runtime/operator.credentials": "synthetic credential canary\n",
        }
        for path, value in excluded.items():
            self._write(path, value)
        self.git("add", "--all")
        self.git(
            "-c",
            "user.name=AOIA Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "-q",
            "-m",
            "tracked excluded artifacts",
        )
        result = self.build()
        encoded = encode_release_manifest(result.manifest)
        paths = {row["path"] for row in result.manifest["core"]["critical_files"]}
        for path, canary in excluded.items():
            self.assertNotIn(path, paths)
            self.assertNotIn(path.encode(), encoded)
            self.assertNotIn(canary.strip().encode(), encoded)

    def test_exclusion_policy_covers_local_credentials_caches_and_outputs(self) -> None:
        excluded_paths = (
            "runtime/.git-credentials",
            "runtime/.htpasswd",
            "runtime/.pgpass",
            "runtime/.my.cnf",
            "apps/demo/.aws/credentials",
            "apps/demo/application_default_credentials.json",
            "apps/demo/kubeconfig",
            "apps/demo/id_ecdsa_sk",
            "apps/demo/server.key",
            "apps/demo/private.pkcs8",
            "apps/demo/private.pkcs12",
            "runtime/operator.token",
            "runtime/operator.secret",
            "runtime/operator.credentials",
            "apps/demo/.cache/value.json",
            "apps/demo/.gradle/state.json",
            "apps/demo/.parcel-cache/state.json",
            "apps/demo/.next/output.json",
            "apps/demo/.nuxt/output.json",
            "apps/demo/.svelte-kit/output.json",
            "apps/demo/.vite/output.json",
            "apps/demo/.turbo/output.json",
            "apps/demo/test-results/result.json",
            "apps/demo/test_results/result.json",
            "apps/demo/out/generated.js",
            "apps/demo/target/generated.bin",
            "apps/demo/wheelhouse/package.whl",
            "apps/demo/package.egg-info/PKG-INFO",
            "tests/coverage.xml",
            "tests/junit.xml",
            "tests/.testmondata",
            "tests/.eslintcache",
            "tests/.idea/workspace.xml",
            "tests/.vscode/settings.json",
            "tests/.history/source.py",
            "tests/result.bak",
            "tests/result.orig",
            "tests/result.rej",
            "tests/profile.prof",
        )
        for path in excluded_paths:
            with self.subTest(path=path):
                with self.assertRaises(release_module._ReleasePathExcluded):
                    release_module._safe_relative_path(path)
        for source_path in (
            "apps/demo/state/auth.py",
            "runtime/security/secret_redaction.py",
            "tests/test_auth_boundary.py",
        ):
            with self.subTest(source_path=source_path):
                self.assertEqual(
                    source_path,
                    release_module._safe_relative_path(source_path),
                )

    def test_ignored_untracked_source_cannot_hide_from_capture(self) -> None:
        info_exclude = self.repository / ".git" / "info" / "exclude"
        info_exclude.write_text("runtime/ignored_source.py\n", encoding="utf-8")
        self._write("runtime/ignored_source.py", "HIDDEN = True\n")
        with self.assertRaises(ReleaseSourceError):
            self.build()

    def test_malformed_scoped_filename_is_rejected_untracked_and_committed(self) -> None:
        self._write("runtime/malformed\\name.py", "MALFORMED = True\n")
        with self.assertRaises(ReleaseSourceError):
            self.build()
        self.git("add", "--all")
        self.git(
            "-c",
            "user.name=AOIA Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "-q",
            "-m",
            "malformed filename",
        )
        with self.assertRaises(ReleaseSourceError):
            self.build()

    def test_assume_unchanged_and_hardlink_sources_are_rejected(self) -> None:
        target = self.repository / "runtime" / "main.py"
        self.git("update-index", "--assume-unchanged", "runtime/main.py")
        original = target.read_text(encoding="utf-8")
        target.write_text(original.replace("release", "tainted"), encoding="utf-8")
        with self.assertRaises(ReleaseSourceError):
            self.build()
        self.git("update-index", "--no-assume-unchanged", "runtime/main.py")
        self.git("restore", "runtime/main.py")
        external = self.root / "hardlink-source.py"
        external.write_bytes(target.read_bytes())
        target.unlink()
        os.link(external, target)
        with self.assertRaises(ReleaseSourceError):
            self.build()

    def test_tracked_symlink_source_is_rejected(self) -> None:
        symlink = self.repository / "runtime" / "linked.py"
        symlink.symlink_to("main.py")
        self.git("add", "runtime/linked.py")
        self.git(
            "-c",
            "user.name=AOIA Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "-q",
            "-m",
            "tracked symlink",
        )
        with self.assertRaises(ReleaseSourceError):
            self.build()

    def test_strict_canonical_bytes_roundtrip_and_malformed_rejection(self) -> None:
        result = self.build()
        payload = encode_release_manifest(result.manifest)
        self.assertEqual(result.manifest, decode_release_manifest(payload))
        self.assertEqual(ReleaseStatus.RELEASE_UNSIGNED, self.verify(payload).status)
        duplicate = b'{"schema_version":"x","schema_version":"y"}\n'
        self.assertEqual(
            ReleaseStatus.RELEASE_INCOMPLETE,
            self.verify(duplicate).status,
        )
        noncanonical = json.dumps(result.manifest).encode("utf-8") + b"\n"
        self.assertEqual(
            ReleaseStatus.RELEASE_INCOMPLETE,
            self.verify(noncanonical).status,
        )
        self.assertEqual(
            ReleaseStatus.RELEASE_INCOMPLETE,
            self.verify(b'{"value":NaN}\n').status,
        )

    def test_deep_cyclic_and_oversized_manifest_shapes_fail_bounded(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["cycle"] = cyclic
        self.assertEqual(
            ReleaseStatus.RELEASE_INCOMPLETE,
            self.verify(cyclic).status,
        )
        deep: object = {}
        for _index in range(release_module.MAX_RELEASE_JSON_DEPTH + 2):
            deep = {"nested": deep}
        self.assertEqual(
            ReleaseStatus.RELEASE_INCOMPLETE,
            self.verify(deep).status,
        )
        oversized = b"{" + b" " * release_module.MAX_RELEASE_MANIFEST_BYTES + b"}\n"
        self.assertEqual(
            ReleaseStatus.RELEASE_INCOMPLETE,
            self.verify(oversized).status,
        )

    def test_exact_numeric_types_and_test_evidence_coherence(self) -> None:
        with self.assertRaises(ValueError):
            TestEvidence(
                command_id="SYNTHETIC_FULL_UNITTEST",
                source_commit=self.git("rev-parse", "HEAD"),
                git_tree_identity=self.git("rev-parse", "HEAD^{tree}"),
                run_count=True,
                pass_count=1,
                failure_count=0,
                error_count=0,
                skip_count=0,
                failure_names_sha256="0" * 64,
                error_names_sha256="0" * 64,
                skip_names_sha256="0" * 64,
                output_log_sha256="0" * 64,
            )
        with self.assertRaises(ValueError):
            TestEvidence(
                command_id="SYNTHETIC_FULL_UNITTEST",
                source_commit=self.git("rev-parse", "HEAD"),
                git_tree_identity=self.git("rev-parse", "HEAD^{tree}"),
                run_count=1,
                pass_count=0,
                failure_count=0,
                error_count=0,
                skip_count=1,
                failure_names_sha256="0" * 64,
                error_names_sha256="0" * 64,
                skip_names_sha256="0" * 64,
                output_log_sha256="0" * 64,
            )
        result = self.build()
        tampered = copy.deepcopy(result.manifest)
        tampered["core"]["source"]["file_count"] = True
        digest = release_module._core_hash(tampered["core"])
        tampered["core_hash"] = digest
        tampered["release_id"] = f"release_{digest}"
        self.assertEqual(
            ReleaseStatus.RELEASE_INCOMPLETE,
            self.verify(tampered).status,
        )

    def test_valid_ephemeral_signature_and_private_key_exclusion(self) -> None:
        signed, registry, fingerprint = self.signed()
        verification = self.verify(
            signed.manifest,
            public_key_registry=registry,
            expected_root_fingerprint=fingerprint,
        )
        self.assertEqual(ReleaseStatus.RELEASE_VALID, verification.status)
        self.assertTrue(verification.valid)
        self.assertTrue(verification.signed)
        encoded = encode_release_manifest(signed.manifest)
        self.assertNotIn(b"PRIVATE KEY", encoded)
        self.assertNotIn(str(self.root).encode(), encoded)

    def test_wrong_trust_key_is_rejected(self) -> None:
        signed, _registry, _fingerprint = self.signed()
        _wrong_key, wrong_registry, wrong_fingerprint = self.trust_fixture("wrong")
        verification = self.verify(
            signed.manifest,
            public_key_registry=wrong_registry,
            expected_root_fingerprint=wrong_fingerprint,
        )
        self.assertEqual(ReleaseStatus.RELEASE_UNKNOWN_KEY, verification.status)
        self.assertFalse(verification.valid)

    def test_modified_self_rehashed_signed_payload_is_signature_invalid(self) -> None:
        signed, registry, fingerprint = self.signed()
        tampered = copy.deepcopy(signed.manifest)
        tampered["core"]["test_evidence"]["output_log_sha256"] = "1" * 64
        digest = release_module._core_hash(tampered["core"])
        tampered["core_hash"] = digest
        tampered["release_id"] = f"release_{digest}"
        verification = self.verify(
            tampered,
            public_key_registry=registry,
            expected_root_fingerprint=fingerprint,
        )
        self.assertEqual(
            ReleaseStatus.RELEASE_SIGNATURE_INVALID,
            verification.status,
        )

    def test_signed_release_without_independent_trust_is_unknown(self) -> None:
        signed, _registry, _fingerprint = self.signed()
        self.assertEqual(
            ReleaseStatus.RELEASE_UNKNOWN_KEY,
            self.verify(signed.manifest).status,
        )

    def test_result_objects_reject_false_success_and_signature_conflicts(self) -> None:
        result = self.build()
        with self.assertRaises(ValueError):
            ReleaseVerificationResult(
                status=ReleaseStatus.RELEASE_VALID,
                release_id=result.release_id,
                core_hash=result.core_hash,
                source_commit=self.git("rev-parse", "HEAD"),
                signed=False,
                test_disposition=TestEvidenceDisposition.VERIFIED_PASS.value,
                message_safe="Invalid synthetic result.",
            )
        with self.assertRaises(ValueError):
            ReleaseVerificationResult(
                status=ReleaseStatus.RELEASE_UNSIGNED,
                release_id=result.release_id,
                core_hash=result.core_hash,
                source_commit=self.git("rev-parse", "HEAD"),
                signed=True,
                test_disposition=TestEvidenceDisposition.VERIFIED_PASS.value,
                message_safe="Invalid synthetic result.",
            )
        with self.assertRaises(ValueError):
            ReleaseBuildResult(
                manifest=result.manifest,
                release_id=result.release_id,
                core_hash=result.core_hash,
                signed=True,
            )
        conflicting = copy.deepcopy(result.manifest)
        conflicting["release_id"] = f"release_{'0' * 64}"
        with self.assertRaises(ValueError):
            ReleaseBuildResult(
                manifest=conflicting,
                release_id=result.release_id,
                core_hash=result.core_hash,
                signed=False,
            )
        self_consistent_fields = copy.deepcopy(result.manifest)
        self_consistent_fields["core"] = {"tampered": True}
        self_consistent_fields["core_hash"] = "0" * 64
        self_consistent_fields["release_id"] = f"release_{'0' * 64}"
        with self.assertRaises(ValueError):
            ReleaseBuildResult(
                manifest=self_consistent_fields,
                release_id=f"release_{'0' * 64}",
                core_hash="0" * 64,
                signed=False,
            )

    def test_signing_requires_external_active_registered_key(self) -> None:
        unsigned = self.build()
        inside = self.repository / "runtime" / "release.pem"
        inside.write_text("not a key\n", encoding="utf-8")
        inside.chmod(0o600)
        registry = self.root / "empty-registry"
        registry.mkdir(mode=0o700)
        with self.assertRaises(ReleaseSigningError):
            with self.observed_dependencies():
                sign_release_manifest(
                    unsigned.manifest,
                    self.repository,
                    private_key_path=inside,
                    public_key_registry=registry,
                    expected_root_fingerprint="0" * 64,
                )


if __name__ == "__main__":
    unittest.main()
