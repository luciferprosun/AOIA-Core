"""Owned local CockroachDB runtime for the final recording application.

All migrations, corpus loading, RLS role creation, and retrieval classes come
from the frozen Memory Patch repository.  This module never opens an AWS
database connection and never mutates the jury deployment.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

import run_cockroachdb_migrations as migrations
import run_step18_retrieval_validation as step18
import run_step27_personal_memory_validation as step27
import run_source_registry_validation as step9_validation
import step38_real_retrieval as real_retrieval
from aioa_memory_kernel.contracts import MemoryTargetScope
from aioa_memory_kernel.contracts.serialization import canonical_sha256
from aioa_memory_kernel.persistence import SerializableTransactionRunner
from aioa_memory_kernel.security.credentials import CredentialPurpose
from aioa_memory_kernel.sources import (
    OriginMetadata,
    ParserIdentity,
    ProvenanceArtifactIdentity,
    RedactionState,
    SourceAccessClass,
    SourceAuthorityAssessment,
    SourceAuthorityLevel,
    SourceLicenseAssessment,
    SourceLicenseStatus,
    SourcePublicationState,
    SourceRegistryRecord,
    SourceScopeDimensions,
    TransformationIdentity,
)
from aioa_memory_kernel.temporal import TEMPORAL_FACTS_DIGEST_SCHEME, TemporalFacts

from .runtime import OWNER_USER_ID, TENANT_ID


EXPECTED_MIGRATIONS = 19
EXPECTED_RLS_TABLES = 52
COCKROACH_VERSION = "v26.2.5"
NACHWG_PACK_ID = "DE-NACHWG-HARD-KNOWLEDGE-2026"
NACHWG_SOURCE_KIND = "REPUTABLE_LEGAL_SECONDARY"
NACHWG_PDF_SHA256 = "fe70b8eaa3a578d17d6578f477526c2642bb0d2fce2d206e9fd3bfb22f614311"
NACHWG_VERIFIED_AT = datetime(2026, 8, 15, tzinfo=UTC)
NACHWG_PACK_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "german_nachwg_hard_knowledge_2026.json"
)
DEFAULT_BINARY = Path(
    "/home/l/.cache/cockroach-v26.2.5/extracted/"
    "cockroach-v26.2.5.linux-amd64/cockroach"
)


class CockroachStartupError(RuntimeError):
    """A safe local startup failure."""


@dataclass(slots=True)
class OwnedCockroachRuntime:
    runtime: migrations.LocalRuntime
    root: object
    database: str
    app_role: str
    runner: SerializableTransactionRunner
    migration_count: int
    rls_table_count: int
    _closed: bool = False

    def close(self) -> dict[str, object]:
        if self._closed:
            return {"already_closed": True}
        self._closed = True
        return step18._stop_owned_runtime(self.runtime)


def start_owned_runtime(binary: Path = DEFAULT_BINARY) -> OwnedCockroachRuntime:
    try:
        resolved_binary = binary.expanduser().resolve(strict=True)
    except OSError as error:
        raise CockroachStartupError("PINNED_COCKROACH_BINARY_UNAVAILABLE") from error
    migrations.verify_binary_identity(resolved_binary)
    # Reuse the canonical Step 38 disposable ownership prefix so the existing
    # runtime cleanup guard can prove this node is safe to remove.
    run_id = "mp_step38_final_recording_" + uuid.uuid4().hex[:10]
    database = run_id + "_db"
    app_role = "mp_final_recording_app_" + uuid.uuid4().hex[:10]
    runtime = migrations.LocalRuntime(resolved_binary, run_id)
    try:
        print("Preparing owned loopback CockroachDB v26.2.5...", flush=True)
        root = step18._start_disposable_runtime(runtime)
        _configure_disposable_cluster(
            migrations.SqlClient(runtime.binary, root.sql_port)
        )
        migrations.create_database(root, database)
        print("Applying 19 canonical Memory Patch migrations...", flush=True)
        applied = migrations.apply_migrations(root, database, timeout=300)
        print("Verifying migration replay and RLS/FORCE RLS...", flush=True)
        replay = migrations.apply_migrations(root, database, timeout=300)
        migration_count = len(migrations.load_migrations())
        if (
            migration_count != EXPECTED_MIGRATIONS
            or len(applied["applied"]) != EXPECTED_MIGRATIONS
            or replay["applied"]
            or len(replay["skipped"]) != EXPECTED_MIGRATIONS
        ):
            raise CockroachStartupError("MIGRATION_REPLAY_VALIDATION_FAILED")
        if not migrations.assert_step36_security_catalog(root, database):
            raise CockroachStartupError("COCKROACH_SECURITY_CATALOG_FAILED")
        rls_table_count = int(
            migrations.one_value(
                root.execute(
                    database,
                    "SELECT count(*) FROM pg_catalog.pg_class AS c "
                    "JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'memory_patch' AND c.relkind = 'r' "
                    "AND c.relrowsecurity AND c.relforcerowsecurity",
                    timeout=60,
                )
            )
        )
        if rls_table_count != EXPECTED_RLS_TABLES:
            raise CockroachStartupError("RLS_FORCE_RLS_VALIDATION_FAILED")
        step27._create_validation_role(root, app_role)
        print("Loading the hash-verified German-law corpus fixture...", flush=True)
        _seed_canonical_corpus(root, database)
        print("Planning the atomic NachwG Hard Knowledge import...", flush=True)
        import_stats = _seed_nachwg_hard_knowledge(root, database)
        print(
            "NachwG Hard Knowledge ready: "
            f"added={import_stats['added']} unchanged={import_stats['unchanged']} "
            f"current={import_stats['current']} superseded={import_stats['superseded']}.",
            flush=True,
        )
        runner = _application_runner(
            port=root.sql_port,
            database=database,
            role=app_role,
        )
        print("CockroachDB German-law knowledge is ready.", flush=True)
        return OwnedCockroachRuntime(
            runtime=runtime,
            root=root,
            database=database,
            app_role=app_role,
            runner=runner,
            migration_count=migration_count,
            rls_table_count=rls_table_count,
        )
    except BaseException:
        if runtime.process is not None:
            try:
                step18._stop_owned_runtime(runtime)
            except Exception:
                pass
        raise


def _application_runner(
    *, port: int, database: str, role: str
) -> SerializableTransactionRunner:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:
        raise CockroachStartupError("PSYCOPG_RUNTIME_UNAVAILABLE") from error

    def connect():
        return psycopg.connect(
            host="127.0.0.1",
            port=port,
            dbname=database,
            user=role,
            sslmode="disable",
            autocommit=True,
            connect_timeout=10,
            options="-c statement_timeout=60000",
            prepare_threshold=None,
            row_factory=dict_row,
        )

    return SerializableTransactionRunner(
        connect,
        credential_purpose=CredentialPurpose.APPLICATION_DATABASE,
    )


def _seed_canonical_corpus(root: object, database: str) -> None:
    roots = real_retrieval.Step38CorpusRoots(
        step14_bundle_root=step18.DEFAULT_STEP14,
        step15_bundle_root=step18.DEFAULT_STEP15,
        step16_bundle_root=step18.DEFAULT_STEP16,
        source_root=step18.DEFAULT_SOURCE_ROOT,
    )
    item, provisions, candidate, manifest_digest = real_retrieval._load_fixture(roots)
    base = real_retrieval.build_source_registry_record(
        candidate,
        created_at=step18.FIXTURE_TIME,
    )
    records = real_retrieval._fixture_records(base, TENANT_ID)
    provision_iii = next(
        value for value in provisions if value.get("provision_identifier") == "III."
    )
    receipt = real_retrieval.project_bmjernano_temporal_facts(
        str(provision_iii["official_text_de"])
    )
    root.execute(
        database,
        step18._seed_sql(records, item, provisions, manifest_digest),
        timeout=300,
    )
    root.execute(
        database,
        real_retrieval._temporal_projection_sql(
            tenant_id=TENANT_ID,
            receipt=receipt,
        ),
        timeout=60,
    )
    q = migrations.sql_literal
    root.execute(
        database,
        "INSERT INTO memory_patch.users "
        "(tenant_id, user_id, display_name, metadata, created_at, updated_at) VALUES ("
        f"{q(TENANT_ID)}, {q(OWNER_USER_ID)}, 'Local recording operator', "
        "'{\"mode\":\"LOCAL_FINAL_RECORDING_UI\"}'::JSONB, now(), now())",
        timeout=60,
    )


def _seed_nachwg_hard_knowledge(root: object, database: str) -> dict[str, int]:
    """Dry-run, atomically import, and replay-check the local verified pack."""

    pack = _load_nachwg_pack()
    entries = _nachwg_seed_entries(pack)
    initial = _nachwg_import_plan(root, database, entries)
    print(
        "NachwG import dry-run: "
        f"insert={initial['insert']} unchanged={initial['unchanged']} "
        f"conflict={initial['conflict']} duplicate_ids=0.",
        flush=True,
    )
    if initial["conflict"]:
        raise CockroachStartupError("BLOCKED_KNOWLEDGE_CONFLICT")
    if initial["insert"]:
        statements = root._statements(_nachwg_seed_sql(entries))
        root.execute_results(
            database,
            statements,
            timeout=300,
            separate_transactions=False,
        )
    replay = _nachwg_import_plan(root, database, entries)
    if replay != {"insert": 0, "unchanged": 36, "conflict": 0}:
        raise CockroachStartupError("KNOWLEDGE_IDEMPOTENCY_VALIDATION_FAILED")
    return {
        "added": initial["insert"],
        "unchanged": initial["unchanged"],
        "current": 31,
        "superseded": 5,
    }


def _load_nachwg_pack() -> Mapping[str, Any]:
    try:
        raw = NACHWG_PACK_PATH.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CockroachStartupError("NACHWG_PACK_UNAVAILABLE") from error
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        raise CockroachStartupError("NACHWG_PACK_INVALID")
    records = value["records"]
    ids = [record.get("knowledge_id") for record in records if isinstance(record, dict)]
    statuses = [record.get("status") for record in records if isinstance(record, dict)]
    source_package = value.get("source_package")
    fingerprint = (
        source_package.get("pdf_sha256")
        if isinstance(source_package, dict)
        else value.get("source_fingerprint", value.get("pdf_sha256"))
    )
    if (
        len(records) != 36
        or len(ids) != 36
        or len(set(ids)) != 36
        or any(not isinstance(item, str) or not item for item in ids)
        or statuses.count("CURRENT") != 31
        or statuses.count("SUPERSEDED") != 5
        or fingerprint != NACHWG_PDF_SHA256
    ):
        raise CockroachStartupError("NACHWG_PACK_INVALID")
    required = {
        "knowledge_id",
        "topic",
        "jurisdiction",
        "valid_from",
        "valid_to",
        "status",
        "rule",
        "exceptions",
        "statutory_basis",
        "source_urls",
        "confidence",
    }
    for record in records:
        if not isinstance(record, dict) or not required.issubset(record):
            raise CockroachStartupError("NACHWG_PACK_INVALID")
        if record["jurisdiction"] != "DE" or record["confidence"] != "HIGH":
            raise CockroachStartupError("NACHWG_PACK_INVALID")
        if record.get("source_fingerprint", NACHWG_PDF_SHA256) != NACHWG_PDF_SHA256:
            raise CockroachStartupError("NACHWG_PACK_INVALID")
    return value


def _nachwg_seed_entries(pack: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    entries: list[Mapping[str, Any]] = []
    for record in sorted(pack["records"], key=lambda item: str(item["knowledge_id"])):
        knowledge_id = str(record["knowledge_id"])
        suffix = hashlib.sha256(knowledge_id.encode("utf-8")).hexdigest()[:20]
        source_id = f"nachwg-hard-{suffix}"
        snapshot_id = f"nachwg-snapshot-{suffix}"
        version_id = f"nachwg-version-{suffix}"
        chunk_id = f"nachwg-chunk-{suffix}"
        content = _nachwg_content(record)
        content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        temporal = _nachwg_temporal_facts(record)
        metadata = dict(record)
        # The verified pack declares several one-to-many historical links.
        # Step 21 intentionally treats such a graph as ambiguous, so retain
        # those source declarations as provenance while canonical temporal
        # selection relies on the verified non-overlapping intervals.
        metadata["declared_supersedes"] = list(metadata.pop("supersedes", ()))
        metadata["declared_superseded_by"] = list(
            metadata.pop("superseded_by", ())
        )
        metadata.update(
            {
                "document_identity": NACHWG_PACK_ID,
                "version_identity": knowledge_id,
                "official_identifier": NACHWG_PACK_ID,
                "provision_identifier": knowledge_id,
                "source_fingerprint": NACHWG_PDF_SHA256,
                "temporal_facts": temporal,
                "temporal_facts_digest": temporal["temporal_facts_digest"],
                "temporal_facts_digest_scheme": TEMPORAL_FACTS_DIGEST_SCHEME,
                "model_generated": False,
                "redaction_state": "NOT_REQUIRED",
            }
        )
        record_digest = canonical_sha256(record)
        entries.append(
            {
                "knowledge_id": knowledge_id,
                "source_id": source_id,
                "snapshot_id": snapshot_id,
                "version_id": version_id,
                "chunk_id": chunk_id,
                "content": content,
                "content_sha256": content_sha256,
                "metadata": metadata,
                "record_digest": record_digest,
                "registry": _nachwg_registry_record(
                    knowledge_id=knowledge_id,
                    source_id=source_id,
                    snapshot_id=snapshot_id,
                    version_id=version_id,
                    content_sha256=content_sha256,
                    content_bytes=len(content.encode("utf-8")),
                    record=record,
                ),
            }
        )
    return tuple(entries)


def _nachwg_content(record: Mapping[str, Any]) -> str:
    def text(value: object) -> str:
        if isinstance(value, (tuple, list)):
            return "; ".join(str(item) for item in value) or "NONE"
        if value in (None, ""):
            return "NONE"
        return str(value)

    return "\n".join(
        (
            "KNOWLEDGE_SCOPE: German Law / NachwG",
            f"KNOWLEDGE_ID: {record['knowledge_id']}",
            f"TOPIC: {record['topic']}",
            f"JURISDICTION: {record['jurisdiction']}",
            f"VALID_FROM: {record['valid_from']}",
            f"VALID_TO_INCLUSIVE: {text(record['valid_to'])}",
            f"STATUS: {record['status']}",
            f"RULE: {record['rule']}",
            f"EXCEPTIONS: {text(record['exceptions'])}",
            f"STATUTORY_BASIS: {text(record['statutory_basis'])}",
            f"SOURCE_LEDGER_IDS: {text(record.get('source_ids', ())) }",
            f"CONFIDENCE: {record['confidence']}",
        )
    )


def _nachwg_temporal_facts(record: Mapping[str, Any]) -> Mapping[str, Any]:
    effective_from = _date_time(str(record["valid_from"]))
    raw_to = record.get("valid_to")
    effective_to = None
    if raw_to not in (None, "", "CURRENT"):
        effective_to = _date_time(str(raw_to)) + timedelta(days=1)
    status = str(record["status"])
    facts = TemporalFacts(
        effective_from=effective_from,
        effective_to=effective_to,
        verified_at=NACHWG_VERIFIED_AT,
        source_observed_at=NACHWG_VERIFIED_AT,
        snapshot_captured_at=NACHWG_VERIFIED_AT,
        superseded_at=effective_to if status == "SUPERSEDED" else None,
        version_status=status,
        consolidation_status="VERIFIED_RESEARCH_PACKAGE",
        document_identity=NACHWG_PACK_ID,
        version_identity=str(record["knowledge_id"]),
        official_identifier=NACHWG_PACK_ID,
        provision_identifier=str(record["knowledge_id"]),
    )
    result: dict[str, Any] = {
        "effective_from": _iso(facts.effective_from),
        "effective_to": _iso(facts.effective_to),
        "verified_at": _iso(facts.verified_at),
        "source_observed_at": _iso(facts.source_observed_at),
        "snapshot_captured_at": _iso(facts.snapshot_captured_at),
        "superseded_at": _iso(facts.superseded_at),
        "version_status": facts.version_status,
        "consolidation_status": facts.consolidation_status,
        "supersedes": [],
        "superseded_by": [],
        "temporal_facts_digest": facts.facts_hash,
        "temporal_facts_digest_scheme": TEMPORAL_FACTS_DIGEST_SCHEME,
    }
    return {key: value for key, value in result.items() if value is not None}


def _nachwg_registry_record(
    *,
    knowledge_id: str,
    source_id: str,
    snapshot_id: str,
    version_id: str,
    content_sha256: str,
    content_bytes: int,
    record: Mapping[str, Any],
) -> SourceRegistryRecord:
    parser = ParserIdentity("verified-atomic-pack-parser", "1.0.0", "1.0.0")
    transformation = TransformationIdentity(
        "nachwg-atomic-record-projection", "1.0.0", "1.0.0"
    )
    origin = OriginMetadata(
        "VERIFIED_OPERATOR_ATTACHMENT",
        "German_NachwG_Temporal_Legal_Audit_2026",
        "2026-08-15",
        "final-recording-local-ingest-1a",
        f"attachment:German_NachwG_Temporal_Legal_Audit_2026#{knowledge_id}",
        NACHWG_VERIFIED_AT,
    )
    artifact = ProvenanceArtifactIdentity(
        "ATOMIC_VERIFIED_LEGAL_RECORD",
        content_sha256,
        content_bytes,
        "text/plain; charset=utf-8",
        origin,
        parser,
        transformation,
        NACHWG_VERIFIED_AT,
        # The snapshot stores these exact canonical atomic-record bytes.  This
        # does not claim that the projection is an authentic copy of the PDF;
        # that distinction remains explicit in the authority metadata above.
        exact_source_bytes=True,
        model_generated=False,
    )
    scope = SourceScopeDimensions(
        tenant_id=TENANT_ID,
        hat_scope_id=real_retrieval.REAL_HAT_SCOPE_ID,
        target_scope=MemoryTargetScope.SHARED_KNOWLEDGE_HAT,
        domain="law.de.employment.nachwg",
        jurisdiction="DE_FEDERAL",
        language="en",
        temporal_policy_reference="step21-canonical-temporal-policy-1a",
        source_collection=("german-nachwg-hard-knowledge-2026",),
        additional_dimensions={
            "source_fingerprint": NACHWG_PDF_SHA256,
            "verified_research_package": True,
            "not_authentic_promulgation": True,
        },
    )
    return SourceRegistryRecord(
        tenant_id=TENANT_ID,
        source_id=source_id,
        hat_scope_id=real_retrieval.REAL_HAT_SCOPE_ID,
        source_kind=NACHWG_SOURCE_KIND,
        source_reference=f"pdf:German_NachwG_Temporal_Legal_Audit_2026#{knowledge_id}",
        scope=scope,
        authority=SourceAuthorityAssessment(
            SourceAuthorityLevel.AUTHORITATIVE_SECONDARY,
            {
                "assessment": "operator-authorized verified legal research package",
                "source_fingerprint": NACHWG_PDF_SHA256,
                "source_ledger_ids": list(record.get("source_ids", ())),
                "not_authentic_promulgation": True,
            },
        ),
        license=SourceLicenseAssessment(
            SourceLicenseStatus.PRIVATE_AUTHORIZED,
            "operator-authorized-recording-use",
            "attachment:deployment-instructions",
        ),
        access_class=SourceAccessClass.TENANT_RESTRICTED,
        redaction_state=RedactionState.NOT_REQUIRED,
        parser=parser,
        transformation=transformation,
        origin=origin,
        artifact=artifact,
        snapshot_id=snapshot_id,
        knowledge_version_id=version_id,
        current_publication_state=SourcePublicationState.PUBLISHED,
        current_publication_sequence=3,
        current_publication_event_digest=canonical_sha256(
            {"event": "LOCAL_VERIFIED_PACK_PUBLICATION", "source_id": source_id}
        ),
        created_at=NACHWG_VERIFIED_AT,
        updated_at=NACHWG_VERIFIED_AT,
    )


def _nachwg_import_plan(
    root: object,
    database: str,
    entries: tuple[Mapping[str, Any], ...],
) -> dict[str, int]:
    q = migrations.sql_literal
    ids = ", ".join(q(str(item["source_id"])) for item in entries)
    total = int(
        migrations.one_value(
            root.execute(
                database,
                "SELECT count(*) FROM memory_patch.source_registry_entries "
                f"WHERE tenant_id = {q(TENANT_ID)} AND source_id IN ({ids})",
                timeout=60,
            )
        )
    )
    if total == 0:
        return {"insert": 36, "unchanged": 0, "conflict": 0}
    exact_predicates = " OR ".join(
        "(source_id = "
        + q(str(item["source_id"]))
        + " AND artifact_digest = "
        + q(str(item["content_sha256"]))
        + ")"
        for item in entries
    )
    exact = int(
        migrations.one_value(
            root.execute(
                database,
                "SELECT count(*) FROM memory_patch.source_registry_entries "
                f"WHERE tenant_id = {q(TENANT_ID)} AND ({exact_predicates})",
                timeout=60,
            )
        )
    )
    table_counts = []
    for table in (
        "knowledge_sources",
        "source_snapshots",
        "knowledge_versions",
        "knowledge_chunks",
        "chunk_search_documents",
    ):
        table_counts.append(
            int(
                migrations.one_value(
                    root.execute(
                        database,
                        f"SELECT count(*) FROM memory_patch.{table} "
                        f"WHERE tenant_id = {q(TENANT_ID)} AND source_id IN ({ids})",
                        timeout=60,
                    )
                )
            )
        )
    if total == exact == 36 and table_counts == [36] * 5:
        return {"insert": 0, "unchanged": 36, "conflict": 0}
    return {"insert": 0, "unchanged": 0, "conflict": max(total, 1)}


def _nachwg_seed_sql(entries: tuple[Mapping[str, Any], ...]) -> str:
    q = migrations.sql_literal
    j = step9_validation.sql_json
    at = step9_validation.timestamp_sql(NACHWG_VERIFIED_AT)
    statements: list[str] = []
    for item in entries:
        source_id = str(item["source_id"])
        snapshot_id = str(item["snapshot_id"])
        version_id = str(item["version_id"])
        chunk_id = str(item["chunk_id"])
        content = str(item["content"])
        digest = str(item["content_sha256"])
        statements.extend(
            (
                "INSERT INTO memory_patch.knowledge_sources "
                "(tenant_id, source_id, hat_scope_id, source_kind, source_reference, "
                "provenance, source_observed_at, created_at) VALUES ("
                f"{q(TENANT_ID)}, {q(source_id)}, {q(real_retrieval.REAL_HAT_SCOPE_ID)}, "
                f"{q(NACHWG_SOURCE_KIND)}, {q(item['registry'].source_reference)}, "
                f"{j({'source_fingerprint': NACHWG_PDF_SHA256, 'record_digest': item['record_digest']})}, "
                f"{at}, {at})",
                "INSERT INTO memory_patch.source_snapshots "
                "(tenant_id, snapshot_id, source_id, hat_scope_id, content_sha256, "
                "byte_length, storage_class, immutable_object_reference, captured_at, "
                "source_observed_at, provenance) VALUES ("
                f"{q(TENANT_ID)}, {q(snapshot_id)}, {q(source_id)}, "
                f"{q(real_retrieval.REAL_HAT_SCOPE_ID)}, {q(digest)}, "
                f"{len(content.encode('utf-8'))}, 'EXTERNAL_DERIVED', "
                f"{q('local-pack:' + NACHWG_PACK_ID + ':' + str(item['knowledge_id']))}, "
                f"{at}, {at}, {j({'source_fingerprint': NACHWG_PDF_SHA256, 'record_digest': item['record_digest']})})",
                "INSERT INTO memory_patch.knowledge_versions "
                "(tenant_id, knowledge_version_id, source_id, snapshot_id, hat_scope_id, "
                "parent_knowledge_version_id, version_ordinal, normalized_content_sha256, "
                "normalization_profile, is_current, created_at, provenance) VALUES ("
                f"{q(TENANT_ID)}, {q(version_id)}, {q(source_id)}, {q(snapshot_id)}, "
                f"{q(real_retrieval.REAL_HAT_SCOPE_ID)}, NULL, 1, {q(digest)}, "
                f"'unicode-nfc-text-normalization', true, {at}, "
                f"{j({'record_digest': item['record_digest'], 'source_fingerprint': NACHWG_PDF_SHA256})})",
                "INSERT INTO memory_patch.knowledge_chunks "
                "(tenant_id, chunk_id, knowledge_version_id, source_id, hat_scope_id, "
                "chunk_ordinal, content_text, content_sha256, start_offset, end_offset, "
                "language_tag, metadata, created_at) VALUES ("
                f"{q(TENANT_ID)}, {q(chunk_id)}, {q(version_id)}, {q(source_id)}, "
                f"{q(real_retrieval.REAL_HAT_SCOPE_ID)}, 0, {q(content)}, {q(digest)}, "
                f"NULL, NULL, 'en', {j(item['metadata'])}, {at})",
                "INSERT INTO memory_patch.chunk_search_documents "
                "(tenant_id, chunk_id, knowledge_version_id, source_id, hat_scope_id, "
                "search_config, search_vector, created_at) VALUES ("
                f"{q(TENANT_ID)}, {q(chunk_id)}, {q(version_id)}, {q(source_id)}, "
                f"{q(real_retrieval.REAL_HAT_SCOPE_ID)}, 'german', "
                f"to_tsvector('german', {q(content)}), {at})",
                step9_validation.registry_insert_sql(item["registry"]),
            )
        )
    return "BEGIN;\n" + ";\n".join(statements) + ";\nCOMMIT;"


def _date_time(value: str) -> datetime:
    try:
        return datetime.combine(date.fromisoformat(value), datetime.min.time(), UTC)
    except ValueError as error:
        raise CockroachStartupError("NACHWG_PACK_TEMPORAL_INVALID") from error


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat().replace("+00:00", "Z")


def _configure_disposable_cluster(client: object) -> None:
    client.execute(
        "defaultdb",
        "SET CLUSTER SETTING sql.stats.automatic_collection.enabled = false",
        timeout=60,
    )


__all__ = [
    "COCKROACH_VERSION",
    "CockroachStartupError",
    "NACHWG_PACK_ID",
    "NACHWG_SOURCE_KIND",
    "OwnedCockroachRuntime",
    "start_owned_runtime",
]
