from __future__ import annotations

from dataclasses import dataclass

from runtime.provider_critic.audit import InMemoryProviderCriticAudit
from runtime.provider_critic.policy import ProviderCriticPolicy
from runtime.provider_critic.records import ProviderCritiqueRecord


class ProviderCallBlockedError(RuntimeError):
    def __init__(self, message: str, record: ProviderCritiqueRecord) -> None:
        super().__init__(message)
        self.record = record


@dataclass(frozen=True)
class ProviderCriticResult:
    record: ProviderCritiqueRecord
    blocked: bool = True


class ProviderCriticGateway:
    def __init__(
        self,
        *,
        policy: ProviderCriticPolicy | None = None,
        audit: InMemoryProviderCriticAudit | None = None,
    ) -> None:
        self.policy = policy or ProviderCriticPolicy()
        self.audit = audit or InMemoryProviderCriticAudit()
        self._attempted_call_count = 0

    @property
    def attempted_call_count(self) -> int:
        return self._attempted_call_count

    def critique(
        self,
        *,
        source_provider: str,
        model_name: str,
        prompt_text: str,
        raise_on_block: bool = True,
        metadata: dict[str, object] | None = None,
    ) -> ProviderCriticResult:
        self.policy.validate_prompt(prompt_text)
        reason = self.policy.block_reason(self._attempted_call_count)
        cost_state = self.policy.cost_ceiling_state(self._attempted_call_count)
        self._attempted_call_count += 1

        record = ProviderCritiqueRecord.blocked_attempt(
            source_provider=source_provider,
            model_name=model_name,
            prompt_text=prompt_text,
            block_reason=reason,
            cost_ceiling_state=cost_state,
            metadata=metadata or {},
        )
        self.audit.append(record)
        if raise_on_block:
            raise ProviderCallBlockedError(reason, record)
        return ProviderCriticResult(record=record, blocked=True)
