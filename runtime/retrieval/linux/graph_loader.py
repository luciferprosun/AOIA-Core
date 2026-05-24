from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=4)
def load_command_graph(project_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_dir) if project_dir is not None else PROJECT_ROOT
    graph_path = root / "knowledge" / "command_graph.json"
    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "nodes": {}}
    return payload if isinstance(payload, dict) else {"version": 1, "nodes": {}}

