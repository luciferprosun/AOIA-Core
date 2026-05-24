#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


CONFIG_PATH = Path(__file__).resolve().parent / "aoia_config.json"
EXPECTED_DEPTHS = ("shallow", "mid", "deep")


@dataclass(frozen=True)
class AOIAConfig:
    """Immutable AOIA configuration loaded once by callers at startup."""

    version: int
    depths: tuple[str, str, str]
    shallow_max: int
    mid_max: int
    runtime_policy: Mapping[str, object]


def load_config(path: Path = CONFIG_PATH) -> AOIAConfig:
    """Load and validate AOIA config as a read-only object."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    depths = tuple(raw.get("depths", ()))
    thresholds = raw.get("pressure_thresholds", {})
    runtime_policy = raw.get("runtime_policy", {})

    if raw.get("version") != 1:
        raise ValueError("AOIA config version must be 1")
    if depths != EXPECTED_DEPTHS:
        raise ValueError("AOIA depths must be exactly: shallow, mid, deep")
    if not isinstance(thresholds, dict):
        raise ValueError("pressure_thresholds must be an object")
    if not isinstance(runtime_policy, dict):
        raise ValueError("runtime_policy must be an object")

    shallow_max = int(thresholds.get("shallow_max"))
    mid_max = int(thresholds.get("mid_max"))
    if shallow_max < 0:
        raise ValueError("shallow_max must be >= 0")
    if mid_max <= shallow_max:
        raise ValueError("mid_max must be greater than shallow_max")
    if runtime_policy.get("load_timing") != "startup_only":
        raise ValueError("runtime_policy.load_timing must be startup_only")
    if runtime_policy.get("mutable_at_runtime") is not False:
        raise ValueError("runtime_policy.mutable_at_runtime must be false")
    if runtime_policy.get("network_required") is not False:
        raise ValueError("runtime_policy.network_required must be false")

    return AOIAConfig(
        version=1,
        depths=EXPECTED_DEPTHS,
        shallow_max=shallow_max,
        mid_max=mid_max,
        runtime_policy=MappingProxyType(dict(runtime_policy)),
    )


if __name__ == "__main__":
    config = load_config()
    print(
        f"AOIA config v{config.version}: "
        f"{config.depths[0]}<= {config.shallow_max}, "
        f"{config.depths[1]}<= {config.mid_max}, "
        f"{config.depths[2]}>{config.mid_max}"
    )

