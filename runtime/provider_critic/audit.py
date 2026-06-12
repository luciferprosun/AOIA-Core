from __future__ import annotations

from pathlib import Path

from runtime.provider_critic.records import ProviderCritiqueRecord


class InMemoryProviderCriticAudit:
    def __init__(self) -> None:
        self._records: list[ProviderCritiqueRecord] = []

    def append(self, record: ProviderCritiqueRecord) -> None:
        self._records.append(record)

    def records(self) -> tuple[ProviderCritiqueRecord, ...]:
        return tuple(self._records)

    def to_jsonl(self) -> str:
        return "\n".join(record.to_json() for record in self._records)


class JsonlProviderCriticAudit:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: ProviderCritiqueRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json())
            handle.write("\n")
