from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from runtime_paths import runtime_state_dir


@dataclass
class MemoryHat:
    name: str
    role: str
    instructions: str
    project_path: str = ""
    persistent: bool = True


DEFAULT_HATS = [
    MemoryHat(
        name="coding",
        role="coding agent",
        instructions=(
            "Focus on small, reviewable code changes. Read relevant files before editing. "
            "Prefer existing project patterns and keep execution human-approved."
        ),
    ),
    MemoryHat(
        name="linux",
        role="linux operator",
        instructions=(
            "Treat shell actions as proposed operations. Prefer inspection commands first. "
            "Avoid destructive commands and package installs unless the user explicitly asks."
        ),
    ),
    MemoryHat(
        name="research",
        role="research analyst",
        instructions=(
            "Separate sourced facts from inference. When browsing, capture relevant text and "
            "summarize concisely without inventing missing details."
        ),
    ),
]


class MemoryHatStore:
    """Persistent context overlays used by the planner prompt."""

    def __init__(self, project_dir: Path) -> None:
        state_root = runtime_state_dir(project_dir)
        self.hats_dir = state_root / "memory" / "hats"
        self.active_file = state_root / "state" / "active_hat.json"
        self.hats_dir.mkdir(parents=True, exist_ok=True)
        self.active_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()

    def list_hats(self) -> list[MemoryHat]:
        hats: list[MemoryHat] = []
        for path in sorted(self.hats_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                hats.append(MemoryHat(**payload))
            except (TypeError, json.JSONDecodeError):
                continue
        return hats

    def get_hat(self, name: str) -> MemoryHat | None:
        hat_path = self.hats_dir / f"{name}.json"
        if not hat_path.exists():
            return None
        try:
            return MemoryHat(**json.loads(hat_path.read_text(encoding="utf-8")))
        except (TypeError, json.JSONDecodeError):
            return None

    def active_hat(self) -> MemoryHat | None:
        if not self.active_file.exists():
            return None
        try:
            payload = json.loads(self.active_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        name = str(payload.get("name", "")).strip()
        if not name:
            return None
        return self.get_hat(name)

    def load_hat(self, name: str) -> MemoryHat:
        hat = self.get_hat(name)
        if hat is None:
            raise ValueError(f"Unknown memory hat: {name}")
        self.active_file.write_text(json.dumps({"name": hat.name}, indent=2), encoding="utf-8")
        return hat

    def clear_active(self) -> None:
        if self.active_file.exists():
            self.active_file.unlink()

    def save_hat(
        self,
        name: str,
        role: str,
        instructions: str,
        project_path: str = "",
        persistent: bool = True,
    ) -> MemoryHat:
        hat = MemoryHat(
            name=name,
            role=role,
            instructions=instructions,
            project_path=project_path,
            persistent=persistent,
        )
        self._write_hat(hat)
        return hat

    def prompt_block(self) -> dict:
        hat = self.active_hat()
        if hat is None:
            return {"active": False, "name": "", "role": "", "instructions": ""}
        return {
            "active": True,
            "name": hat.name,
            "role": hat.role,
            "instructions": hat.instructions,
            "project_path": hat.project_path,
        }

    def _ensure_defaults(self) -> None:
        for hat in DEFAULT_HATS:
            path = self.hats_dir / f"{hat.name}.json"
            if not path.exists():
                self._write_hat(hat)

    def _write_hat(self, hat: MemoryHat) -> None:
        path = self.hats_dir / f"{hat.name}.json"
        path.write_text(json.dumps(asdict(hat), indent=2, ensure_ascii=False), encoding="utf-8")
