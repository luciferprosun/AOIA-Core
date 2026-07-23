"""Single canonical JSON and hash implementation for Knowledge HAT data."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from dataclasses import asdict, is_dataclass, replace
from enum import Enum
from typing import Any, Mapping

from .contracts import (
    HatAttachment,
    HatDescriptor,
    HatEvidenceBundle,
    HatPassage,
    HatValidationError,
)

PROMPT_RENDERER_SCHEMA_VERSION = 1


def normalize_text(value: str) -> str:
    if not isinstance(value, str):
        raise HatValidationError("text normalization requires a string")
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise HatValidationError("non-finite numbers are not canonical JSON values")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise HatValidationError(f"non-canonical value type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_text(canonical_json(value))


def descriptor_payload(descriptor: HatDescriptor) -> dict[str, object]:
    return _json_value(descriptor)


def passage_payload(passage: HatPassage, *, include_digest: bool = True) -> dict[str, object]:
    payload = _json_value(passage)
    if not include_digest:
        payload.pop("content_digest", None)
    return payload


def passage_digest_payload(
    *,
    hat_id: str,
    library_id: str,
    library_version: str,
    source_id: str,
    source_title: str,
    source_locator: str,
    statutory_references: tuple[str, ...],
    effective_dates: tuple[str, ...],
    excerpt: str,
) -> dict[str, object]:
    return {
        "hat_id": hat_id,
        "library_id": library_id,
        "library_version": library_version,
        "source_id": source_id,
        "source_title": source_title,
        "source_locator": source_locator,
        "statutory_references": statutory_references,
        "effective_dates": effective_dates,
        "excerpt": excerpt,
    }


def bundle_payload(bundle: HatEvidenceBundle, *, include_hash: bool = True) -> dict[str, object]:
    payload = _json_value(bundle)
    if not include_hash:
        payload.pop("bundle_hash", None)
    return payload


def attachment_payload(attachment: HatAttachment, *, include_hash: bool = True) -> dict[str, object]:
    payload = {
        "descriptor": descriptor_payload(attachment.descriptor),
        "bundle_hash": attachment.bundle.bundle_hash,
        "rendered_evidence_digest": attachment.rendered_evidence_digest,
        "prompt_renderer_schema_version": PROMPT_RENDERER_SCHEMA_VERSION,
    }
    if include_hash:
        payload["attachment_hash"] = attachment.attachment_hash
    return payload


def build_bundle(**values: Any) -> HatEvidenceBundle:
    provisional = HatEvidenceBundle(bundle_hash="0" * 64, **values)
    return replace(provisional, bundle_hash=canonical_sha256(bundle_payload(provisional, include_hash=False)))


def build_attachment(
    descriptor: HatDescriptor,
    bundle: HatEvidenceBundle,
    rendered_evidence: str,
) -> HatAttachment:
    rendered_digest = sha256_text(rendered_evidence)
    provisional = HatAttachment(
        descriptor=descriptor,
        bundle=bundle,
        rendered_evidence=rendered_evidence,
        rendered_evidence_digest=rendered_digest,
        attachment_hash="0" * 64,
    )
    return replace(
        provisional,
        attachment_hash=canonical_sha256(attachment_payload(provisional, include_hash=False)),
    )


def verify_bundle(bundle: HatEvidenceBundle) -> None:
    if not isinstance(bundle, HatEvidenceBundle):
        raise HatValidationError("invalid evidence bundle type")
    if bundle.query_digest != sha256_text(bundle.normalized_query):
        raise HatValidationError("bundle query digest mismatch")
    for passage in bundle.passages:
        expected = canonical_sha256(
            passage_digest_payload(
                hat_id=bundle.hat_id,
                library_id=bundle.library_id,
                library_version=bundle.library_version,
                source_id=passage.source_id,
                source_title=passage.source_title,
                source_locator=passage.source_locator,
                statutory_references=passage.statutory_references,
                effective_dates=passage.effective_dates,
                excerpt=passage.excerpt,
            )
        )
        if passage.content_digest != expected:
            raise HatValidationError("passage content or provenance digest mismatch")
    expected_bundle = canonical_sha256(bundle_payload(bundle, include_hash=False))
    if bundle.bundle_hash != expected_bundle:
        raise HatValidationError("bundle hash mismatch")


def verify_attachment(attachment: HatAttachment) -> None:
    if not isinstance(attachment, HatAttachment):
        raise HatValidationError("invalid HAT attachment type")
    verify_bundle(attachment.bundle)
    if attachment.rendered_evidence_digest != sha256_text(attachment.rendered_evidence):
        raise HatValidationError("rendered evidence digest mismatch")
    expected = canonical_sha256(attachment_payload(attachment, include_hash=False))
    if attachment.attachment_hash != expected:
        raise HatValidationError("attachment hash mismatch")
