"""Pinned adapter for the standalone German Federal Law Knowledge Hat 1A."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from runtime.knowledge_modules.contracts import (
    CONFIGURATION_SCHEMA_VERSION,
    DESCRIPTOR_SCHEMA_VERSION,
    VERIFICATION_SCHEMA_VERSION,
    KnowledgeModuleConfiguration,
    KnowledgeModuleDescriptor,
    KnowledgeModuleError,
    KnowledgeModuleFailure,
    KnowledgeModuleVerificationResult,
    canonical_json_bytes,
    exact_fields,
    reject_enabled_authority,
)
from runtime.knowledge_modules.evidence import (
    KnowledgeCoverageWarning,
    KnowledgeEvidenceBundle,
    KnowledgeEvidenceItem,
    evidence_bundle_from_fields,
    evidence_item_from_fields,
)
from runtime.knowledge_modules.external_gateway import GermanLawExternalGateway
from runtime.knowledge_modules.registry import (
    KnowledgeModuleRegistration,
    KnowledgeModuleRegistry,
)
from runtime.knowledge_modules.selection import (
    DOCUMENT_TYPES,
    SOURCE_CLASSES,
    KnowledgeModuleQuery,
)


GERMAN_LAW_MODULE_ID = "de-law-federal-1a"
GERMAN_LAW_MODULE_VERSION = "1a"
GERMAN_LAW_DISPLAY_NAME = "German Federal Law"
GERMAN_LAW_EXPECTED_HEAD = "73f444cdad78fa5d66f76216c19dc41f4c0e3b03"
GERMAN_LAW_FACTORY_SNAPSHOT = "federal-factory-1a-9d801825276967f0c960c876feb51297"
GERMAN_LAW_SOURCE_SNAPSHOTS = (
    "snapshot-491d6b80bbfe6f5fa7189c98f7552111",
    "snapshot-8dac9a7b0a3b7654cbc8be71b1358f6a",
    "snapshot-e80c174b544320ddf703e4f2d9256e62",
)
GERMAN_LAW_TEMPORAL_SNAPSHOT = "federal-temporal-1a-fe9ce34784e92af97651fe0378672d4c"
EU_PILOT_SNAPSHOT = "eu-cellar-pilot-1e-4b13d5fed487005392e9109486c2d4b6"
EU_PILOT_MANIFEST_HASH = "ee3ef27b0375f767ff34c70cf54ac2b102e85e541dd0545680e457f16ba2c412"
APPROVED_RESOLVED_CORPUS_PATH = (
    "/media/l/LSC_DATA/01_ACTIVE_WORK/AI_WORKSPACE/datasets/german-law-corpus"
)

EXPECTED_MANIFEST_HASHES = (
    (
        "manifests/coverage.json",
        "81d8c349db031e56d85154bb70d218e77a5a9b783f2ea0335dc90ea135b94999",
    ),
    (
        "manifests/federal-temporal-graph-1a.json",
        "d61c983d9316bcc0e2c214dfbe977fc820fe11d62d7099e9361585a2eda6e5b8",
    ),
    (
        "snapshots/eu/eu-cellar-pilot-1e-4b13d5fed487005392e9109486c2d4b6/snapshot.json",
        "449129d8d759a4b8f60f3abf442f23ae8ecf6d7076858ccac8db5d3fbb0c861f",
    ),
    (
        "snapshots/snapshot-491d6b80bbfe6f5fa7189c98f7552111/snapshot.json",
        "7b39668bdba55e5224f52e789aa1c819754b427a5369ff6c8b8ababab5c4e72e",
    ),
    (
        "snapshots/snapshot-8dac9a7b0a3b7654cbc8be71b1358f6a/snapshot.json",
        "ba7a1759049574dd25c7312e07505edb54d17c67dc69f6275dec9f6ebf60f468",
    ),
    (
        "snapshots/snapshot-e80c174b544320ddf703e4f2d9256e62/snapshot.json",
        "6cb5fb039bc82a09ce4372b87d54273f1e8e6b31150ae06ebef464f76236c73a",
    ),
)

_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_SHA64 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_REF = re.compile(r"refs/heads/[A-Za-z0-9._/-]+\Z")

_EXTERNAL_DESCRIPTOR_FIELDS = {
    "authority_status",
    "can_approve",
    "can_call_provider",
    "can_execute",
    "can_provide_binding_legal_advice",
    "can_write",
    "corpus_snapshot_ids",
    "coverage_status",
    "currentness_status",
    "display_name",
    "domain",
    "enabled_by_default",
    "jurisdictions",
    "known_limitations",
    "languages",
    "licence_status",
    "module_id",
    "module_version",
    "retrieval_modes",
    "source_classes",
    "subdomains",
    "supported_filters",
    "temporal_snapshot_id",
}
_EXTERNAL_VERIFY_FIELDS = {
    "authority_status",
    "can_approve",
    "can_call_provider",
    "can_execute",
    "can_provide_binding_legal_advice",
    "can_write",
    "corpus_snapshot_ids",
    "counts",
    "data_root",
    "errors",
    "filesystem_read_only",
    "immutable_sqlite",
    "manifest_hash",
    "manifests_unchanged",
    "module_id",
    "module_version",
    "mutation_attempt_blocked",
    "network_calls",
    "provider_calls",
    "quick_checks",
    "sampled_source_objects",
    "sampled_source_objects_verified",
    "selected_manifest_hashes",
    "sql_injection_inert",
    "sqlite_mode",
    "temporal_snapshot_id",
    "valid",
    "verification_hash",
}
_EXTERNAL_VERIFY_COUNT_FIELDS = {
    "amendment_relationships",
    "document_validity",
    "documents",
    "provision_validity",
    "provisions",
    "resolved_documents_at_evaluation_date",
    "resolved_provisions_at_evaluation_date",
    "temporal_events",
    "temporal_records",
    "unresolved",
}
_EXTERNAL_BUNDLE_FIELDS = {
    "authority_status",
    "bundle_id",
    "can_approve",
    "can_call_provider",
    "can_execute",
    "can_provide_binding_legal_advice",
    "can_write",
    "corpus_snapshot_id",
    "coverage_warnings",
    "evidence_items",
    "module_id",
    "module_version",
    "query_as_of_date",
    "query_hash",
    "retrieval_failures",
    "retrieval_mode",
    "temporal_snapshot_id",
    "total_context_characters",
    "truncated",
}
_EXTERNAL_ITEM_FIELDS = {
    "authority_status",
    "can_approve",
    "can_call_provider",
    "can_execute",
    "can_provide_binding_legal_advice",
    "can_write",
    "corpus_snapshot_id",
    "document_id",
    "document_type",
    "effective_from",
    "effective_until",
    "excerpt",
    "excerpt_incomplete",
    "heading",
    "jurisdiction",
    "licence_status",
    "module_id",
    "module_version",
    "official_abbreviation",
    "official_title",
    "provision_id",
    "provision_number",
    "publication_date",
    "publication_reference",
    "retrieval_mode",
    "retrieval_score",
    "source_class",
    "source_object_sha256",
    "source_snapshot_id",
    "source_url",
    "temporal_snapshot_id",
    "temporal_status",
    "version_id",
    "warnings",
}
_EXTERNAL_WARNING_FIELDS = {"code", "message"}
_EXTERNAL_FAILURE_FIELDS = {"code", "document_id", "message", "provision_id"}
_RETRIEVAL_FAILURE_CODES = {
    "AMBIGUOUS_CITATION",
    "NO_RESULTS",
    "NO_TEMPORAL_EVIDENCE",
    "NO_APPLICABLE_VERSION",
    "MULTIPLE_APPLICABLE_VERSIONS",
    "TEMPORAL_CONFLICT",
    "SOURCE_OBJECT_MISSING",
    "DATE_OUTSIDE_SUPPORTED_RANGE",
    "FUTURE_VERSION_ONLY",
}


EXPECTED_GERMAN_LAW_DESCRIPTOR = KnowledgeModuleDescriptor(
    schema_version=DESCRIPTOR_SCHEMA_VERSION,
    module_id=GERMAN_LAW_MODULE_ID,
    module_version=GERMAN_LAW_MODULE_VERSION,
    display_name=GERMAN_LAW_DISPLAY_NAME,
    description=(
        "Optional read-only retrieval over acquired German federal statutes, "
        "regulations, promulgations, and separately classified administrative rules."
    ),
    domain="LAW",
    subdomains=(
        "GERMAN_FEDERAL_STATUTES_AND_REGULATIONS",
        "GERMAN_FEDERAL_ADMINISTRATIVE_RULES",
        "GERMAN_FEDERAL_OFFICIAL_PROMULGATIONS",
    ),
    jurisdictions=("DE-BUND",),
    languages=("de",),
    source_classes=(
        "OFFICIAL_CONSOLIDATED_TEXT",
        "OFFICIAL_PROMULGATION",
        "OFFICIAL_ADMINISTRATIVE_RULE",
    ),
    corpus_snapshot_ids=GERMAN_LAW_SOURCE_SNAPSHOTS,
    temporal_snapshot_id=GERMAN_LAW_TEMPORAL_SNAPSHOT,
    retrieval_modes=("SOURCE_DISCOVERY", "VERIFIED_AS_OF"),
    supported_filters=(
        "jurisdictions",
        "document_types",
        "source_classes",
        "publishers",
        "languages",
        "official_only",
        "include_administrative_rules",
        "as_of_date",
    ),
    coverage_status="PARTIAL_FEDERAL_COVERAGE",
    currentness_status="PARTIAL_TEMPORAL_COVERAGE",
    licence_status="LICENCE_REVIEW_REQUIRED",
    known_limitations=(
        "Federal material only; EU, Land, municipal, case-law, and forms coverage is excluded.",
        "Temporal coverage is partial and VERIFIED_AS_OF fails closed when evidence is incomplete.",
        "GII consolidated text does not by itself prove historical or current applicability.",
        "Administrative rules are classified separately and are not statutes.",
        "All output is non-authoritative evidence and not binding legal advice.",
    ),
    enabled_by_default=False,
    authority_status="NON_AUTHORITATIVE",
    capability_ids=(),
)


def production_german_law_configuration(
    *,
    module_repository_path: str,
    corpus_data_root: str,
    expected_repository_head: str,
) -> KnowledgeModuleConfiguration:
    return KnowledgeModuleConfiguration(
        schema_version=CONFIGURATION_SCHEMA_VERSION,
        module_repository_path=module_repository_path,
        corpus_data_root=corpus_data_root,
        approved_resolved_corpus_path=APPROVED_RESOLVED_CORPUS_PATH,
        expected_repository_head=expected_repository_head,
        expected_module_id=GERMAN_LAW_MODULE_ID,
        expected_module_version=GERMAN_LAW_MODULE_VERSION,
        expected_descriptor_hash=EXPECTED_GERMAN_LAW_DESCRIPTOR.descriptor_hash,
        expected_corpus_snapshot_id=GERMAN_LAW_FACTORY_SNAPSHOT,
        expected_corpus_snapshot_ids=GERMAN_LAW_SOURCE_SNAPSHOTS,
        expected_temporal_snapshot_id=GERMAN_LAW_TEMPORAL_SNAPSHOT,
        expected_eu_snapshot_id=EU_PILOT_SNAPSHOT,
        expected_eu_snapshot_manifest_hash=EU_PILOT_MANIFEST_HASH,
        expected_manifest_hashes=EXPECTED_MANIFEST_HASHES,
    )


class GermanLawModuleAdapter:
    __slots__ = ("_gateway",)

    def __init__(self, gateway: GermanLawExternalGateway | None = None) -> None:
        self._gateway = gateway or GermanLawExternalGateway()

    def verify(
        self,
        configuration: KnowledgeModuleConfiguration,
        expected_descriptor: KnowledgeModuleDescriptor,
    ) -> KnowledgeModuleVerificationResult:
        repository_head: str | None = None
        resolved_corpus: str | None = None
        manifest_hashes: tuple[tuple[str, str], ...] = ()
        try:
            self._validate_configuration(configuration, expected_descriptor)
            repository = self._resolve_repository(configuration.module_repository_path)
            repository_head = self._repository_head(repository)
            if repository_head != configuration.expected_repository_head:
                raise KnowledgeModuleError(
                    "MODULE_REPOSITORY_MISMATCH",
                    f"German Law HEAD {repository_head} differs from the reviewed pin",
                )
            corpus = self._resolve_corpus_root(configuration)
            resolved_corpus = str(corpus)
            manifest_hashes, temporal = self._verify_manifest_pins(configuration, corpus)
            descriptor = self._descriptor_from_external(self._gateway.descriptor(configuration))
            if descriptor != expected_descriptor:
                raise KnowledgeModuleError(
                    "MODULE_DESCRIPTOR_MISMATCH", "external descriptor differs from registration"
                )
            external_result = self._gateway.verify(configuration)
            external_hash = self._validate_external_verification(
                external_result.payload,
                external_result.returncode,
                configuration,
                corpus,
                temporal,
                manifest_hashes,
            )
            after_hashes, _ = self._verify_manifest_pins(configuration, corpus)
            if after_hashes != manifest_hashes:
                raise KnowledgeModuleError(
                    "CORPUS_VERIFICATION_FAILED", "corpus manifests changed during verification"
                )
            return KnowledgeModuleVerificationResult(
                schema_version=VERIFICATION_SCHEMA_VERSION,
                module_id=GERMAN_LAW_MODULE_ID,
                module_version=GERMAN_LAW_MODULE_VERSION,
                valid=True,
                status="VERIFIED",
                repository_head=repository_head,
                descriptor_hash=descriptor.descriptor_hash,
                resolved_corpus_path=resolved_corpus,
                corpus_snapshot_ids=descriptor.corpus_snapshot_ids,
                temporal_snapshot_id=descriptor.temporal_snapshot_id,
                manifest_hashes=manifest_hashes,
                external_verification_hash=external_hash,
                descriptor=descriptor,
                failures=(),
            )
        except KnowledgeModuleError as exc:
            failure = KnowledgeModuleFailure.create(
                GERMAN_LAW_MODULE_ID,
                exc.status,
                exc.reason,
            )
            return KnowledgeModuleVerificationResult(
                schema_version=VERIFICATION_SCHEMA_VERSION,
                module_id=GERMAN_LAW_MODULE_ID,
                module_version=GERMAN_LAW_MODULE_VERSION,
                valid=False,
                status=exc.status,
                repository_head=repository_head,
                descriptor_hash=None,
                resolved_corpus_path=resolved_corpus,
                corpus_snapshot_ids=(),
                temporal_snapshot_id=None,
                manifest_hashes=manifest_hashes,
                external_verification_hash=None,
                descriptor=None,
                failures=(failure,),
            )
        except Exception:
            failure = KnowledgeModuleFailure.create(
                GERMAN_LAW_MODULE_ID,
                "MODULE_OUTPUT_MALFORMED",
                "German Law verification failed closed on malformed external state",
            )
            return KnowledgeModuleVerificationResult(
                schema_version=VERIFICATION_SCHEMA_VERSION,
                module_id=GERMAN_LAW_MODULE_ID,
                module_version=GERMAN_LAW_MODULE_VERSION,
                valid=False,
                status="MODULE_OUTPUT_MALFORMED",
                repository_head=repository_head,
                descriptor_hash=None,
                resolved_corpus_path=resolved_corpus,
                corpus_snapshot_ids=(),
                temporal_snapshot_id=None,
                manifest_hashes=manifest_hashes,
                external_verification_hash=None,
                descriptor=None,
                failures=(failure,),
            )

    def query(
        self,
        configuration: KnowledgeModuleConfiguration,
        query: KnowledgeModuleQuery,
        expected_descriptor: KnowledgeModuleDescriptor,
    ) -> KnowledgeEvidenceBundle:
        try:
            self._validate_configuration(configuration, expected_descriptor)
            repository = self._resolve_repository(configuration.module_repository_path)
            if self._repository_head(repository) != configuration.expected_repository_head:
                raise KnowledgeModuleError(
                    "MODULE_REPOSITORY_MISMATCH", "German Law repository changed before query"
                )
            corpus = self._resolve_corpus_root(configuration)
            before, _ = self._verify_manifest_pins(configuration, corpus)
            raw = self._gateway.query(configuration, query)
            bundle = self._bundle_from_external(raw, query, expected_descriptor, configuration)
            after, _ = self._verify_manifest_pins(configuration, corpus)
            if before != after:
                raise KnowledgeModuleError(
                    "CORPUS_VERIFICATION_FAILED", "corpus manifests changed during query"
                )
            return bundle
        except KnowledgeModuleError:
            raise
        except Exception as exc:
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED", "German Law query failed closed"
            ) from exc

    @staticmethod
    def _validate_configuration(
        configuration: KnowledgeModuleConfiguration,
        expected_descriptor: KnowledgeModuleDescriptor,
    ) -> None:
        if configuration.approved_resolved_corpus_path != APPROVED_RESOLVED_CORPUS_PATH:
            raise KnowledgeModuleError(
                "CORPUS_PATH_MISMATCH", "approved corpus root is not the reviewed production pin"
            )
        if configuration.expected_module_id != GERMAN_LAW_MODULE_ID:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "module ID pin differs")
        if configuration.expected_module_version != GERMAN_LAW_MODULE_VERSION:
            raise KnowledgeModuleError("MODULE_VERSION_MISMATCH", "module version pin differs")
        if configuration.expected_repository_head != GERMAN_LAW_EXPECTED_HEAD:
            raise KnowledgeModuleError(
                "MODULE_REPOSITORY_MISMATCH", "repository pin is not the reviewed production pin"
            )
        if configuration.expected_descriptor_hash != EXPECTED_GERMAN_LAW_DESCRIPTOR.descriptor_hash:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "descriptor pin differs")
        if expected_descriptor != EXPECTED_GERMAN_LAW_DESCRIPTOR:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "registry descriptor differs")
        if configuration.expected_corpus_snapshot_id != GERMAN_LAW_FACTORY_SNAPSHOT:
            raise KnowledgeModuleError("CORPUS_SNAPSHOT_MISMATCH", "factory snapshot pin differs")
        if configuration.expected_corpus_snapshot_ids != tuple(sorted(GERMAN_LAW_SOURCE_SNAPSHOTS)):
            raise KnowledgeModuleError("CORPUS_SNAPSHOT_MISMATCH", "source snapshot pins differ")
        if configuration.expected_temporal_snapshot_id != GERMAN_LAW_TEMPORAL_SNAPSHOT:
            raise KnowledgeModuleError("TEMPORAL_SNAPSHOT_MISMATCH", "temporal snapshot pin differs")
        if (
            configuration.expected_eu_snapshot_id != EU_PILOT_SNAPSHOT
            or configuration.expected_eu_snapshot_manifest_hash != EU_PILOT_MANIFEST_HASH
        ):
            raise KnowledgeModuleError("CORPUS_SNAPSHOT_MISMATCH", "EU pilot snapshot pin differs")
        if configuration.expected_manifest_hashes != tuple(sorted(EXPECTED_MANIFEST_HASHES)):
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "manifest byte pins differ")

    @staticmethod
    def _resolve_repository(value: str) -> Path:
        supplied = Path(value)
        if not supplied.is_absolute() or ".." in supplied.parts:
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "repository path is invalid")
        absolute = supplied.absolute()
        for component in (absolute, *absolute.parents):
            if component.exists() and component.is_symlink():
                raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "repository symlink is forbidden")
        try:
            root = supplied.resolve(strict=True)
        except OSError as exc:
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "repository does not exist") from exc
        if not root.is_dir() or not (root / ".git").is_dir():
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "repository is not a Git worktree")
        if not (root / "src/german_law_corpus/cli.py").is_file():
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "German Law CLI is missing")
        return root

    @staticmethod
    def _repository_head(repository: Path) -> str:
        git_dir = (repository / ".git").resolve(strict=True)
        try:
            git_dir.relative_to(repository)
        except ValueError as exc:
            raise KnowledgeModuleError("MODULE_REPOSITORY_MISMATCH", "Git directory escapes repository") from exc
        head_text = (git_dir / "HEAD").read_text(encoding="ascii").strip()
        if _SHA40.fullmatch(head_text):
            return head_text
        prefix = "ref: "
        if not head_text.startswith(prefix):
            raise KnowledgeModuleError("MODULE_REPOSITORY_MISMATCH", "Git HEAD is malformed")
        reference = head_text[len(prefix) :]
        if not _GIT_REF.fullmatch(reference) or ".." in reference.split("/"):
            raise KnowledgeModuleError("MODULE_REPOSITORY_MISMATCH", "Git HEAD reference is invalid")
        loose = git_dir / reference
        if loose.is_file():
            value = loose.read_text(encoding="ascii").strip()
            if _SHA40.fullmatch(value):
                return value
        packed = git_dir / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="ascii").splitlines():
                if not line or line.startswith(("#", "^")):
                    continue
                digest, _, name = line.partition(" ")
                if name == reference and _SHA40.fullmatch(digest):
                    return digest
        raise KnowledgeModuleError("MODULE_REPOSITORY_MISMATCH", "Git HEAD commit is unresolved")

    @staticmethod
    def _resolve_corpus_root(configuration: KnowledgeModuleConfiguration) -> Path:
        supplied = Path(configuration.corpus_data_root)
        approved = Path(configuration.approved_resolved_corpus_path)
        if not supplied.is_absolute() or not approved.is_absolute() or ".." in supplied.parts:
            raise KnowledgeModuleError("CORPUS_PATH_MISMATCH", "corpus path is invalid")
        try:
            root = supplied.resolve(strict=True)
            approved_root = approved.resolve(strict=True)
        except OSError as exc:
            raise KnowledgeModuleError("MODULE_NOT_AVAILABLE", "corpus path is unavailable") from exc
        if root != approved_root or not root.is_dir():
            raise KnowledgeModuleError("CORPUS_PATH_MISMATCH", "corpus path escaped its approved root")
        return root

    @staticmethod
    def _manifest_path(corpus: Path, relative: str) -> Path:
        try:
            path = (corpus / relative).resolve(strict=True)
            path.relative_to(corpus)
        except (OSError, ValueError) as exc:
            raise KnowledgeModuleError("CORPUS_PATH_MISMATCH", "manifest path escaped corpus") from exc
        if not path.is_file():
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "manifest is missing")
        return path

    def _verify_manifest_pins(
        self,
        configuration: KnowledgeModuleConfiguration,
        corpus: Path,
    ) -> tuple[tuple[tuple[str, str], ...], dict[str, Any]]:
        actual: list[tuple[str, str]] = []
        for relative, expected in configuration.expected_manifest_hashes:
            path = self._manifest_path(corpus, relative)
            digest = self._sha256_file(path)
            if digest != expected:
                raise KnowledgeModuleError(
                    "CORPUS_VERIFICATION_FAILED", f"manifest hash differs: {relative}"
                )
            actual.append((relative, digest))
        temporal = self._read_json_object(
            self._manifest_path(corpus, "manifests/federal-temporal-graph-1a.json")
        )
        temporal_without_hash = dict(temporal)
        supplied_temporal_hash = temporal_without_hash.pop("manifest_hash", None)
        if supplied_temporal_hash != self._german_hash(temporal_without_hash):
            raise KnowledgeModuleError(
                "CORPUS_VERIFICATION_FAILED", "temporal embedded manifest hash differs"
            )
        source_ids = tuple(sorted(str(item) for item in temporal.get("source_snapshot_ids") or ()))
        if source_ids != configuration.expected_corpus_snapshot_ids:
            raise KnowledgeModuleError("CORPUS_SNAPSHOT_MISMATCH", "temporal source snapshots differ")
        if temporal.get("corpus_snapshot_id") != configuration.expected_temporal_snapshot_id:
            raise KnowledgeModuleError("TEMPORAL_SNAPSHOT_MISMATCH", "temporal snapshot differs")
        factory_hash = str(temporal.get("factory_verification_hash") or "")
        factory_id = f"federal-factory-1a-{factory_hash[:32]}"
        if not _SHA64.fullmatch(factory_hash) or factory_id != configuration.expected_corpus_snapshot_id:
            raise KnowledgeModuleError("CORPUS_SNAPSHOT_MISMATCH", "factory snapshot differs")
        eu_relative = f"snapshots/eu/{configuration.expected_eu_snapshot_id}/snapshot.json"
        eu = self._read_json_object(self._manifest_path(corpus, eu_relative))
        if (
            eu.get("snapshot_id") != configuration.expected_eu_snapshot_id
            or eu.get("manifest_hash") != configuration.expected_eu_snapshot_manifest_hash
        ):
            raise KnowledgeModuleError("CORPUS_SNAPSHOT_MISMATCH", "EU snapshot manifest differs")
        return tuple(sorted(actual)), temporal

    @staticmethod
    def _read_json_object(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "manifest JSON is invalid") from exc
        if not isinstance(value, dict):
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "manifest is not an object")
        return value

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _german_hash(value: Any) -> str:
        return hashlib.sha256(canonical_json_bytes(value) + b"\n").hexdigest()

    @staticmethod
    def _descriptor_from_external(raw: Mapping[str, Any]) -> KnowledgeModuleDescriptor:
        exact_fields(raw, _EXTERNAL_DESCRIPTOR_FIELDS, label="German Law descriptor")
        reject_enabled_authority(raw)
        if raw["module_id"] != GERMAN_LAW_MODULE_ID:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "external module ID differs")
        if raw["module_version"] != GERMAN_LAW_MODULE_VERSION:
            raise KnowledgeModuleError("MODULE_VERSION_MISMATCH", "external module version differs")
        if raw["enabled_by_default"] is not False or raw["authority_status"] != "NON_AUTHORITATIVE":
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "external descriptor claims activation or authority"
            )
        try:
            descriptor = KnowledgeModuleDescriptor(
                schema_version=DESCRIPTOR_SCHEMA_VERSION,
                module_id=raw["module_id"],
                module_version=raw["module_version"],
                display_name=raw["display_name"],
                description=EXPECTED_GERMAN_LAW_DESCRIPTOR.description,
                domain=raw["domain"],
                subdomains=tuple(raw["subdomains"]),
                jurisdictions=tuple(raw["jurisdictions"]),
                languages=tuple(raw["languages"]),
                source_classes=tuple(raw["source_classes"]),
                corpus_snapshot_ids=tuple(raw["corpus_snapshot_ids"]),
                temporal_snapshot_id=raw["temporal_snapshot_id"],
                retrieval_modes=tuple(raw["retrieval_modes"]),
                supported_filters=tuple(raw["supported_filters"]),
                coverage_status=raw["coverage_status"],
                currentness_status=raw["currentness_status"],
                licence_status=raw["licence_status"],
                known_limitations=tuple(raw["known_limitations"]),
                enabled_by_default=False,
                authority_status="NON_AUTHORITATIVE",
                capability_ids=(),
            )
        except (KeyError, TypeError, KnowledgeModuleError) as exc:
            if isinstance(exc, KnowledgeModuleError):
                raise
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "descriptor values are invalid") from exc
        if descriptor.descriptor_hash != EXPECTED_GERMAN_LAW_DESCRIPTOR.descriptor_hash:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "descriptor hash differs")
        return descriptor

    def _validate_external_verification(
        self,
        raw: Mapping[str, Any],
        returncode: int,
        configuration: KnowledgeModuleConfiguration,
        corpus: Path,
        temporal: Mapping[str, Any],
        manifest_hashes: tuple[tuple[str, str], ...],
    ) -> str:
        exact_fields(raw, _EXTERNAL_VERIFY_FIELDS, label="German Law verification")
        reject_enabled_authority(raw)
        if returncode != 0 or raw["valid"] is not True:
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "German Law verify() failed")
        if raw["module_id"] != GERMAN_LAW_MODULE_ID:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "verification module ID differs")
        if raw["module_version"] != GERMAN_LAW_MODULE_VERSION:
            raise KnowledgeModuleError("MODULE_VERSION_MISMATCH", "verification module version differs")
        try:
            reported_root = Path(str(raw["data_root"])).resolve(strict=True)
        except OSError as exc:
            raise KnowledgeModuleError("CORPUS_PATH_MISMATCH", "reported corpus root is invalid") from exc
        if reported_root != corpus:
            raise KnowledgeModuleError("CORPUS_PATH_MISMATCH", "verification corpus path differs")
        if tuple(sorted(raw["corpus_snapshot_ids"])) != configuration.expected_corpus_snapshot_ids:
            raise KnowledgeModuleError("CORPUS_SNAPSHOT_MISMATCH", "verification snapshots differ")
        if raw["temporal_snapshot_id"] != configuration.expected_temporal_snapshot_id:
            raise KnowledgeModuleError("TEMPORAL_SNAPSHOT_MISMATCH", "verification temporal pin differs")
        if raw["manifest_hash"] != temporal["manifest_hash"]:
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "verification manifest differs")
        exact_fields(raw["counts"], _EXTERNAL_VERIFY_COUNT_FIELDS, label="verification counts")
        if any(type(value) is not int or value < 0 for value in raw["counts"].values()):
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "verification counts are invalid")
        if raw["quick_checks"] != {"search": "ok", "temporal": "ok"}:
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "SQLite quick checks failed")
        required_truths = (
            "immutable_sqlite",
            "manifests_unchanged",
            "mutation_attempt_blocked",
            "sql_injection_inert",
        )
        if any(raw[name] is not True for name in required_truths) or raw["sqlite_mode"] != "ro":
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "read-only verification failed")
        if type(raw["filesystem_read_only"]) is not bool:
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "filesystem status is malformed")
        if raw["sampled_source_objects"] != 3 or raw["sampled_source_objects_verified"] != 3:
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "source-object samples failed")
        if raw["network_calls"] != 0 or raw["provider_calls"] != 0 or raw["errors"] != []:
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "verification used a forbidden capability"
            )
        selected = raw["selected_manifest_hashes"]
        if not isinstance(selected, Mapping):
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "manifest proof is malformed")
        for relative, digest in manifest_hashes:
            if relative.startswith("snapshots/eu/"):
                continue
            if selected.get(relative) != digest:
                raise KnowledgeModuleError(
                    "CORPUS_VERIFICATION_FAILED", f"verification omitted manifest {relative}"
                )
        verification_hash = raw["verification_hash"]
        if not isinstance(verification_hash, str) or not _SHA64.fullmatch(verification_hash):
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "verification hash is invalid")
        without_hash = dict(raw)
        without_hash.pop("verification_hash")
        if verification_hash != self._german_hash(without_hash):
            raise KnowledgeModuleError("CORPUS_VERIFICATION_FAILED", "verification hash differs")
        return verification_hash

    def _bundle_from_external(
        self,
        raw: Mapping[str, Any],
        query: KnowledgeModuleQuery,
        descriptor: KnowledgeModuleDescriptor,
        configuration: KnowledgeModuleConfiguration,
    ) -> KnowledgeEvidenceBundle:
        exact_fields(raw, _EXTERNAL_BUNDLE_FIELDS, label="German Law evidence bundle")
        reject_enabled_authority(raw)
        external_material = dict(raw)
        external_bundle_id = external_material.pop("bundle_id")
        expected_external_bundle_id = (
            f"knowledge-bundle-{self._german_hash(external_material)[:32]}"
        )
        if external_bundle_id != expected_external_bundle_id:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "external bundle ID differs")
        if raw["authority_status"] != "NON_AUTHORITATIVE_EVIDENCE_BUNDLE":
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "bundle authority differs")
        if raw["module_id"] != descriptor.module_id:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "bundle module ID differs")
        if raw["module_version"] != descriptor.module_version:
            raise KnowledgeModuleError("MODULE_VERSION_MISMATCH", "bundle module version differs")
        if raw["corpus_snapshot_id"] != configuration.expected_corpus_snapshot_id:
            raise KnowledgeModuleError("CORPUS_SNAPSHOT_MISMATCH", "bundle factory snapshot differs")
        if raw["temporal_snapshot_id"] != configuration.expected_temporal_snapshot_id:
            raise KnowledgeModuleError("TEMPORAL_SNAPSHOT_MISMATCH", "bundle temporal snapshot differs")
        if raw["retrieval_mode"] != query.retrieval_mode or raw["query_as_of_date"] != query.as_of_date:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "bundle query mode differs")
        expected_external_hash = self._external_query_hash(query)
        if raw["query_hash"] != expected_external_hash:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "external query hash differs")
        items_value = raw["evidence_items"]
        warnings_value = raw["coverage_warnings"]
        failures_value = raw["retrieval_failures"]
        if not all(isinstance(value, list) for value in (items_value, warnings_value, failures_value)):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "bundle lists are malformed")
        items = tuple(
            self._evidence_item(item, query, descriptor, configuration)
            for item in items_value
        )
        warnings = tuple(self._coverage_warning(item) for item in warnings_value)
        failures = tuple(self._retrieval_failure(item, descriptor.module_id) for item in failures_value)
        if len(items) > query.max_results:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "result count exceeds request")
        total = sum(len(item.bounded_excerpt) for item in items)
        if (
            type(raw["total_context_characters"]) is not int
            or raw["total_context_characters"] != total
            or total > query.max_total_context_characters
            or any(len(item.bounded_excerpt) > query.max_excerpt_characters for item in items)
        ):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "context budget differs")
        if type(raw["truncated"]) is not bool:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "bundle truncation is invalid")
        return evidence_bundle_from_fields(
            query_hash=query.query_hash,
            module_id=descriptor.module_id,
            module_version=descriptor.module_version,
            descriptor_hash=descriptor.descriptor_hash,
            retrieval_mode=query.retrieval_mode,
            query_as_of_date=query.as_of_date,
            corpus_snapshot_id=configuration.expected_corpus_snapshot_id,
            temporal_snapshot_id=configuration.expected_temporal_snapshot_id,
            evidence_items=items,
            coverage_warnings=warnings,
            retrieval_failures=failures,
            total_context_characters=total,
            truncated=raw["truncated"],
            authority_status="NON_AUTHORITATIVE_EVIDENCE_BUNDLE",
        )

    @staticmethod
    def _external_query_hash(query: KnowledgeModuleQuery) -> str:
        payload = {
            "as_of_date": query.as_of_date,
            "document_types": list(query.document_types),
            "include_administrative_rules": query.include_administrative_rules,
            "jurisdictions": list(query.jurisdictions),
            "languages": list(query.languages),
            "max_excerpt_characters": query.max_excerpt_characters,
            "max_results": query.max_results,
            "max_total_context_characters": query.max_total_context_characters,
            "official_only": True,
            "publishers": [],
            "query_text": query.question,
            "retrieval_mode": query.retrieval_mode,
            "source_classes": list(query.source_classes),
        }
        return GermanLawModuleAdapter._german_hash(payload)

    @staticmethod
    def _coverage_warning(raw: Mapping[str, Any]) -> KnowledgeCoverageWarning:
        exact_fields(raw, _EXTERNAL_WARNING_FIELDS, label="coverage warning")
        if not isinstance(raw["code"], str) or not isinstance(raw["message"], str):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "coverage warning is invalid")
        return KnowledgeCoverageWarning.create(raw["code"], raw["message"])

    @staticmethod
    def _retrieval_failure(raw: Mapping[str, Any], module_id: str) -> KnowledgeModuleFailure:
        exact_fields(raw, _EXTERNAL_FAILURE_FIELDS, label="retrieval failure")
        if raw["code"] not in _RETRIEVAL_FAILURE_CODES or not isinstance(raw["message"], str):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "retrieval failure is invalid")
        details = tuple(
            (name, str(raw[name]))
            for name in ("document_id", "provision_id")
            if raw[name] is not None
        )
        return KnowledgeModuleFailure.create(
            module_id,
            raw["code"],
            raw["message"],
            details=details,
        )

    @staticmethod
    def _evidence_item(
        raw: Mapping[str, Any],
        query: KnowledgeModuleQuery,
        descriptor: KnowledgeModuleDescriptor,
        configuration: KnowledgeModuleConfiguration,
    ) -> KnowledgeEvidenceItem:
        exact_fields(raw, _EXTERNAL_ITEM_FIELDS, label="evidence item")
        reject_enabled_authority(raw)
        if raw["authority_status"] != "NON_AUTHORITATIVE_EVIDENCE":
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "item authority differs")
        if raw["module_id"] != descriptor.module_id:
            raise KnowledgeModuleError("MODULE_DESCRIPTOR_MISMATCH", "item module ID differs")
        if raw["module_version"] != descriptor.module_version:
            raise KnowledgeModuleError("MODULE_VERSION_MISMATCH", "item module version differs")
        if raw["document_type"] not in DOCUMENT_TYPES or raw["source_class"] not in SOURCE_CLASSES:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "item source classification differs")
        if query.document_types and raw["document_type"] not in query.document_types:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "item document filter differs")
        if query.source_classes and raw["source_class"] not in query.source_classes:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "item source filter differs")
        if raw["source_snapshot_id"] is not None and (
            raw["source_snapshot_id"] not in configuration.expected_corpus_snapshot_ids
        ):
            raise KnowledgeModuleError("CORPUS_SNAPSHOT_MISMATCH", "item source snapshot differs")
        if (
            raw["corpus_snapshot_id"] != configuration.expected_corpus_snapshot_id
            or raw["temporal_snapshot_id"] != configuration.expected_temporal_snapshot_id
            or raw["retrieval_mode"] != query.retrieval_mode
        ):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "item provenance differs")
        if raw["jurisdiction"] not in query.jurisdictions:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "item jurisdiction differs")
        if not query.include_administrative_rules and (
            raw["document_type"] == "ADMINISTRATIVE_RULE"
            or raw["source_class"] == "OFFICIAL_ADMINISTRATIVE_RULE"
        ):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "administrative rule was not requested")
        warnings = raw["warnings"]
        if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "item warnings are invalid")
        return evidence_item_from_fields(
            module_id=raw["module_id"],
            module_version=raw["module_version"],
            corpus_snapshot_id=raw["corpus_snapshot_id"],
            temporal_snapshot_id=raw["temporal_snapshot_id"],
            retrieval_mode=raw["retrieval_mode"],
            jurisdiction=raw["jurisdiction"],
            document_id=raw["document_id"],
            provision_id=raw["provision_id"],
            version_id=raw["version_id"],
            document_type=raw["document_type"],
            source_class=raw["source_class"],
            official_title=raw["official_title"],
            official_abbreviation=raw["official_abbreviation"],
            provision_number=raw["provision_number"],
            heading=raw["heading"],
            bounded_excerpt=raw["excerpt"],
            excerpt_truncated=raw["excerpt_incomplete"],
            source_url=raw["source_url"],
            source_object_sha256=raw["source_object_sha256"],
            publication_reference=raw["publication_reference"],
            publication_date=raw["publication_date"],
            effective_from=raw["effective_from"],
            effective_until=raw["effective_until"],
            temporal_status=raw["temporal_status"],
            licence_status=raw["licence_status"],
            retrieval_score=raw["retrieval_score"],
            warnings=tuple(warnings),
            source_snapshot_id=raw["source_snapshot_id"],
            authority_status="NON_AUTHORITATIVE_EVIDENCE",
        )


def production_knowledge_module_registry() -> KnowledgeModuleRegistry:
    return KnowledgeModuleRegistry().register(
        KnowledgeModuleRegistration(
            descriptor=EXPECTED_GERMAN_LAW_DESCRIPTOR,
            adapter_factory=GermanLawModuleAdapter,
        )
    )


__all__ = (
    "APPROVED_RESOLVED_CORPUS_PATH",
    "EU_PILOT_MANIFEST_HASH",
    "EU_PILOT_SNAPSHOT",
    "EXPECTED_GERMAN_LAW_DESCRIPTOR",
    "EXPECTED_MANIFEST_HASHES",
    "GERMAN_LAW_EXPECTED_HEAD",
    "GERMAN_LAW_FACTORY_SNAPSHOT",
    "GERMAN_LAW_MODULE_ID",
    "GERMAN_LAW_MODULE_VERSION",
    "GERMAN_LAW_SOURCE_SNAPSHOTS",
    "GERMAN_LAW_TEMPORAL_SNAPSHOT",
    "GermanLawModuleAdapter",
    "production_german_law_configuration",
    "production_knowledge_module_registry",
)
