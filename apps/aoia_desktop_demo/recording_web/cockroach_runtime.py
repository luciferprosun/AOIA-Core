"""Owned local CockroachDB runtime for the final recording application.

All migrations, corpus loading, RLS role creation, and retrieval classes come
from the frozen Memory Patch repository.  This module never opens an AWS
database connection and never mutates the jury deployment.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import run_cockroachdb_migrations as migrations
import run_step18_retrieval_validation as step18
import run_step27_personal_memory_validation as step27
import step38_real_retrieval as real_retrieval
from aioa_memory_kernel.persistence import SerializableTransactionRunner
from aioa_memory_kernel.security.credentials import CredentialPurpose

from .runtime import OWNER_USER_ID, TENANT_ID


EXPECTED_MIGRATIONS = 19
EXPECTED_RLS_TABLES = 52
COCKROACH_VERSION = "v26.2.5"
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


def _configure_disposable_cluster(client: object) -> None:
    client.execute(
        "defaultdb",
        "SET CLUSTER SETTING sql.stats.automatic_collection.enabled = false",
        timeout=60,
    )


__all__ = [
    "COCKROACH_VERSION",
    "CockroachStartupError",
    "OwnedCockroachRuntime",
    "start_owned_runtime",
]
