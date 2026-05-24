from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LocalRoute:
    actions: list[dict[str, Any]]
    final_message: str | None = None


class LocalRouter:
    """Conservative local router for obvious tasks that do not need an LLM."""

    def __init__(self, desktop_dir: Path) -> None:
        self.desktop_dir = desktop_dir

    def route(self, user_input: str) -> LocalRoute | None:
        text = user_input.strip()
        lowered = text.lower()
        if not text:
            return None

        if self._asks_for_date(lowered):
            return LocalRoute([{"action": "shell_execute", "command": "date -Iseconds", "reason": "Local date route."}])

        if lowered in {"pwd", "gdzie jestem", "pokaz katalog", "pokaż katalog"}:
            return LocalRoute([{"action": "shell_execute", "command": "pwd", "reason": "Local pwd route."}])

        if lowered in {"ls", "lista plikow", "lista plików", "pokaz pliki", "pokaż pliki"}:
            return LocalRoute([{"action": "shell_execute", "command": "ls -la", "reason": "Local list route."}])

        if lowered in {"curl --version", "sprawdz curl", "sprawdź curl"}:
            return LocalRoute([{"action": "shell_execute", "command": "curl --version", "reason": "Local curl version route."}])

        folder_name = self._extract_desktop_folder_name(text)
        if folder_name:
            target = self.desktop_dir / folder_name
            return LocalRoute(
                [{"action": "create_folder", "path": str(target), "reason": "Local desktop folder route."}],
                f"Folder ready at {target}",
            )

        return None

    @staticmethod
    def _asks_for_date(lowered: str) -> bool:
        return (
            "jaki dzis" in lowered
            or "jaki dziś" in lowered
            or "data" == lowered
            or lowered in {"date", "dzisiejsza data"}
        )

    @staticmethod
    def _extract_desktop_folder_name(text: str) -> str | None:
        lowered = text.lower()
        if not any(token in lowered for token in ("folder", "katalog")):
            return None
        if not any(token in lowered for token in ("pulpit", "pulpicie", "desktop")):
            return None
        if not any(token in lowered for token in ("stw", "utw", "zrob", "zrób", "create", "make")):
            return None

        patterns = [
            r"(?:folder|katalog)\s+([A-Za-z0-9_.-]{2,80})",
            r"([A-Za-z0-9_.-]{2,80})\s+(?:na|on)\s+(?:pulpicie|desktop)",
        ]
        ignored = {"na", "on", "pulpicie", "desktop", "folder", "katalog"}
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            name = match.group(1).strip().strip(".,?!")
            if name.lower() not in ignored:
                return name
        return None
