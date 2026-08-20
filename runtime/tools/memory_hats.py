from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from runtime.safety.atomic_persistence import (
    DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    atomic_write_json,
    locked_unlink,
    state_resource_lock_path,
    validate_lock_timeout_seconds,
)
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

    def __init__(
        self,
        project_dir: Path,
        *,
        initialize_defaults: bool = True,
        state_lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        state_root = runtime_state_dir(project_dir)
        self.state_dir = state_root / "state"
        self.state_lock_timeout_seconds = validate_lock_timeout_seconds(
            state_lock_timeout_seconds
        )
        self.hats_dir = state_root / "memory" / "hats"
        self.active_file = self.state_dir / "active_hat.json"
        if initialize_defaults:
            self.ensure_initialized()

    def ensure_initialized(self) -> None:
        self.hats_dir.mkdir(parents=True, exist_ok=True)
        self.active_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()

    def list_hats(self) -> list[MemoryHat]:
        self.ensure_initialized()
        hats: list[MemoryHat] = []
        for path in sorted(self.hats_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                hats.append(MemoryHat(**payload))
            except (TypeError, json.JSONDecodeError):
                continue
        return hats

    def get_hat(self, name: str) -> MemoryHat | None:
        self.ensure_initialized()
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
        self.ensure_initialized()
        hat = self.get_hat(name)
        if hat is None:
            raise ValueError(f"Unknown memory hat: {name}")
        atomic_write_json(
            self.active_file,
            {"name": hat.name},
            lock_path=self._lock_for(self.active_file),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )
        return hat

    def clear_active(self) -> None:
        locked_unlink(
            self.active_file,
            lock_path=self._lock_for(self.active_file),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )

    def save_hat(
        self,
        name: str,
        role: str,
        instructions: str,
        project_path: str = "",
        persistent: bool = True,
    ) -> MemoryHat:
        self.ensure_initialized()
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
        atomic_write_json(
            path,
            asdict(hat),
            lock_path=self._lock_for(path),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )

    def _lock_for(self, resource_path: Path) -> Path:
        return state_resource_lock_path(self.state_dir, resource_path)
