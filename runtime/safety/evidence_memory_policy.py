from __future__ import annotations

from runtime.schemas.evidence_memory import (
    EvidenceMemoryRecord,
    EvidenceSourceType,
    NonEvidenceChannel,
    classify_non_evidence_input,
)
from runtime.schemas.provider_critic import ProviderCritiqueRecord


class EvidenceWriteBlockedError(RuntimeError):
    pass


class ProviderCritiqueEvidenceContaminationError(EvidenceWriteBlockedError):
    pass


class CanonicalPromotionBlockedError(RuntimeError):
    pass


_ALLOWED_EVIDENCE_SOURCES = {
    EvidenceSourceType.HUMAN_ENTERED,
    EvidenceSourceType.LOCAL_PARSED_DOCUMENT,
}


def classify_write_channel(source_or_channel: object) -> str:
    if isinstance(source_or_channel, EvidenceSourceType):
        if source_or_channel in _ALLOWED_EVIDENCE_SOURCES:
            return "candidate_evidence"
        if source_or_channel is EvidenceSourceType.SOURCE_METADATA:
            return "provenance_metadata_only"
    if isinstance(source_or_channel, str):
        try:
            return classify_write_channel(EvidenceSourceType(source_or_channel))
        except ValueError:
            pass
    if classify_non_evidence_input(source_or_channel) is not None:
        return "blocked_non_evidence"
    return "blocked_unknown"


def assert_can_write_evidence(record: object) -> None:
    assert_provider_critique_cannot_be_evidence(record)
    if not isinstance(record, EvidenceMemoryRecord):
        raise EvidenceWriteBlockedError("only EvidenceMemoryRecord can enter Evidence Memory")
    if record.source_type not in _ALLOWED_EVIDENCE_SOURCES:
        raise EvidenceWriteBlockedError("source type is not standalone evidence")
    if record.provider_generated:
        raise ProviderCritiqueEvidenceContaminationError("provider-generated records cannot enter Evidence Memory")
    if record.canonical_write_allowed:
        raise EvidenceWriteBlockedError("evidence intake cannot request canonical writes")
    if record.contradiction_registry_write_allowed:
        raise EvidenceWriteBlockedError("evidence intake cannot request contradiction registry writes")
    if record.action_approval_allowed:
        raise EvidenceWriteBlockedError("evidence cannot approve actions")
    if record.execution_allowed:
        raise EvidenceWriteBlockedError("evidence cannot execute")


def assert_provider_critique_cannot_be_evidence(provider_critique_record: object) -> None:
    if isinstance(provider_critique_record, ProviderCritiqueRecord):
        raise ProviderCritiqueEvidenceContaminationError("ProviderCritiqueRecord cannot enter Evidence Memory")
    if getattr(provider_critique_record, "untrusted", False) is True:
        raise ProviderCritiqueEvidenceContaminationError("untrusted provider/model output cannot enter Evidence Memory")
    if getattr(provider_critique_record, "provider_generated", False) is True:
        raise ProviderCritiqueEvidenceContaminationError("provider-generated output cannot enter Evidence Memory")
    if classify_non_evidence_input(provider_critique_record) is NonEvidenceChannel.PROVIDER_CRITIQUE:
        raise ProviderCritiqueEvidenceContaminationError("provider critique channel cannot enter Evidence Memory")
    if isinstance(provider_critique_record, dict):
        if provider_critique_record.get("untrusted") is True:
            raise ProviderCritiqueEvidenceContaminationError("serialized untrusted output cannot enter Evidence Memory")
        if provider_critique_record.get("provider_generated") is True:
            raise ProviderCritiqueEvidenceContaminationError("serialized provider output cannot enter Evidence Memory")
        provider_keys = {"source_provider", "source_model", "response_text"}
        if provider_keys.issubset(provider_critique_record):
            raise ProviderCritiqueEvidenceContaminationError("serialized provider critique cannot enter Evidence Memory")


def assert_canonical_promotion_blocked_by_default(record: EvidenceMemoryRecord) -> None:
    if not isinstance(record, EvidenceMemoryRecord):
        raise TypeError("record must be an EvidenceMemoryRecord")
    raise CanonicalPromotionBlockedError("canonical promotion is blocked by default")


def assert_evidence_cannot_approve_action(record: EvidenceMemoryRecord) -> None:
    if not isinstance(record, EvidenceMemoryRecord):
        raise TypeError("record must be an EvidenceMemoryRecord")
    raise EvidenceWriteBlockedError("evidence cannot approve actions")


def assert_evidence_cannot_execute(record: EvidenceMemoryRecord) -> None:
    if not isinstance(record, EvidenceMemoryRecord):
        raise TypeError("record must be an EvidenceMemoryRecord")
    raise EvidenceWriteBlockedError("evidence cannot execute")
