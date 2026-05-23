#!/usr/bin/env python3
from __future__ import annotations


def select_depth(pressure: int) -> str:
    """Return one of three deterministic routing depths for a pressure score."""
    if pressure < 0:
        raise ValueError("pressure must be >= 0")
    if pressure <= 33:
        return "shallow"
    if pressure <= 66:
        return "mid"
    return "deep"


if __name__ == "__main__":
    for sample in (0, 34, 67):
        print(f"{sample}: {select_depth(sample)}")

