from __future__ import annotations

from runtime.schemas.provider_critic import ProviderCritiqueRecord, ProviderTrustLevel


class ProviderCallBlockedError(RuntimeError):
    pass


class UntrustedProviderOutputBlockedError(RuntimeError):
    pass


def is_provider_call_enabled() -> bool:
    return False


def assert_provider_call_blocked_by_default() -> None:
    if not is_provider_call_enabled():
        raise ProviderCallBlockedError("provider calls are blocked by default in M2-B0")


def _assert_untrusted_record(record: ProviderCritiqueRecord, capability: str) -> None:
    if not isinstance(record, ProviderCritiqueRecord):
        raise TypeError("record must be a ProviderCritiqueRecord")
    if record.trust_level is ProviderTrustLevel.UNTRUSTED and record.untrusted is True:
        raise UntrustedProviderOutputBlockedError(
            f"untrusted provider output cannot {capability}"
        )
    raise UntrustedProviderOutputBlockedError(
        f"provider output is not allowed to {capability} in M2-B0"
    )


def assert_provider_output_cannot_write_evidence(record: ProviderCritiqueRecord) -> None:
    _assert_untrusted_record(record, "write evidence")


def assert_provider_output_cannot_write_canonical(record: ProviderCritiqueRecord) -> None:
    _assert_untrusted_record(record, "write canonical knowledge")


def assert_provider_output_cannot_approve_action(record: ProviderCritiqueRecord) -> None:
    _assert_untrusted_record(record, "approve actions")


def assert_provider_output_cannot_execute(record: ProviderCritiqueRecord) -> None:
    _assert_untrusted_record(record, "execute")
