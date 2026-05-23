#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROFILE_PATH = Path(__file__).resolve().parent / "traffic_profiles.json"


def load_profiles(path: Path = PROFILE_PATH) -> dict[str, Any]:
    """Load static local traffic profiles."""
    return json.loads(path.read_text(encoding="utf-8"))


def current_local_hour() -> int:
    """Return the current local hour as an integer from 0 to 23."""
    return datetime.now().hour


def classify_traffic(region: str, hour: int | None = None) -> str:
    """Classify a region/hour pair as high or low traffic."""
    resolved_hour = current_local_hour() if hour is None else hour
    profiles = load_profiles()
    profile = profiles.get(region)
    if profile is None:
        raise ValueError(f"Unknown region: {region}")

    if resolved_hour in profile.get("peak_hours", []):
        return "high_traffic"
    if resolved_hour in profile.get("off_peak_hours", []):
        return "low_traffic"
    return "low_traffic"


if __name__ == "__main__":
    print(classify_traffic("Europe"))

