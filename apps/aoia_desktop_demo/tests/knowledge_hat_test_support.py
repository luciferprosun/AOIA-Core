"""Deterministic in-memory Knowledge HAT fixtures for desktop-demo tests."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.aoia_desktop_demo.knowledge.hats.canonical import (
    build_attachment,
    build_bundle,
    canonical_sha256,
    passage_digest_payload,
    sha256_text,
)
from apps.aoia_desktop_demo.knowledge.hats.contracts import (
    HatAttachment,
    HatDescriptor,
    HatPassage,
)
from apps.aoia_desktop_demo.knowledge.hats.adapters.german_federal_employment_worker_law import (
    GermanLawCorpusIdentity,
)
from apps.aoia_desktop_demo.knowledge.hats.prompt_rendering import render_evidence_bundle


def make_attachment(
    descriptor: HatDescriptor,
    *,
    excerpt: str = "Bounded fixture evidence.",
    manifest_digest: str = "1" * 64,
    index_digest: str = "2" * 64,
) -> HatAttachment:
    source_values = {
        "hat_id": descriptor.hat_id,
        "library_id": "fixture-library",
        "library_version": "1",
        "source_id": "fixture-document:fixture-provision",
        "source_title": "Fixture Source",
        "source_locator": "normalized/documents/fixture-document.json#fixture-provision",
        "statutory_references": ("FixtureG § 1",),
        "effective_dates": ("2026-01-01",),
        "excerpt": excerpt,
    }
    passage = HatPassage(
        source_id=source_values["source_id"],
        source_title=source_values["source_title"],
        source_locator=source_values["source_locator"],
        statutory_references=source_values["statutory_references"],
        effective_dates=source_values["effective_dates"],
        excerpt=excerpt,
        rank=1,
        score=100,
        content_digest=canonical_sha256(passage_digest_payload(**source_values)),
    )
    bundle = build_bundle(
        schema_version=descriptor.evidence_schema_version,
        hat_id=descriptor.hat_id,
        normalized_query="fixture query",
        query_digest=sha256_text("fixture query"),
        library_id="fixture-library",
        library_version="1",
        manifest_id="fixture-manifest",
        manifest_digest=manifest_digest,
        index_id="fixture-index",
        index_digest=index_digest,
        passages=(passage,),
    )
    return build_attachment(descriptor, bundle, render_evidence_bundle(bundle))


def mutate_passage_excerpt(attachment: HatAttachment, excerpt: str) -> HatAttachment:
    passage = replace(attachment.bundle.passages[0], excerpt=excerpt)
    bundle = replace(attachment.bundle, passages=(passage,))
    return replace(attachment, bundle=bundle)


def make_german_law_fixture() -> tuple[
    TemporaryDirectory[str],
    Path,
    GermanLawCorpusIdentity,
]:
    temporary = TemporaryDirectory()
    root = Path(temporary.name)
    (root / "indexes").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "normalized" / "documents").mkdir(parents=True)
    (root / "objects" / "sha256").mkdir(parents=True)

    rows = (
        {
            "record_id": "provision-gewo-105",
            "document_id": "de-bund-gii-gewo",
            "title": "Gewerbeordnung",
            "abbreviation": "GewO",
            "provision_number": "§ 105",
            "heading": "Freie Gestaltung des Arbeitsvertrages",
            "exact_text": (
                "Arbeitgeber und Arbeitnehmer können Abschluss, Inhalt und Form des "
                "Arbeitsvertrages frei vereinbaren, soweit nicht zwingende gesetzliche "
                "Vorschriften, Tarifverträge oder Betriebsvereinbarungen entgegenstehen. "
                "Der Nachweis richtet sich nach dem Nachweisgesetz."
            ),
        },
        {
            "record_id": "provision-nachwg-2",
            "document_id": "de-bund-gii-nachwg",
            "title": (
                "Gesetz über den Nachweis der für ein Arbeitsverhältnis geltenden "
                "wesentlichen Bedingungen"
            ),
            "abbreviation": "NachwG",
            "provision_number": "§ 2",
            "heading": "Nachweispflicht",
            "exact_text": (
                "Der Arbeitgeber hat die wesentlichen Vertragsbedingungen schriftlich "
                "niederzulegen, zu unterzeichnen und auszuhändigen. Die Niederschrift kann "
                "in Textform abgefasst und elektronisch übermittelt werden, sofern sie "
                "zugänglich, speicherbar und ausdruckbar ist und ein Empfangsnachweis "
                "angefordert wird. Diese elektronische Möglichkeit gilt nicht für "
                "Arbeitnehmer in Wirtschaftsbereichen nach § 2a Absatz 1 des "
                "Schwarzarbeitsbekämpfungsgesetzes. "
                + (
                    "Weitere wesentliche Bedingungen, Fristen, Verfahren und Ausnahmen "
                    "sind anhand der aktuellen amtlichen Fassung gesondert zu prüfen. "
                )
                * 20
            ),
        },
    )
    for row in rows:
        payload = f"official fixture source: {row['record_id']}\n".encode("utf-8")
        source_digest = hashlib.sha256(payload).hexdigest()
        source_path = (
            root
            / "objects"
            / "sha256"
            / source_digest[:2]
            / source_digest[2:4]
            / source_digest
        )
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(payload)
        document = {
            "document_id": row["document_id"],
            "object_sha256": source_digest,
            "source_sha256": source_digest,
            "source_url": f"https://fixture.invalid/{row['document_id']}",
            "publication_date": "2026-01-01",
            "authority_status": "NON_AUTHORITATIVE_SYSTEM_RECORD",
            "can_approve": False,
            "can_write": False,
            "can_execute": False,
        }
        (root / "normalized" / "documents" / f"{row['document_id']}.json").write_text(
            json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )

    search_path = root / "indexes" / "german_law.sqlite3"
    search = sqlite3.connect(search_path)
    try:
        search.executescript(
            """
            CREATE TABLE records (
                record_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                title TEXT NOT NULL,
                abbreviation TEXT,
                provision_number TEXT,
                heading TEXT,
                exact_text TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                source_class TEXT NOT NULL,
                document_type TEXT NOT NULL,
                publisher TEXT NOT NULL,
                citation TEXT,
                effective_from TEXT,
                effective_until TEXT,
                version_date TEXT,
                language TEXT NOT NULL,
                official_text INTEGER NOT NULL,
                currentness_status TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE records_fts USING fts5(
                record_id UNINDEXED, title, abbreviation, provision_number, heading,
                exact_text, jurisdiction, document_type, publisher, citation,
                effective_from, version_date, content='records', content_rowid='rowid'
            );
            """
        )
        for row in rows:
            search.execute(
                """
                INSERT INTO records (
                    record_id, document_id, title, abbreviation, provision_number,
                    heading, exact_text, jurisdiction, source_class, document_type,
                    publisher, citation, effective_from, effective_until, version_date,
                    language, official_text, currentness_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["record_id"],
                    row["document_id"],
                    row["title"],
                    row["abbreviation"],
                    row["provision_number"],
                    row["heading"],
                    row["exact_text"],
                    "DE-BUND",
                    "OFFICIAL_CONSOLIDATED_TEXT",
                    "STATUTE_OR_REGULATION",
                    "Fixture Federal Publisher",
                    "",
                    None,
                    None,
                    "2026-01-01",
                    "de",
                    0,
                    "CURRENTNESS_NOT_VERIFIED",
                ),
            )
        search.execute("INSERT INTO records_fts(records_fts) VALUES('rebuild')")
        search.commit()
    finally:
        search.close()

    temporal_snapshot = "fixture-temporal-snapshot"
    output_hashes = {
        "events": "a" * 64,
        "document_validity": "b" * 64,
        "provision_validity": "c" * 64,
        "amendment_relationships": "d" * 64,
        "unresolved": "e" * 64,
    }
    temporal_logical_hash = "f" * 64
    temporal_path = root / "indexes" / "federal_temporal_graph.sqlite3"
    temporal = sqlite3.connect(temporal_path)
    try:
        temporal.execute(
            "CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL)"
        )
        metadata = {
            "corpus_snapshot_id": temporal_snapshot,
            "format": "federal_temporal_graph_1a",
            "scope": "federal",
            "output_hashes": output_hashes,
        }
        temporal.executemany(
            "INSERT INTO metadata (key, value_json) VALUES (?, ?)",
            (
                (
                    key,
                    json.dumps({"value": value}, sort_keys=True, separators=(",", ":")),
                )
                for key, value in metadata.items()
            ),
        )
        temporal.commit()
    finally:
        temporal.close()

    manifest = {
        "authority_status": "NON_AUTHORITATIVE_SYSTEM_RECORD",
        "can_approve": False,
        "can_execute": False,
        "can_write": False,
        "corpus_snapshot_id": temporal_snapshot,
        "counts": {"provisions_inspected": len(rows)},
        "format": "federal_temporal_graph_1a",
        "index": {"logical_hash": temporal_logical_hash},
        "module_id": "DE_BUND_TEMPORAL_GRAPH",
        "module_version": "1A",
        "output_hashes": output_hashes,
        "scope": "federal",
    }
    manifest_digest = hashlib.sha256(
        (
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    manifest["manifest_hash"] = manifest_digest
    (root / "manifests" / "federal-temporal-graph-1a.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )

    search_digest = hashlib.sha256(search_path.read_bytes()).hexdigest()
    index_digest = canonical_sha256(
        {
            "search_index_sha256": search_digest,
            "temporal_index_logical_hash": temporal_logical_hash,
        }
    )
    identity = GermanLawCorpusIdentity(
        manifest_id=temporal_snapshot,
        manifest_digest=manifest_digest,
        search_index_sha256=search_digest,
        temporal_index_logical_hash=temporal_logical_hash,
        index_id="fixture-search+temporal",
        index_digest=index_digest,
        indexed_source_count=len(rows),
    )
    return temporary, root, identity
