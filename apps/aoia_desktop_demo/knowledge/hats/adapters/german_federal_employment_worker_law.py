"""Read-only adapter for the existing German Federal Law 1A corpus."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from ..canonical import (
    build_bundle,
    canonical_sha256,
    normalize_text,
    passage_digest_payload,
    sha256_text,
)
from ..contracts import (
    HatBinding,
    HatDescriptor,
    HatPassage,
    HatRetrievalLimits,
    HatStatus,
    HatValidationError,
)

HAT_ID = "german_federal_employment_worker_law"
ADAPTER_ID = "german_federal_employment_worker_law_v1"
BINDING_KEY = "german_federal_employment_worker_law_local"
LIBRARY_ID = "de-law-federal-1a"
LIBRARY_VERSION = "1a"
DISPLAY_NAME = "German Federal Law"
MANIFEST_RELATIVE = Path("manifests/federal-temporal-graph-1a.json")
SEARCH_INDEX_RELATIVE = Path("indexes/german_law.sqlite3")
TEMPORAL_INDEX_RELATIVE = Path("indexes/federal_temporal_graph.sqlite3")

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]+\Z")
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_CITATION = re.compile(
    r"§\s*(?P<number>[0-9]+[a-z]?)\s*(?P<abbreviation>[A-Za-zÄÖÜäöüß0-9. -]{2,24})?",
    re.UNICODE,
)


@dataclass(frozen=True, slots=True)
class GermanLawCorpusIdentity:
    manifest_id: str
    manifest_digest: str
    search_index_sha256: str
    temporal_index_logical_hash: str
    index_id: str
    index_digest: str
    indexed_source_count: int


DEFAULT_IDENTITY = GermanLawCorpusIdentity(
    manifest_id="federal-temporal-1a-fe9ce34784e92af97651fe0378672d4c",
    manifest_digest="602922920c30dcae567a1bc4f8459060a24ae507b4d432ebf82673320e20a7a2",
    search_index_sha256="0b2a97eac5c7e33902d1bd6a49531ecefdfa1f06b5f9511a1131d6e6d622c9bf",
    temporal_index_logical_hash="923b439eaa736247686fbf43cc00db8cefac125dff96631a590548d9cd20cc0c",
    index_id="german-law-fts5+federal-temporal-graph-1a",
    index_digest="8491438dd28a428a69a9bf5c49b215f63ff35507124378f0c635bf11b2448f19",
    indexed_source_count=370_039,
)

_TRANSLATIONS: dict[str, tuple[str, ...]] = {
    "employment": ("arbeitsverhältnis", "arbeitsvertrag", "arbeitnehmer"),
    "contract": ("arbeitsvertrag", "vertrag"),
    "oral": ("mündlich", "form"),
    "orally": ("mündlich", "form"),
    "valid": ("wirksam", "abschluss"),
    "validity": ("wirksam", "abschluss"),
    "documentation": ("nachweis", "nachweispflicht", "niederschrift"),
    "document": ("nachweis", "niederschrift"),
    "provide": ("aushändigen", "übermitteln"),
    "employer": ("arbeitgeber",),
    "employee": ("arbeitnehmer",),
    "essential": ("wesentliche",),
    "working": ("arbeitsbedingungen", "vertragsbedingungen"),
    "conditions": ("arbeitsbedingungen", "vertragsbedingungen"),
    "statutory": ("gesetz", "vorschrift"),
    "provisions": ("vorschrift",),
    "form": ("form", "schriftform", "textform"),
    "requirements": ("pflicht", "nachweispflicht"),
    "exceptions": ("ausnahme", "soweit"),
    "exception": ("ausnahme", "soweit"),
    "delivery": ("aushändigen", "übermitteln"),
    "transmission": ("übermitteln", "textform"),
}
_CONTRACT_CONCEPT = frozenset({"employment", "contract", "oral", "orally", "valid", "validity", "form"})
_DOCUMENTATION_CONCEPT = frozenset(
    {"documentation", "document", "provide", "employer", "essential", "working", "conditions", "requirements", "delivery", "transmission"}
)
_CONTRACT_FACET = (
    "arbeitsvertrag",
    "arbeitsvertrages",
    "form",
    "abschluss",
    "mündlich",
    "wirksam",
    "nachweisgesetz",
    "nachweisgesetzes",
)
_DOCUMENTATION_FACET = (
    "nachweispflicht",
    "vertragsbedingungen",
    "niederschrift",
    "arbeitsverhältnis",
    "arbeitgeber",
    "arbeitnehmer",
)


@dataclass(frozen=True, slots=True)
class _ControlFiles:
    root: Path
    manifest: Path
    search_index: Path
    temporal_index: Path


@dataclass(frozen=True, slots=True)
class _Candidate:
    facet: int
    document_id: str
    record_id: str
    title: str
    abbreviation: str | None
    provision_number: str | None
    heading: str | None
    exact_text: str
    source_class: str
    effective_from: str | None
    effective_until: str | None
    version_date: str | None
    stable_score: int

    @property
    def key(self) -> tuple[str, str]:
        return self.document_id, self.record_id


class GermanFederalEmploymentWorkerLawAdapter:
    """Direct data adapter; it never imports or executes external corpus code."""

    def __init__(self, identity: GermanLawCorpusIdentity = DEFAULT_IDENTITY) -> None:
        self._identity = identity
        self._digest_cache: dict[tuple[str, int, int, int], str] = {}

    def descriptor(self) -> HatDescriptor:
        return HatDescriptor(
            hat_id=HAT_ID,
            display_name=DISPLAY_NAME,
            domain="german_federal_employment_law",
            adapter_id=ADAPTER_ID,
            descriptor_schema_version=1,
            evidence_schema_version=1,
            external_resource=True,
            authoritative=False,
        )

    def inspect_status(self, binding: HatBinding) -> HatStatus:
        try:
            controls = self._control_files(binding)
            manifest = self._validated_manifest(controls.manifest)
            search_digest = self._file_sha256(controls.search_index)
            if search_digest != self._identity.search_index_sha256:
                raise HatValidationError("search index digest mismatch")
            self._validate_search_index(controls.search_index, manifest)
            self._validate_temporal_index(controls.temporal_index, manifest)
            computed_index_digest = canonical_sha256(
                {
                    "search_index_sha256": search_digest,
                    "temporal_index_logical_hash": manifest["index"]["logical_hash"],
                }
            )
            if computed_index_digest != self._identity.index_digest:
                raise HatValidationError("composite index digest mismatch")
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            return self._status("unavailable", "external_resource_unavailable")
        except (HatValidationError, json.JSONDecodeError, sqlite3.DatabaseError, OSError, ValueError, TypeError):
            return self._status("invalid", "external_resource_invalid")
        return HatStatus(
            hat_id=HAT_ID,
            state="ready",
            library_id=LIBRARY_ID,
            library_version=LIBRARY_VERSION,
            manifest_id=self._identity.manifest_id,
            manifest_digest=self._identity.manifest_digest,
            index_id=self._identity.index_id,
            index_digest=self._identity.index_digest,
            indexed_source_count=self._identity.indexed_source_count,
            read_only=True,
            local_only=True,
            error_category=None,
        )

    def retrieve(
        self,
        binding: HatBinding,
        query: str,
        *,
        limits: HatRetrievalLimits,
    ):
        normalized_query = normalize_text(query)
        if not normalized_query:
            raise HatValidationError("HAT query must not be empty")
        before = self.inspect_status(binding)
        if before.state != "ready":
            raise HatValidationError(before.error_category or "HAT is not ready")
        controls = self._control_files(binding)
        candidates = self._retrieve_candidates(controls.search_index, normalized_query)
        passages = self._build_passages(controls.root, candidates, limits)
        after = self.inspect_status(binding)
        if after != before:
            raise HatValidationError("HAT control identity changed during retrieval")
        return build_bundle(
            schema_version=1,
            hat_id=HAT_ID,
            normalized_query=normalized_query,
            query_digest=sha256_text(normalized_query),
            library_id=LIBRARY_ID,
            library_version=LIBRARY_VERSION,
            manifest_id=before.manifest_id,
            manifest_digest=before.manifest_digest,
            index_id=before.index_id,
            index_digest=before.index_digest,
            passages=passages,
        )

    def _control_files(self, binding: HatBinding) -> _ControlFiles:
        if binding.hat_id != HAT_ID or binding.binding_key != BINDING_KEY:
            raise HatValidationError("binding identity does not match the German-law adapter")
        try:
            root = binding.root.resolve(strict=True)
        except FileNotFoundError:
            raise
        if not root.is_dir():
            raise NotADirectoryError(root)
        return _ControlFiles(
            root=root,
            manifest=self._required_file(root, MANIFEST_RELATIVE),
            search_index=self._required_file(root, SEARCH_INDEX_RELATIVE),
            temporal_index=self._required_file(root, TEMPORAL_INDEX_RELATIVE),
        )

    @staticmethod
    def _required_file(root: Path, relative: Path) -> Path:
        if relative.is_absolute() or ".." in relative.parts:
            raise HatValidationError("unsafe required control path")
        candidate = root / relative
        if candidate.is_symlink():
            raise HatValidationError("required control file cannot be a symlink")
        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise HatValidationError("required control file escapes the bound root") from exc
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        return resolved

    def _validated_manifest(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise HatValidationError("manifest must be a JSON object")
        expected_manifest_hash = value.get("manifest_hash")
        payload = {key: item for key, item in value.items() if key != "manifest_hash"}
        computed_manifest_hash = hashlib.sha256(
            (
                json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode("utf-8")
        ).hexdigest()
        if expected_manifest_hash != computed_manifest_hash:
            raise HatValidationError("manifest self-hash mismatch")
        required = {
            "module_id": "DE_BUND_TEMPORAL_GRAPH",
            "module_version": "1A",
            "scope": "federal",
            "corpus_snapshot_id": self._identity.manifest_id,
            "manifest_hash": self._identity.manifest_digest,
        }
        if any(value.get(key) != expected for key, expected in required.items()):
            raise HatValidationError("manifest identity mismatch")
        index = value.get("index")
        counts = value.get("counts")
        if not isinstance(index, dict) or not isinstance(counts, dict):
            raise HatValidationError("manifest index/count metadata is malformed")
        if index.get("logical_hash") != self._identity.temporal_index_logical_hash:
            raise HatValidationError("temporal logical index digest mismatch")
        if counts.get("provisions_inspected") != self._identity.indexed_source_count:
            raise HatValidationError("manifest indexed-source count mismatch")
        if value.get("authority_status") != "NON_AUTHORITATIVE_SYSTEM_RECORD":
            raise HatValidationError("manifest authority boundary mismatch")
        if any(value.get(name) is not False for name in ("can_approve", "can_write", "can_execute")):
            raise HatValidationError("manifest exposes a forbidden capability")
        return value

    def _file_sha256(self, path: Path) -> str:
        metadata = path.stat()
        cache_key = (path.as_posix(), metadata.st_size, metadata.st_mtime_ns, metadata.st_ino)
        cached = self._digest_cache.get(cache_key)
        if cached is not None:
            return cached
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        value = digest.hexdigest()
        self._digest_cache = {cache_key: value}
        return value

    @staticmethod
    @contextmanager
    def _connection(path: Path) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro&immutable=1", uri=True)
        connection.row_factory = sqlite3.Row
        denied_names = (
            "SQLITE_INSERT",
            "SQLITE_UPDATE",
            "SQLITE_DELETE",
            "SQLITE_CREATE_INDEX",
            "SQLITE_CREATE_TABLE",
            "SQLITE_CREATE_TEMP_INDEX",
            "SQLITE_CREATE_TEMP_TABLE",
            "SQLITE_CREATE_TRIGGER",
            "SQLITE_CREATE_VIEW",
            "SQLITE_DROP_INDEX",
            "SQLITE_DROP_TABLE",
            "SQLITE_ALTER_TABLE",
            "SQLITE_ATTACH",
            "SQLITE_DETACH",
            "SQLITE_REINDEX",
            "SQLITE_ANALYZE",
        )
        denied = {getattr(sqlite3, name) for name in denied_names if hasattr(sqlite3, name)}

        def authorizer(action: int, _arg1: str | None, _arg2: str | None, _db: str | None, _src: str | None) -> int:
            return sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK

        connection.set_authorizer(authorizer)
        try:
            yield connection
        finally:
            connection.close()

    def _validate_search_index(self, path: Path, manifest: dict[str, Any]) -> None:
        with self._connection(path) as connection:
            tables = {
                str(row["name"])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = ? ORDER BY name",
                    ("table",),
                )
            }
            if not {"records", "records_fts"} <= tables:
                raise HatValidationError("search index schema is incomplete")
            count = int(connection.execute("SELECT COUNT(*) AS value FROM records").fetchone()["value"])
        if count != int(manifest["counts"]["provisions_inspected"]):
            raise HatValidationError("search index record count mismatch")

    def _validate_temporal_index(self, path: Path, manifest: dict[str, Any]) -> None:
        with self._connection(path) as connection:
            rows = connection.execute(
                "SELECT key, value_json FROM metadata ORDER BY key"
            ).fetchall()
        metadata = {str(row["key"]): json.loads(str(row["value_json"])).get("value") for row in rows}
        if metadata.get("corpus_snapshot_id") != manifest["corpus_snapshot_id"]:
            raise HatValidationError("temporal index snapshot identity mismatch")
        if metadata.get("format") != manifest["format"] or metadata.get("scope") != "federal":
            raise HatValidationError("temporal index metadata mismatch")
        if metadata.get("output_hashes") != manifest.get("output_hashes"):
            raise HatValidationError("temporal index output identity mismatch")

    def _retrieve_candidates(self, search_index: Path, query: str) -> tuple[_Candidate, ...]:
        query_words = tuple(_words(query))
        expanded = _expanded_terms(query_words)
        facets: list[tuple[str, tuple[str, ...]]] = []
        bounded_to_semantic_facets = False
        citation = _citation_terms(query)
        if citation:
            facets.append((_and_expression(citation), citation))
        if set(query_words) & _CONTRACT_CONCEPT:
            bounded_to_semantic_facets = True
            facets.append(
                (
                    '("arbeitsvertrag" OR "arbeitsvertrages") AND '
                    '("form" OR "abschluss" OR "mündlich" OR "wirksam" '
                    'OR "nachweisgesetz" OR "nachweisgesetzes")',
                    _CONTRACT_FACET,
                )
            )
        if set(query_words) & _DOCUMENTATION_CONCEPT:
            bounded_to_semantic_facets = True
            facets.append(
                (
                    '("nachweispflicht" OR "vertragsbedingungen" OR "niederschrift") '
                    'AND ("arbeitsverhältnis" OR "arbeitgeber" OR "arbeitnehmer")',
                    _DOCUMENTATION_FACET,
                )
            )
        if expanded and not bounded_to_semantic_facets and not citation:
            facets.append((_or_expression(expanded[:24]), expanded[:24]))
        if not facets:
            raise HatValidationError("query contains no searchable terms")

        candidates: dict[tuple[int, str, str], _Candidate] = {}
        with self._connection(search_index) as connection:
            for facet_index, (expression, terms) in enumerate(facets):
                rows = connection.execute(
                    """
                    SELECT
                        r.document_id,
                        r.record_id,
                        r.title,
                        r.abbreviation,
                        r.provision_number,
                        r.heading,
                        substr(r.exact_text, 1, 8001) AS exact_text,
                        r.source_class,
                        r.effective_from,
                        r.effective_until,
                        r.version_date
                    FROM records_fts
                    JOIN records r ON r.rowid = records_fts.rowid
                    WHERE records_fts MATCH ?
                      AND r.jurisdiction = ?
                      AND r.source_class = ?
                    ORDER BY bm25(records_fts), r.document_id, r.record_id
                    LIMIT 160
                    """,
                    (expression, "DE-BUND", "OFFICIAL_CONSOLIDATED_TEXT"),
                ).fetchall()
                for row in rows:
                    candidate = _candidate_from_row(facet_index, row, terms)
                    candidates[(facet_index, candidate.document_id, candidate.record_id)] = candidate

        selected: list[_Candidate] = []
        seen: set[tuple[str, str]] = set()
        for facet_index in range(len(facets)):
            pool = sorted(
                (candidate for candidate in candidates.values() if candidate.facet == facet_index),
                key=lambda candidate: (
                    -candidate.stable_score,
                    candidate.document_id,
                    candidate.record_id,
                ),
            )
            if pool:
                selected.append(pool[0])
                seen.add(pool[0].key)
        if bounded_to_semantic_facets or citation:
            return tuple(selected)
        remaining = sorted(
            (candidate for candidate in candidates.values() if candidate.key not in seen),
            key=lambda candidate: (
                -candidate.stable_score,
                candidate.facet,
                candidate.document_id,
                candidate.record_id,
            ),
        )
        selected.extend(remaining)
        return tuple(selected)

    def _build_passages(
        self,
        root: Path,
        candidates: tuple[_Candidate, ...],
        limits: HatRetrievalLimits,
    ) -> tuple[HatPassage, ...]:
        passages: list[HatPassage] = []
        seen: set[tuple[str, str]] = set()
        total_chars = 0
        for candidate in candidates:
            if candidate.key in seen or len(passages) >= limits.max_results:
                continue
            remaining = limits.max_total_chars - total_chars
            if remaining < 256:
                break
            excerpt = candidate.exact_text[: min(limits.max_excerpt_chars, remaining)]
            if not excerpt.strip():
                continue
            document = self._document_metadata(root, candidate.document_id)
            digest = str(document.get("object_sha256") or document.get("source_sha256") or "")
            if not _SHA256.fullmatch(digest):
                raise HatValidationError("source provenance digest is malformed")
            source_object = self._required_file(
                root,
                Path("objects/sha256") / digest[:2] / digest[2:4] / digest,
            )
            if self._file_sha256(source_object) != digest:
                raise HatValidationError("source object digest mismatch")
            source_locator = (
                f"normalized/documents/{candidate.document_id}.json"
                f"#{candidate.record_id}"
            )
            reference = " ".join(
                item
                for item in (candidate.abbreviation, candidate.provision_number)
                if item
            ).strip()
            effective_dates = tuple(
                dict.fromkeys(
                    str(value)
                    for value in (
                        candidate.effective_from,
                        candidate.effective_until,
                        candidate.version_date,
                        document.get("publication_date"),
                        document.get("effective_date"),
                    )
                    if isinstance(value, str) and value.strip()
                )
            )
            source_id = f"{candidate.document_id}:{candidate.record_id}"
            title = normalize_text(candidate.title)
            digest_payload = passage_digest_payload(
                hat_id=HAT_ID,
                library_id=LIBRARY_ID,
                library_version=LIBRARY_VERSION,
                source_id=source_id,
                source_title=title,
                source_locator=source_locator,
                statutory_references=(reference,) if reference else (),
                effective_dates=effective_dates,
                excerpt=excerpt,
            )
            passage = HatPassage(
                source_id=source_id,
                source_title=title,
                source_locator=source_locator,
                statutory_references=(reference,) if reference else (),
                effective_dates=effective_dates,
                excerpt=excerpt,
                rank=len(passages) + 1,
                score=candidate.stable_score,
                content_digest=canonical_sha256(digest_payload),
            )
            passages.append(passage)
            seen.add(candidate.key)
            total_chars += len(excerpt)
        return tuple(passages)

    def _document_metadata(self, root: Path, document_id: str) -> dict[str, Any]:
        if not _IDENTIFIER.fullmatch(document_id):
            raise HatValidationError("document id is malformed")
        path = self._required_file(
            root,
            Path("normalized/documents") / f"{document_id}.json",
        )
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict) or value.get("document_id") != document_id:
            raise HatValidationError("document provenance is malformed")
        source_url = value.get("source_url")
        if not isinstance(source_url, str) or not source_url.strip():
            raise HatValidationError("document provenance is missing a source URL")
        return value

    @staticmethod
    def _status(state: str, category: str) -> HatStatus:
        return HatStatus(
            hat_id=HAT_ID,
            state=state,  # type: ignore[arg-type]
            library_id=None,
            library_version=None,
            manifest_id=None,
            manifest_digest=None,
            index_id=None,
            index_digest=None,
            indexed_source_count=None,
            read_only=True,
            local_only=True,
            error_category=category,
        )


def _normalized(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(_words(value))


def _words(value: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return tuple(_WORD.findall(normalized))


def _expanded_terms(query_words: tuple[str, ...]) -> tuple[str, ...]:
    terms: list[str] = []
    for word in query_words:
        if len(word) >= 3:
            terms.append(word)
        terms.extend(_TRANSLATIONS.get(word, ()))
    return tuple(dict.fromkeys(term for term in terms if _WORD.fullmatch(term)))


def _citation_terms(query: str) -> tuple[str, ...]:
    match = _CITATION.search(query)
    if match is None:
        return ()
    abbreviation_words = _words(match.group("abbreviation") or "")
    abbreviation = next((word for word in abbreviation_words if len(word) >= 2), "")
    return tuple(item for item in (abbreviation, match.group("number")) if item)


def _quoted(term: str) -> str:
    safe = "".join(_WORD.findall(term))
    if not safe:
        raise HatValidationError("unsafe FTS term")
    return f'"{safe}"'


def _or_expression(terms: tuple[str, ...]) -> str:
    return " OR ".join(_quoted(term) for term in terms)


def _and_expression(terms: tuple[str, ...]) -> str:
    return " AND ".join(_quoted(term) for term in terms)


def _candidate_from_row(
    facet: int,
    row: sqlite3.Row,
    terms: tuple[str, ...],
) -> _Candidate:
    title = str(row["title"] or "")
    heading = str(row["heading"] or "")
    exact_text = str(row["exact_text"] or "")
    normalized_title = _normalized(title)
    normalized_heading = _normalized(heading)
    normalized_excerpt = _normalized(exact_text)
    score = 0
    for term in terms:
        normalized_term = _normalized(term)
        if normalized_term and normalized_term in normalized_excerpt:
            score += 4
        if normalized_term and normalized_term in normalized_title:
            score += 8
        if normalized_term and normalized_term in normalized_heading:
            score += 12
    return _Candidate(
        facet=facet,
        document_id=str(row["document_id"]),
        record_id=str(row["record_id"]),
        title=title,
        abbreviation=str(row["abbreviation"]) if row["abbreviation"] else None,
        provision_number=str(row["provision_number"]) if row["provision_number"] else None,
        heading=heading or None,
        exact_text=exact_text,
        source_class=str(row["source_class"]),
        effective_from=str(row["effective_from"]) if row["effective_from"] else None,
        effective_until=str(row["effective_until"]) if row["effective_until"] else None,
        version_date=str(row["version_date"]) if row["version_date"] else None,
        stable_score=score,
    )
