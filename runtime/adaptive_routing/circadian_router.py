#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime


def current_local_hour() -> int:
    """Return the current local hour as an integer from 0 to 23."""
    return datetime.now().hour


def classify_period(hour: int) -> str:
    """Classify the local hour into the first AOIA pressure window."""
    if 18 <= hour <= 23:
        return "peak_hours"
    return "off_peak_hours"


def select_routing_mode(hour: int | None = None) -> str:
    """Return the minimal DVM-inspired routing mode for the given local hour."""
    resolved_hour = current_local_hour() if hour is None else hour
    if classify_period(resolved_hour) == "peak_hours":
        return "deep_mode"
    return "surface_mode"


if __name__ == "__main__":
    print(select_routing_mode())

