from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCriticPolicy:
    enabled: bool = False
    max_calls_per_session: int = 0
    max_prompt_chars: int = 8000
    allow_network: bool = False
    allow_auto_send: bool = False
    allow_action_proposals: bool = False
    allow_canonical_writes: bool = False

    def validate_prompt(self, prompt_text: str) -> None:
        if len(prompt_text) > self.max_prompt_chars:
            raise ValueError(f"provider critic prompt exceeds {self.max_prompt_chars} characters")

    def block_reason(self, attempted_call_count: int = 0) -> str:
        if not self.enabled:
            return "provider critic disabled by default"
        if not self.allow_network:
            return "provider critic network calls are not allowed"
        if not self.allow_auto_send:
            return "provider critic auto-send is not allowed"
        if attempted_call_count >= self.max_calls_per_session:
            return "provider critic call ceiling reached"
        return "provider critic blocked in inert M2-B0 phase"

    def cost_ceiling_state(self, attempted_call_count: int = 0) -> str:
        return f"calls={attempted_call_count};max={self.max_calls_per_session};network_allowed={self.allow_network}"
