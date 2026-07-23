"""Load private local HAT bindings without exposing roots to prompts or UI."""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Mapping

from .contracts import HatBinding, HatValidationError

DEFAULT_BINDINGS_PATH = Path.home() / ".config" / "aoia-control-chat-demo" / "hat_bindings.json"
_ROOT_KEYS = {"binding_key", "root"}


class HatBindingError(HatValidationError):
    """Malformed private binding state."""


def load_bindings(
    known_binding_keys: Mapping[str, str],
    path: Path = DEFAULT_BINDINGS_PATH,
) -> dict[str, HatBinding]:
    if not path.exists():
        return {}
    if path.is_symlink() or not path.is_file():
        raise HatBindingError("binding file is not a regular local file")
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        raise HatBindingError("binding file cannot be inspected") from exc
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise HatBindingError("binding file permissions are broader than 0600")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HatBindingError("binding file is malformed") from exc
    if not isinstance(value, dict) or set(value) != {"schema_version", "bindings"}:
        raise HatBindingError("binding file has an unexpected shape")
    if value["schema_version"] != 1 or not isinstance(value["bindings"], dict):
        raise HatBindingError("unsupported binding schema")
    if set(value["bindings"]) - set(known_binding_keys):
        raise HatBindingError("binding file contains an unknown HAT id")
    result: dict[str, HatBinding] = {}
    for hat_id, raw in value["bindings"].items():
        if not isinstance(raw, dict) or set(raw) != _ROOT_KEYS:
            raise HatBindingError("binding record has an unexpected shape")
        if raw["binding_key"] != known_binding_keys[hat_id]:
            raise HatBindingError("binding key does not match the committed catalog")
        root = raw["root"]
        if not isinstance(root, str) or not root.strip():
            raise HatBindingError("binding root must be non-empty text")
        try:
            binding = HatBinding(
                hat_id=hat_id,
                binding_key=raw["binding_key"],
                root=Path(root),
            )
        except HatValidationError as exc:
            raise HatBindingError("binding record is invalid") from exc
        result[hat_id] = binding
    return result
